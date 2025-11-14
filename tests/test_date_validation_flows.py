import io
import pytest
import sys
import os
from datetime import date

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
        'R2_CONFIGURADO': True,
        'CLOUDFLARE_BUCKET_NAME': 'test-bucket',
        'CLOUDFLARE_PUBLIC_URL': 'https://example.com'
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
        test_email = 'testdate@example.com'
        execute_db(
            "INSERT OR IGNORE INTO usuarios (usuario, senha) VALUES (?, ?)",
            (test_email, generate_password_hash('password123'))
        )
        execute_db(
            """INSERT OR IGNORE INTO perfil_usuario (usuario, nome, cargo, perfil_acesso)
                VALUES (?, ?, ?, ?)""",
            (test_email, 'Tester', 'Tester', 'Implantador')
        )
    resp = client.post('/login', data={'email': test_email, 'password': 'password123'}, follow_redirects=True)
    assert resp.status_code == 200
    return client


def _create_impl_andamento(app):
    with app.app_context():
        execute_db(
            """INSERT INTO implantacoes (nome_empresa, email_responsavel, usuario_cs, status)
                VALUES (?, ?, ?, ?)""",
            ('Empresa Datas', 'resp@teste.com', 'testdate@example.com', 'andamento')
        )
        impl = query_db("SELECT * FROM implantacoes WHERE nome_empresa = ?", ('Empresa Datas',), one=True)
        return impl['id']


def test_parar_implantacao_multiplos_formatos(auth_client, app):
    formats = [
        '2024-01-15',
        '15/01/2024',
        '01/15/2024',
        '2024-01-15T00:00:00Z',
        '2024-01-15T23:00:00-03:00'
    ]
    for d in formats:
        impl_id = _create_impl_andamento(app)
        resp = auth_client.post('/parar_implantacao', data={
            'implantacao_id': impl_id,
            'motivo_parada': 'Teste formatos',
            'data_parada': d
        }, follow_redirects=True)
        assert resp.status_code == 200
        txt = resp.get_data(as_text=True)
        assert 'Implantação marcada como "Parada"' in txt or 'Parada' in txt
        with app.app_context():
            row = query_db("SELECT status, data_finalizacao FROM implantacoes WHERE id = ?", (impl_id,), one=True)
        assert row['status'] == 'parada'


def test_parar_implantacao_timezone_normalizacao(auth_client, app):
    impl_id = _create_impl_andamento(app)
    with app.app_context():
        execute_db("UPDATE implantacoes SET status='andamento', data_finalizacao=NULL WHERE id = ?", (impl_id,))
    resp = auth_client.post('/parar_implantacao', data={
        'implantacao_id': impl_id,
        'motivo_parada': 'Teste TZ 1',
        'data_parada': '2024-01-15T02:00:00-03:00'
    }, follow_redirects=True)
    assert resp.status_code == 200
    with app.app_context():
        r1 = query_db("SELECT data_finalizacao FROM implantacoes WHERE id = ?", (impl_id,), one=True)
    assert str(r1['data_finalizacao']).startswith('2024-01-15')

    with app.app_context():
        execute_db("UPDATE implantacoes SET status='andamento', data_finalizacao=NULL WHERE id = ?", (impl_id,))
    resp2 = auth_client.post('/parar_implantacao', data={
        'implantacao_id': impl_id,
        'motivo_parada': 'Teste TZ 2',
        'data_parada': '2024-01-15T23:00:00-03:00'
    }, follow_redirects=True)
    assert resp2.status_code == 200
    with app.app_context():
        r2 = query_db("SELECT data_finalizacao FROM implantacoes WHERE id = ?", (impl_id,), one=True)
    assert str(r2['data_finalizacao']).startswith('2024-01-16')


def test_cancelar_implantacao_multiplos_formatos(auth_client, app, monkeypatch):
    class FakeR2:
        def upload_fileobj(self, f, bucket, key, ExtraArgs=None):
            return None

    import project.blueprints.implantacao_actions as actions_mod
    monkeypatch.setattr(actions_mod, 'r2_client', FakeR2())

    with app.app_context():
        execute_db(
            """INSERT INTO implantacoes (nome_empresa, email_responsavel, usuario_cs, status)
                VALUES (?, ?, ?, ?)""",
            ('Empresa Cancel', 'resp@teste.com', 'testdate@example.com', 'andamento')
        )
        impl = query_db("SELECT * FROM implantacoes WHERE nome_empresa = ?", ('Empresa Cancel',), one=True)
        impl_id = impl['id']

    data_variants = ['2024-02-10', '10/02/2024', '02/10/2024']
    for d in data_variants:
        f = (io.BytesIO(b"fake data"), 'comprovante.pdf')
        resp = auth_client.post('/cancelar_implantacao', data={
            'implantacao_id': impl_id,
            'data_cancelamento': d,
            'motivo_cancelamento': 'Teste',
            'comprovante_cancelamento': f
        }, content_type='multipart/form-data', follow_redirects=True)
        assert resp.status_code == 200
        txt = resp.get_data(as_text=True)
        assert 'Implantação cancelada com sucesso.' in txt or 'cancelada' in txt
        with app.app_context():
            row = query_db("SELECT status, data_cancelamento FROM implantacoes WHERE id = ?", (impl_id,), one=True)
        assert row['status'] == 'cancelada'


def test_mensagens_erro_datas_invalidas_parar(auth_client, app):
    impl_id = _create_impl_andamento(app)
    resp = auth_client.post('/parar_implantacao', data={
        'implantacao_id': impl_id,
        'motivo_parada': 'Teste',
        'data_parada': '31/02/2024'
    }, follow_redirects=True)
    assert resp.status_code == 200
    assert 'Formatos aceitos: DD/MM/AAAA, MM/DD/AAAA, AAAA-MM-DD' in resp.get_data(as_text=True)