import unittest
from unittest.mock import patch
from decimal import Decimal
import sys
import os
from flask import g

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
try:
    from backend.project import create_app
except ImportError:
    from project import create_app

class TestConsultarEmpresa(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.app.config['LOGIN_DISABLED'] = True
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()
        
        # Mock g.user_email for limiter
        @self.app.before_request
        def set_user():
            g.user_email = 'test@example.com'

    def tearDown(self):
        self.ctx.pop()

    @patch('backend.project.database.external_db.query_external_db')
    def test_consultar_empresa_success(self, mock_query):
        # Mock DB response
        mock_query.return_value = [{
            'codigofinanceiro': 123,
            'nomefantasia': 'Empresa Teste',
            'razaosocial': 'Razao Teste',
            'email': 'teste@teste.com',
            'telefone': '123456789',
            'inicioimplantacao': None,
            'nivelreceitamensal': 'Baixo',
            'mrr': Decimal('123.45')
        }]

        response = self.client.get('/api/consultar_empresa?id_favorecido=123')
        data = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(data['ok'])
        self.assertEqual(data['empresa']['nomefantasia'], 'Empresa Teste')
        self.assertEqual(data['empresa']['email'], 'teste@teste.com')
        self.assertEqual(data['empresa']['mrr'], '123.45')

    def test_consultar_empresa_missing_id(self):
        response = self.client.get('/api/consultar_empresa')
        self.assertEqual(response.status_code, 400)

    def test_consultar_empresa_invalid_id(self):
        response = self.client.get('/api/consultar_empresa?id_favorecido=abc')
        self.assertEqual(response.status_code, 400)

    @patch('backend.project.database.external_db.query_external_db')
    def test_consultar_empresa_not_found(self, mock_query):
        mock_query.return_value = []
        response = self.client.get('/api/consultar_empresa?id_favorecido=999')
        self.assertEqual(response.status_code, 404)
        data = response.get_json()
        self.assertFalse(data['ok'])
        self.assertIn('Empresa não encontrada', data['error'])

    @patch('backend.project.database.external_db.query_external_db')
    def test_consultar_empresa_db_error(self, mock_query):
        mock_query.side_effect = Exception("DB Error")
        response = self.client.get('/api/consultar_empresa?id_favorecido=123')
        self.assertEqual(response.status_code, 500)
        data = response.get_json()
        self.assertFalse(data['ok'])
        self.assertIn('Erro ao consultar banco de dados externo', data['error'])

    @patch('backend.project.database.external_db.query_external_db')
    def test_consultar_empresa_timeout(self, mock_query):
        from sqlalchemy.exc import OperationalError
        # Mock raising OperationalError with timeout message
        mock_query.side_effect = OperationalError("connection timed out", params=None, orig=Exception("Timeout"))
        
        response = self.client.get('/api/consultar_empresa?id_favorecido=123')
        self.assertEqual(response.status_code, 504)
        data = response.get_json()
        self.assertFalse(data['ok'])
        self.assertIn('Tempo limite excedido', data['error'])

if __name__ == '__main__':
    unittest.main()
