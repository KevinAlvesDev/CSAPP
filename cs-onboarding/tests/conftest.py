"""
Conftest.py — Configuração global de testes para pytest.

Contém fixtures reutilizáveis para:
- Criação de app Flask em modo de teste
- Cliente HTTP de teste
- Banco de dados em memória (SQLite)
- Usuários e perfis de teste
"""

import os
import tempfile

import pytest

# Forçar ambiente de teste ANTES de qualquer import do projeto
os.environ["USE_SQLITE_LOCALLY"] = "True"
os.environ["FLASK_ENV"] = "testing"
os.environ["SECRET_KEY"] = "test-secret-key-do-not-use-in-production"
os.environ["AUTH0_ENABLED"] = "false"
os.environ["DEBUG"] = "True"


@pytest.fixture(scope="session")
def app():
    """Cria uma instância da aplicação Flask para testes."""
    from backend.project import create_app

    # Banco de dados temporário para testes
    db_fd, db_path = tempfile.mkstemp(suffix=".db")

    test_config = {
        "TESTING": True,
        "USE_SQLITE_LOCALLY": True,
        "DATABASE_URL": f"sqlite:///{db_path}",
        "SECRET_KEY": "test-secret-key-do-not-use-in-production",
        "AUTH0_ENABLED": False,
        "WTF_CSRF_ENABLED": False,  # Desabilitar CSRF em testes
        "RATELIMIT_ENABLED": False,
        "SERVER_NAME": "localhost",
    }

    app = create_app(test_config=test_config)

    yield app

    # Cleanup
    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def client(app):
    """Cria um cliente de teste HTTP."""
    with app.test_client() as client:
        yield client


@pytest.fixture
def runner(app):
    """Cria um runner para testar CLI commands."""
    return app.test_cli_runner()


@pytest.fixture
def app_context(app):
    """Fornece um app context para testes que precisam."""
    with app.app_context():
        yield app


@pytest.fixture
def authenticated_client(client, app):
    """Cliente de teste com sessão autenticada como admin."""
    with client.session_transaction() as sess:
        sess["user"] = {
            "email": "admin@admin.com",
            "name": "Administrador",
            "sub": "test|admin",
        }
    return client


@pytest.fixture
def implantador_client(client, app):
    """Cliente de teste com sessão autenticada como implantador."""
    with client.session_transaction() as sess:
        sess["user"] = {
            "email": "implantador@test.com",
            "name": "Implantador Teste",
            "sub": "test|implantador",
        }
    return client
