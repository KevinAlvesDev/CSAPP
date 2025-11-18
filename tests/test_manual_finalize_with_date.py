import os
import sys
import pytest
from datetime import datetime

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
        email = 'final_date@example.com'
        pwd = 'pass123456'
        execute_db("INSERT OR IGNORE INTO usuarios (usuario, senha) VALUES (?, ?)", (email, generate_password_hash(pwd)))
        execute_db("INSERT OR IGNORE INTO perfil_usuario (usuario, nome, cargo, perfil_acesso) VALUES (?, ?, ?, ?)", (email, 'User', 'Implantador', 'Implantador'))
        execute_db("INSERT INTO implantacoes (nome_empresa, email_responsavel, usuario_cs, status) VALUES (?, ?, ?, ?)",
                   ('Empresa Fin', 'resp@fin.com', email, 'andamento'))
        impl = query_db("SELECT * FROM implantacoes WHERE nome_empresa = ?", ('Empresa Fin',), one=True)
        impl_id = impl['id']
        \
        execute_db("INSERT INTO tarefas (implantacao_id, tarefa_pai, tarefa_filho, ordem, concluida) VALUES (?, ?, ?, ?, ?)", (impl_id, 'Treinamentos', 'T1', 1, 1))
        execute_db("INSERT INTO tarefas (implantacao_id, tarefa_pai, tarefa_filho, ordem, concluida) VALUES (?, ?, ?, ?, ?)", (impl_id, 'Treinamentos', 'T2', 2, 1))
    resp = client.post('/login', data={'email': 'final_date@example.com', 'password': 'pass123456'}, follow_redirects=True)
    assert resp.status_code == 200
    return client


def test_manual_finalize_sets_provided_date(auth_client, app):
    with app.app_context():
        impl = query_db("SELECT * FROM implantacoes WHERE nome_empresa = ?", ('Empresa Fin',), one=True)
        impl_id = impl['id']
        r = auth_client.post('/finalizar_implantacao', data={
            'implantacao_id': impl_id,
            'redirect_to': 'dashboard',
            'data_finalizacao': '01/10/2025'
        }, follow_redirects=True)
        assert r.status_code == 200
        impl2 = query_db("SELECT status, data_finalizacao FROM implantacoes WHERE id = ?", (impl_id,), one=True)
        assert impl2['status'] == 'finalizada'
        dt = impl2['data_finalizacao']
        if isinstance(dt, str):
            assert dt.startswith('2025-10-01')
        elif isinstance(dt, datetime):
            assert dt.date().isoformat() == '2025-10-01'


def test_100_percent_does_not_finalize_automatically(auth_client, app):
    with app.app_context():
        \
        execute_db("INSERT INTO implantacoes (nome_empresa, email_responsavel, usuario_cs, status) VALUES (?, ?, ?, ?)",
                   ('Empresa 100', 'resp@100.com', 'final_date@example.com', 'andamento'))
        impl = query_db("SELECT * FROM implantacoes WHERE nome_empresa = ?", ('Empresa 100',), one=True)
        impl_id = impl['id']
        execute_db("INSERT INTO tarefas (implantacao_id, tarefa_pai, tarefa_filho, ordem, concluida) VALUES (?, ?, ?, ?, ?)", (impl_id, 'Treinamentos', 'T1', 1, 1))
        execute_db("INSERT INTO tarefas (implantacao_id, tarefa_pai, tarefa_filho, ordem, concluida) VALUES (?, ?, ?, ?, ?)", (impl_id, 'Treinamentos', 'T2', 2, 1))
        impl3 = query_db("SELECT status FROM implantacoes WHERE id = ?", (impl_id,), one=True)
        assert impl3['status'] == 'andamento'
