import unittest
from unittest.mock import patch, MagicMock
import sys
import os
from flask import g

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
try:
    from backend.project import create_app
except ImportError:
    from project import create_app

class TestCriarImplantacao(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()
        
        # Mock g.user_email and g.perfil for login/permission checks
        @self.app.before_request
        def set_user():
            g.user_email = 'test@example.com'
            g.perfil = {'perfil_acesso': 'Administrador', 'nome': 'Test Admin'}

    def tearDown(self):
        self.ctx.pop()

    @patch('backend.project.blueprints.main.query_db')
    @patch('backend.project.blueprints.main.get_dashboard_data')
    @patch('backend.project.blueprints.implantacao_actions.query_db')
    @patch('backend.project.blueprints.implantacao_actions.execute_and_fetch_one')
    @patch('backend.project.blueprints.implantacao_actions.logar_timeline')
    def test_criar_implantacao_missing_id_favorecido(self, mock_log, mock_exec, mock_query, mock_get_dashboard, mock_main_query):
        # Mock duplicate check returns None (no duplicate)
        mock_query.return_value = None

        # Use follow_redirects=False to check the flash message in session
        response = self.client.post('/criar_implantacao', data={
            'nome_empresa': 'Nova Empresa',
            'usuario_atribuido_cs': 'user2@example.com'
            # Missing id_favorecido
        }, follow_redirects=False)

        # Should redirect
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.location.endswith('/dashboard'))
        
        # Check flash message in session
        with self.client.session_transaction() as sess:
            flashes = sess.get('_flashes', [])
            # Flashes are stored as list of (category, message) tuples
            found = False
            for cat, msg in flashes:
                if 'ID Favorecido é obrigatório' in msg:
                    found = True
                    break
            self.assertTrue(found, f"Flash message not found. Flashes: {flashes}")
        
        # Ensure insert was NOT called
        mock_exec.assert_not_called()

    @patch('backend.project.blueprints.main.query_db')
    @patch('backend.project.blueprints.main.get_dashboard_data')
    @patch('backend.project.blueprints.implantacao_actions.query_db')
    @patch('backend.project.blueprints.implantacao_actions.execute_and_fetch_one')
    @patch('backend.project.blueprints.implantacao_actions.logar_timeline')
    def test_criar_implantacao_success(self, mock_log, mock_exec, mock_query, mock_get_dashboard, mock_main_query):
        # Mock dashboard data to avoid errors during redirect
        mock_get_dashboard.return_value = ({
            'andamento': [], 'novas': [], 'futuras': [], 'sem_previsao': [],
            'finalizadas': [], 'paradas': []
        }, {})
        mock_main_query.return_value = [] # For _get_all_cs_users

        # Mock duplicate check returns None
        mock_query.return_value = None
        
        # Mock insert return
        mock_exec.return_value = {'id': 100}

        response = self.client.post('/criar_implantacao', data={
            'nome_empresa': 'Nova Empresa',
            'usuario_atribuido_cs': 'user2@example.com',
            'id_favorecido': '12345'
        }, follow_redirects=False)

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.location.endswith('/dashboard'))

        # Check flash message
        with self.client.session_transaction() as sess:
            flashes = sess.get('_flashes', [])
            found = False
            for cat, msg in flashes:
                if 'criada com sucesso' in msg:
                    found = True
                    break
            self.assertTrue(found, f"Success flash message not found. Flashes: {flashes}")
        
        # Ensure insert was called with id_favorecido
        args, _ = mock_exec.call_args
        query = args[0]
        params = args[1]
        self.assertIn('id_favorecido', query)
        self.assertIn(12345, params) # Should be integer
        args, _ = mock_exec.call_args
        query = args[0]
        params = args[1]
        self.assertIn('id_favorecido', query)
        self.assertIn(12345, params) # Should be integer

if __name__ == '__main__':
    unittest.main()