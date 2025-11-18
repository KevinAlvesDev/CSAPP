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
        email = 'nova@example.com'
        pwd = 'pass123456'
        execute_db("INSERT OR IGNORE INTO usuarios (usuario, senha) VALUES (?, ?)", (email, generate_password_hash(pwd)))
        execute_db("INSERT OR IGNORE INTO perfil_usuario (usuario, nome, cargo, perfil_acesso) VALUES (?, ?, ?, ?)", (email, 'User', 'Implantador', 'Implantador'))
        execute_db("INSERT INTO implantacoes (nome_empresa, email_responsavel, usuario_cs, status) VALUES (?, ?, ?, ?)",
                   ('Empresa Nova', 'resp@nova.com', email, 'nova'))
    resp = client.post('/login', data={'email': 'nova@example.com', 'password': 'pass123456'}, follow_redirects=True)
    assert resp.status_code == 200
    return client


def test_cancelar_indisponivel_para_nova(auth_client, app):
    with app.app_context():
        impl = query_db("SELECT * FROM implantacoes WHERE nome_empresa = ?", ('Empresa Nova',), one=True)
        impl_id = impl['id']
        r = auth_client.post('/cancelar_implantacao', data={
            'implantacao_id': impl_id,
            'data_cancelamento': '01/01/2025',
            'motivo_cancelamento': 'Teste'
        }, follow_redirects=True)
        assert r.status_code == 200
        impl2 = query_db("SELECT status FROM implantacoes WHERE id = ?", (impl_id,), one=True)
        assert impl2['status'] == 'nova'

