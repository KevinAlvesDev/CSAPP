import os
import io
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
        email = 'photo_local@example.com'
        pwd = 'pass123456'
        execute_db("INSERT OR IGNORE INTO usuarios (usuario, senha) VALUES (?, ?)", (email, generate_password_hash(pwd)))
        execute_db("INSERT OR IGNORE INTO perfil_usuario (usuario, nome, cargo, perfil_acesso) VALUES (?, ?, ?, ?)", (email, 'User', 'Implantador', 'Implantador'))
    resp = client.post('/login', data={'email': 'photo_local@example.com', 'password': 'pass123456'}, follow_redirects=True)
    assert resp.status_code == 200
    return client


def test_upload_profile_photo_local(auth_client, app):
    with app.app_context():
        img_bytes = io.BytesIO(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDAT\x08\xd7c``\x00\x00\x00\x04\x00\x01m\xe7\x86\x9c\x00\x00\x00\x00IEND\xAEB`\x82")
        data = {
            'nome': 'User',
            'cargo': 'Implantador'
        }
        resp = auth_client.post('/profile/save', data={**data, 'foto': (img_bytes, 'avatar.png')}, content_type='multipart/form-data', follow_redirects=True)
        assert resp.status_code in (200, 302)
        perfil = query_db("SELECT foto_url FROM perfil_usuario WHERE usuario = ?", ('photo_local@example.com',), one=True)
        assert perfil is not None
        url = perfil.get('foto_url')
        assert isinstance(url, str) and url.startswith('/static/uploads/profile/')
        static_path = os.path.join(app.static_folder, url.replace('/static/', ''))
        assert os.path.exists(static_path)

        page = auth_client.get('/profile/')
        assert page.status_code == 200
        html = page.get_data(as_text=True)
        assert url in html

