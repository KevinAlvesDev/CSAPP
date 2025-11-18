import pytest
import sys
import os

\
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))

from project import create_app
from project.db import query_db, execute_db


@pytest.fixture
def app():
    app = create_app()
    app.config.update({
        'TESTING': True,
        'USE_SQLITE_LOCALLY': True,
        'WTF_CSRF_ENABLED': False,
        'AUTH0_ENABLED': False,
    })
    with app.app_context():
        from project.db import init_db
        init_db()
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth_client(client, app):
    with app.app_context():
        from werkzeug.security import generate_password_hash
        email = 'test_auto@example.com'
        pwd = 'pass123456'
        execute_db("INSERT OR IGNORE INTO usuarios (usuario, senha) VALUES (?, ?)", (email, generate_password_hash(pwd)))
        execute_db("INSERT OR IGNORE INTO perfil_usuario (usuario, nome, cargo, perfil_acesso) VALUES (?, ?, ?, ?)", (email, 'Tester', 'QA', 'Implantador'))
    resp = client.post('/login', data={'email': 'test_auto@example.com', 'password': 'pass123456'}, follow_redirects=True)
    assert resp.status_code == 200
    return client


def test_excluir_modulo_nao_finaliza_implantacao(auth_client, app):
    with app.app_context():
        execute_db("INSERT INTO implantacoes (nome_empresa, email_responsavel, usuario_cs, status) VALUES (?, ?, ?, ?)",
                   ('Empresa Auto', 'resp@auto.com', 'test_auto@example.com', 'andamento'))
        impl = query_db("SELECT * FROM implantacoes WHERE nome_empresa = ?", ('Empresa Auto',), one=True)
        impl_id = impl['id']

        \
        execute_db("INSERT INTO tarefas (implantacao_id, tarefa_pai, tarefa_filho, ordem, concluida) VALUES (?, ?, ?, ?, ?)", (impl_id, 'Modulo A', 'T1', 1, 1))
        execute_db("INSERT INTO tarefas (implantacao_id, tarefa_pai, tarefa_filho, ordem, concluida) VALUES (?, ?, ?, ?, ?)", (impl_id, 'Modulo A', 'T2', 2, 1))
        execute_db("INSERT INTO tarefas (implantacao_id, tarefa_pai, tarefa_filho, ordem, concluida) VALUES (?, ?, ?, ?, ?)", (impl_id, 'Modulo B', 'T3', 1, 0))
        execute_db("INSERT INTO tarefas (implantacao_id, tarefa_pai, tarefa_filho, ordem, concluida) VALUES (?, ?, ?, ?, ?)", (impl_id, 'Modulo B', 'T4', 2, 0))

        \
        r = auth_client.post('/api/excluir_tarefas_modulo', json={'implantacao_id': impl_id, 'tarefa_pai': 'Modulo B'})
        assert r.status_code == 200
        data = r.get_json()
        assert data['ok'] is True
        assert data['implantacao_finalizada'] is False

        \
        impl_after = query_db("SELECT status FROM implantacoes WHERE id = ?", (impl_id,), one=True)
        assert impl_after['status'] == 'andamento'

