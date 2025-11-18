\
\

import pytest
import sys
import os
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))

from project import create_app
from project.db import execute_db


@pytest.fixture
def app():
    """Cria uma instância do app para testes."""
    app = create_app()
    app.config.update({
        'TESTING': True,
        'USE_SQLITE_LOCALLY': True,
        'WTF_CSRF_ENABLED': False,
    })
    
    with app.app_context():
        from project.db import init_db
        init_db()
    
    yield app
    
        \
    with app.app_context():
        from project.db import get_db_connection
        conn, _ = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM implantacoes WHERE usuario_cs = 'apiv1@test.com'")
        cursor.execute("DELETE FROM perfil_usuario WHERE usuario = 'apiv1@test.com'")
        cursor.execute("DELETE FROM usuarios WHERE usuario = 'apiv1@test.com'")
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
        
                \
        execute_db(
            "INSERT OR IGNORE INTO usuarios (usuario, senha) VALUES (?, ?)",
            ('apiv1@test.com', generate_password_hash('testpass'))
        )
        
        execute_db(
            """INSERT OR IGNORE INTO perfil_usuario 
               (usuario, nome, cargo, perfil_acesso) 
               VALUES (?, ?, ?, ?)""",
            ('apiv1@test.com', 'API V1 Test User', 'Tester', 'Implantador')
        )
    
    client.post('/login', data={
        'email': 'apiv1@test.com',
        'password': 'testpass'
    })
    
    return client


class TestAPIv1Health:
    """Testes para health check da API v1."""
    
    def test_health_endpoint(self, client):
        """Testa endpoint de health check."""
        response = client.get('/api/v1/health')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert data['status'] == 'ok'
        assert data['version'] == 'v1'
        assert 'api' in data


class TestAPIv1Implantacoes:
    """Testes para endpoints de implantações da API v1."""
    
    def test_list_implantacoes_sem_autenticacao(self, client):
        """Testa listagem sem autenticação."""
        response = client.get('/api/v1/implantacoes')
        
                \
        assert response.status_code in [302, 401]
    
    def test_list_implantacoes_vazia(self, auth_client):
        """Testa listagem vazia."""
        response = auth_client.get('/api/v1/implantacoes')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert data['ok'] is True
        assert 'data' in data
        assert isinstance(data['data'], list)
        assert 'pagination' in data
    
    def test_list_implantacoes_com_dados(self, auth_client, app):
        """Testa listagem com dados."""
        with app.app_context():
            \
            for i in range(5):
                execute_db(
                    """INSERT INTO implantacoes 
                       (nome_empresa, email_responsavel, usuario_cs, status) 
                       VALUES (?, ?, ?, ?)""",
                    (f'API V1 Test Company {i}', f'test{i}@test.com', 'apiv1@test.com', 'andamento')
                )
        
        response = auth_client.get('/api/v1/implantacoes')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert data['ok'] is True
        assert len(data['data']) >= 5
        assert data['pagination']['total'] >= 5
    
    def test_list_implantacoes_com_paginacao(self, auth_client, app):
        """Testa listagem com paginação."""
        with app.app_context():
            \
            for i in range(15):
                execute_db(
                    """INSERT INTO implantacoes 
                       (nome_empresa, email_responsavel, usuario_cs, status) 
                       VALUES (?, ?, ?, ?)""",
                    (f'API V1 Pagination {i}', f'test{i}@test.com', 'apiv1@test.com', 'andamento')
                )
        
        response1 = auth_client.get('/api/v1/implantacoes?page=1&per_page=10')
        data1 = json.loads(response1.data)
        
        assert data1['ok'] is True
        assert len(data1['data']) == 10
        assert data1['pagination']['page'] == 1
        assert data1['pagination']['per_page'] == 10
        assert data1['pagination']['total'] >= 15
        
                \
        response2 = auth_client.get('/api/v1/implantacoes?page=2&per_page=10')
        data2 = json.loads(response2.data)
        
        assert data2['ok'] is True
        assert len(data2['data']) >= 5
        assert data2['pagination']['page'] == 2
    
    def test_list_implantacoes_com_filtro_status(self, auth_client, app):
        """Testa listagem com filtro de status."""
        with app.app_context():
            \
            execute_db(
                """INSERT INTO implantacoes 
                   (nome_empresa, email_responsavel, usuario_cs, status) 
                   VALUES (?, ?, ?, ?)""",
                ('API V1 Andamento', 'test@test.com', 'apiv1@test.com', 'andamento')
            )
            
            execute_db(
                """INSERT INTO implantacoes 
                   (nome_empresa, email_responsavel, usuario_cs, status) 
                   VALUES (?, ?, ?, ?)""",
                ('API V1 Finalizada', 'test@test.com', 'apiv1@test.com', 'finalizada')
            )
        
        response = auth_client.get('/api/v1/implantacoes?status=andamento')
        data = json.loads(response.data)
        
        assert data['ok'] is True
        \
        for impl in data['data']:
            assert impl['status'] == 'andamento'
    
    def test_get_implantacao_detalhes(self, auth_client, app):
        """Testa detalhes de uma implantação."""
        with app.app_context():
            \
            impl_id = execute_db(
                """INSERT INTO implantacoes 
                   (nome_empresa, email_responsavel, usuario_cs, status) 
                   VALUES (?, ?, ?, ?)""",
                ('API V1 Details Test', 'test@test.com', 'apiv1@test.com', 'andamento')
            )
        
        response = auth_client.get(f'/api/v1/implantacoes/{impl_id}')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert data['ok'] is True
        assert 'data' in data
        assert 'implantacao' in data['data']
        assert 'tarefas' in data['data']
        assert data['data']['implantacao']['id'] == impl_id
    
    def test_get_implantacao_nao_encontrada(self, auth_client):
        """Testa busca de implantação inexistente."""
        response = auth_client.get('/api/v1/implantacoes/999999')
        
        assert response.status_code == 404
        data = json.loads(response.data)
        
        assert data['ok'] is False
        assert 'error' in data

