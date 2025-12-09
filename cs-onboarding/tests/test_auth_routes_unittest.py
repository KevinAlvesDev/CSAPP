
import unittest
import sys
import os
from flask import url_for

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from project import create_app
except ImportError:
    # Fallback if running from root
    sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
    from backend.project import create_app

class TestAuthRoutes(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['SERVER_NAME'] = 'localhost' # Required for url_for with _external
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()

    def tearDown(self):
        self.ctx.pop()

    def test_auth_endpoints_existence(self):
        """
        Verifica se todos os endpoints de autenticação críticos estão registrados
        e acessíveis (pelo menos geram URL sem erro).
        """
        expected_endpoints = [
            'auth.login',
            'auth.logout',
            'auth.google_login',
            'auth.google_callback',
            'auth.dev_login',
            'auth.check_user_external'
        ]
        
        print("\nVerificando Endpoints:")
        for endpoint in expected_endpoints:
            try:
                if 'callback' in endpoint:
                     url = url_for(endpoint, _external=True)
                else:
                     url = url_for(endpoint)
                print(f"✅ {endpoint} -> {url}")
                self.assertIsNotNone(url)
            except Exception as e:
                self.fail(f"Endpoint {endpoint} not found or failed to build: {e}")

    def test_google_login_route(self):
        """
        Verifica se a rota /login/google responde.
        """
        # Note: SERVER_NAME adds subdomain/domain matching, so we must use full URL or relative path carefully.
        # Flask test client usually handles relative paths fine, but url_for might return absolute.
        
        # Test route map directly
        rules = [str(p) for p in self.app.url_map.iter_rules()]
        self.assertIn('/login/google', rules)
        self.assertIn('/login/google/callback', rules)

if __name__ == '__main__':
    unittest.main()
