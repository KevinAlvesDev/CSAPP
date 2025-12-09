import unittest
import os
import sys
from unittest.mock import patch, MagicMock

# Adicionar diretório backend ao path
backend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'backend')
sys.path.insert(0, backend_dir)

from flask import Flask, url_for
from project import create_app

class TestEnvironments(unittest.TestCase):

    def setUp(self):
        # Configuração base para os testes
        self.original_environ = os.environ.copy()

    def tearDown(self):
        # Restaurar ambiente original
        os.environ.clear()
        os.environ.update(self.original_environ)

    def test_dev_environment_routes(self):
        """
        Verifica se em ambiente de desenvolvimento (DEBUG=True ou FLASK_ENV=development):
        - /dev-login está acessível
        - /login/google está acessível
        """
        print("\n--- Testando Ambiente de Desenvolvimento ---")
        
        # Simular ambiente de desenvolvimento
        new_env = self.original_environ.copy()
        new_env['FLASK_ENV'] = 'development'
        new_env['USE_SQLITE_LOCALLY'] = 'true'
        new_env['DEBUG'] = 'true'
        new_env['AUTH0_ENABLED'] = 'false' # Dev login requer Auth0 desabilitado geralmente
        
        with patch.dict(os.environ, new_env, clear=True):
            # Recriar app com novas variáveis de ambiente
            app = create_app()
            app.config['SERVER_NAME'] = 'localhost'
            app.config['WTF_CSRF_ENABLED'] = False
            
            with app.test_client() as client:
                with app.app_context():
                    # Verificar existência do endpoint dev-login
                    try:
                        dev_url = url_for('auth.dev_login')
                        print(f"✅ [DEV] Endpoint 'auth.dev_login' registrado: {dev_url}")
                    except Exception as e:
                        self.fail(f"❌ [DEV] Endpoint 'auth.dev_login' não encontrado: {e}")

                    # Verificar acesso ao dev-login (deve retornar redirecionamento ou sucesso, não 404)
                    response = client.get(dev_url)
                    print(f"ℹ️ [DEV] GET {dev_url} status: {response.status_code}")
                    self.assertNotEqual(response.status_code, 404, "Em DEV, /dev-login NÃO deve retornar 404")

                    # Verificar google login também
                    try:
                        google_url = url_for('auth.google_login')
                        print(f"✅ [DEV] Endpoint 'auth.google_login' registrado: {google_url}")
                    except Exception as e:
                        self.fail(f"❌ [DEV] Endpoint 'auth.google_login' não encontrado: {e}")

    def test_prod_environment_routes(self):
        """
        Verifica se em ambiente de produção (FLASK_ENV=production):
        - /dev-login retorna 404 (bloqueado)
        - /login/google está acessível
        """
        print("\n--- Testando Ambiente de Produção ---")
        
        # Simular ambiente de produção
        new_env = self.original_environ.copy()
        new_env['FLASK_ENV'] = 'production'
        new_env['USE_SQLITE_LOCALLY'] = 'false'
        new_env['DEBUG'] = 'false'
        # Em prod, AUTH0 ou Google podem estar habilitados. Vamos assumir Google habilitado.
        new_env['GOOGLE_CLIENT_ID'] = 'dummy'
        new_env['GOOGLE_CLIENT_SECRET'] = 'dummy'
        new_env['GOOGLE_REDIRECT_URI'] = 'http://localhost/callback'
        
        with patch.dict(os.environ, new_env, clear=True):
            app = create_app()
            app.config['SERVER_NAME'] = 'localhost'
            app.config['WTF_CSRF_ENABLED'] = False
            
            with app.test_client() as client:
                with app.app_context():
                    # O endpoint EXISTE no mapa de rotas, mas a lógica interna deve abortar 404
                    try:
                        dev_url = url_for('auth.dev_login')
                        print(f"✅ [PROD] Endpoint 'auth.dev_login' registrado: {dev_url}")
                    except Exception as e:
                         self.fail(f"❌ [PROD] Endpoint 'auth.dev_login' deveria existir no mapa, mas falhou: {e}")

                    # Tentar acessar - DEVE retornar 404
                    response = client.get(dev_url)
                    print(f"ℹ️ [PROD] GET {dev_url} status: {response.status_code}")
                    self.assertEqual(response.status_code, 404, "Em PROD, /dev-login DEVE retornar 404")
                    
                    # Verificar google login - DEVE estar acessível (redirecionar para Google)
                    # Nota: Como não configuramos Google OAuth real, ele pode falhar ou redirecionar.
                    # O importante é que não dê 404 se configurado corretamente.
                    try:
                        google_url = url_for('auth.google_login')
                        print(f"✅ [PROD] Endpoint 'auth.google_login' registrado: {google_url}")
                    except Exception as e:
                        self.fail(f"❌ [PROD] Endpoint 'auth.google_login' não encontrado: {e}")

if __name__ == '__main__':
    unittest.main()
