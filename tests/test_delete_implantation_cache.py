import os
import sys
import pytest

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
        email = 'del_cache@example.com'
        pwd = 'pass123456'
        execute_db("INSERT OR IGNORE INTO usuarios (usuario, senha) VALUES (?, ?)", (email, generate_password_hash(pwd)))
        execute_db("INSERT OR IGNORE INTO perfil_usuario (usuario, nome, cargo, perfil_acesso) VALUES (?, ?, ?, ?)", (email, 'User', 'Implantador', 'Implantador'))
    resp = client.post('/login', data={'email': 'del_cache@example.com', 'password': 'pass123456'}, follow_redirects=True)
    assert resp.status_code == 200
    return client


def test_delete_implantation_clears_dashboard_cache(auth_client, app):
    with app.app_context():
        execute_db("INSERT INTO implantacoes (nome_empresa, email_responsavel, usuario_cs, status) VALUES (?, ?, ?, ?)",
                   ('Empresa Del', 'resp@del.com', 'del_cache@example.com', 'andamento'))
        impl = query_db("SELECT * FROM implantacoes WHERE nome_empresa = ?", ('Empresa Del',), one=True)
        impl_id = impl['id']

        resp = auth_client.post('/excluir_implantacao', data={'implantacao_id': impl_id}, follow_redirects=True)
        assert resp.status_code == 200

        impl_after = query_db("SELECT * FROM implantacoes WHERE id = ?", (impl_id,), one=True)
        assert impl_after is None

