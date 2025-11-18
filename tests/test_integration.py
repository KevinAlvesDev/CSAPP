

import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))

from project import create_app
from project.db import get_db_connection, query_db, execute_db


@pytest.fixture
def app():
    """Cria uma instância do app para testes."""
    app = create_app()
    app.config.update({
        'TESTING': True,
        'USE_SQLITE_LOCALLY': True,
        'WTF_CSRF_ENABLED': False,\
        'AUTH0_ENABLED': False,\
    })

    with app.app_context():
        from project.db import init_db
        init_db()
    
    yield app

    with app.app_context():
        conn, _ = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("DELETE FROM comentarios")
        cursor.execute("DELETE FROM tarefas")
        cursor.execute("DELETE FROM implantacoes")
        cursor.execute("DELETE FROM perfil_usuario WHERE usuario LIKE 'test%'")
        cursor.execute("DELETE FROM usuarios WHERE usuario LIKE 'test%'")
        conn.commit()
        conn.close()


@pytest.fixture
def client(app):
    """Cria um cliente de teste."""
    return app.test_client()


@pytest.fixture
def auth_client(client, app):
    """Cria um cliente autenticado."""
    with app.app_context():

        from werkzeug.security import generate_password_hash
        
        test_email = 'test@example.com'
        test_password = 'testpassword123'

        execute_db(
            "INSERT OR IGNORE INTO usuarios (usuario, senha) VALUES (?, ?)",
            (test_email, generate_password_hash(test_password))
        )

        execute_db(
            """INSERT OR IGNORE INTO perfil_usuario 
               (usuario, nome, cargo, perfil_acesso) 
               VALUES (?, ?, ?, ?)""",
            (test_email, 'Test User', 'Tester', 'Implantador')
        )
    
    response = client.post('/login', data={
        'email': test_email,
        'password': test_password
    }, follow_redirects=True)
    
    assert response.status_code == 200
    
    return client


class TestImplantacaoFlowIntegration:
    """Testes de integração do fluxo completo de implantação."""
    
    def test_criar_implantacao_completo(self, auth_client, app):
        """Testa o fluxo completo de criação de implantação."""
        with app.app_context():

            response = auth_client.post('/criar_implantacao', data={
                'nome_empresa': 'Empresa Teste Integração',
                'email_responsavel': 'responsavel@teste.com',
                'responsavel_cliente': 'João Silva',
                'usuario_atribuido_cs': 'test@example.com',
                'status': 'andamento'
            }, follow_redirects=True)
            
            assert response.status_code == 200

            impl = query_db(
                "SELECT * FROM implantacoes WHERE nome_empresa = ?",
                ('Empresa Teste Integração',),
                one=True
            )
            
            assert impl is not None
            assert impl['nome_empresa'] == 'Empresa Teste Integração'
            assert impl['status'] == 'andamento'
            
            impl_id = impl['id']

            tarefas = query_db(
                "SELECT * FROM tarefas WHERE implantacao_id = ?",
                (impl_id,)
            )
            
            assert len(tarefas) > 0
            assert any(t['tarefa_pai'] == 'Checklist Obrigatório' for t in tarefas)

            tarefa_id = tarefas[0]['id']
            response = auth_client.post(f'/api/toggle_tarefa/{tarefa_id}')
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['ok'] is True

            tarefa_atualizada = query_db(
                "SELECT * FROM tarefas WHERE id = ?",
                (tarefa_id,),
                one=True
            )
            
            assert tarefa_atualizada['concluida'] == 1
    
    def test_adicionar_comentario_completo(self, auth_client, app):
        """Testa o fluxo completo de adicionar comentário."""
        with app.app_context():

            execute_db(
                """INSERT INTO implantacoes 
                   (nome_empresa, email_responsavel, usuario_cs, status) 
                   VALUES (?, ?, ?, ?)""",
                ('Empresa Comentário', 'resp@teste.com', 'test@example.com', 'andamento')
            )
            
            impl = query_db(
                "SELECT * FROM implantacoes WHERE nome_empresa = ?",
                ('Empresa Comentário',),
                one=True
            )
            impl_id = impl['id']

            execute_db(
                """INSERT INTO tarefas 
                   (implantacao_id, tarefa_pai, tarefa_filho, ordem) 
                   VALUES (?, ?, ?, ?)""",
                (impl_id, 'Módulo Teste', 'Tarefa Teste', 1)
            )
            
            tarefa = query_db(
                "SELECT * FROM tarefas WHERE implantacao_id = ?",
                (impl_id,),
                one=True
            )
            tarefa_id = tarefa['id']

            response = auth_client.post(
                f'/api/adicionar_comentario/{tarefa_id}',
                data={
                    'texto': 'Comentário de teste de integração',
                    'visibilidade': 'interno'
                },
                headers={'HX-Request': 'true'}
            )
            
            assert response.status_code == 200

            comentarios = query_db(
                "SELECT * FROM comentarios WHERE tarefa_id = ?",
                (tarefa_id,)
            )
            
            assert len(comentarios) == 1
            assert comentarios[0]['texto'] == 'Comentário de teste de integração'
        assert comentarios[0]['visibilidade'] == 'interno'

    def test_parar_implantacao_validacao_data(self, auth_client, app):
        with app.app_context():

            execute_db(
                """INSERT INTO implantacoes 
                   (nome_empresa, email_responsavel, usuario_cs, status) 
                   VALUES (?, ?, ?, ?)""",
                ('Empresa Parada', 'resp@teste.com', 'test@example.com', 'andamento')
            )
            impl = query_db(
                "SELECT * FROM implantacoes WHERE nome_empresa = ?",
                ('Empresa Parada',),
                one=True
            )
            impl_id = impl['id']

        resp_ok = auth_client.post('/parar_implantacao', data={
            'implantacao_id': impl_id,
            'motivo_parada': 'Teste de parada',
            'data_parada': '2023-12-25'
        }, follow_redirects=True)
        assert resp_ok.status_code == 200
        with app.app_context():
            upd = query_db("SELECT status, data_finalizacao FROM implantacoes WHERE id = ?", (impl_id,), one=True)
        assert upd['status'] == 'parada'
        assert str(upd['data_finalizacao']).startswith('2023-12-25')

        with app.app_context():
            execute_db("UPDATE implantacoes SET status='andamento', data_finalizacao=NULL WHERE id = ?", (impl_id,))
        resp_br = auth_client.post('/parar_implantacao', data={
            'implantacao_id': impl_id,
            'motivo_parada': 'Teste BR',
            'data_parada': '25/12/2023'
        }, follow_redirects=True)
        assert resp_br.status_code == 200
        with app.app_context():
            upd_br = query_db("SELECT status, data_finalizacao FROM implantacoes WHERE id = ?", (impl_id,), one=True)
        assert upd_br['status'] == 'parada'
        assert str(upd_br['data_finalizacao']).startswith('2023-12-25')

    def test_excluir_implantacao_status_200(self, auth_client, app):
        with app.app_context():

            execute_db(
                """INSERT INTO implantacoes 
                   (nome_empresa, email_responsavel, usuario_cs, status) 
                   VALUES (?, ?, ?, ?)""",
                ('Empresa Excluir', 'resp@teste.com', 'test@example.com', 'andamento')
            )
            impl = query_db("SELECT * FROM implantacoes WHERE nome_empresa = ?", ('Empresa Excluir',), one=True)
            impl_id = impl['id']

        resp = auth_client.post('/excluir_implantacao', data={
            'implantacao_id': impl_id
        }, follow_redirects=True)
        assert resp.status_code == 200
        with app.app_context():
            deleted = query_db("SELECT * FROM implantacoes WHERE id = ?", (impl_id,), one=True)
        assert deleted is None

