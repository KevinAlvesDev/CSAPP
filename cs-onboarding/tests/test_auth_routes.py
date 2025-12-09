
import pytest
from flask import url_for

def test_auth_endpoints_existence(client):
    """
    Verifica se todos os endpoints de autenticação críticos estão registrados
    e acessíveis (pelo menos geram URL sem erro).
    """
    # Lista de endpoints esperados
    expected_endpoints = [
        'auth.login',
        'auth.logout',
        'auth.google_login',
        'auth.google_callback',
        'auth.dev_login',
        'auth.check_user_external'
    ]
    
    # Verifica se cada endpoint pode ter sua URL construída
    # Isso confirma que estão no url_map
    with client.application.test_request_context():
        for endpoint in expected_endpoints:
            try:
                if 'callback' in endpoint:
                     url = url_for(endpoint, _external=True)
                else:
                     url = url_for(endpoint)
                assert url is not None
                print(f"Endpoint verified: {endpoint} -> {url}")
            except Exception as e:
                pytest.fail(f"Endpoint {endpoint} not found or failed to build: {e}")

def test_google_login_redirect(client):
    """
    Verifica se a rota de login do Google tenta redirecionar.
    Nota: Pode falhar se o Google OAuth não estiver configurado no ambiente de teste,
    mas valida que a rota existe e executa código.
    """
    response = client.get('/login/google')
    # Se não configurado, deve redirecionar para login ou dar erro flash, mas não 404
    assert response.status_code in [302, 200]

def test_auth_blueprint_prefix(client):
    """
    Verifica se o blueprint de auth não tem prefixo duplicado ou incorreto.
    """
    with client.application.test_request_context():
        # O padrão é /login, não /auth/login, pois o blueprint geralmente é registrado na raiz ou com prefixo vazio
        # Verificando o registro real
        rules = [str(p) for p in client.application.url_map.iter_rules()]
        
        # Baseado no debug_routes anterior, parece que as rotas estão na raiz (/login, /logout)
        # ou o blueprint não tem prefixo. Vamos verificar a rota exata.
        assert '/login/google' in rules
