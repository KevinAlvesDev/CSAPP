import unittest
from unittest.mock import patch
import sys
import os
from flask import g
from datetime import date

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
try:
    from backend.project import create_app
except ImportError:
    from project import create_app

class TestModalDateMapping(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.app.config['LOGIN_DISABLED'] = True
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()
        
        @self.app.before_request
        def set_user():
            g.user_email = 'test@example.com'

    def tearDown(self):
        self.ctx.pop()

    @patch('backend.project.database.external_db.query_external_db')
    def test_field_mapping(self, mock_query):
        # Mock DB response with various field name possibilities
        mock_query.return_value = [{
            'codigofinanceiro': 123,
            'iniciodeproducao': '2023-01-01', # The one requested
            'inicio_implantacao': '2023-02-01',
            'finalimplantacao': '2023-03-01',
            'status': 'Em Andamento',
            'nivelatendimento': 'Ouro',
            'nivelreceita': 'Alta'
        }]

        response = self.client.get('/api/consultar_empresa?id_favorecido=123')
        data = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(data['ok'])
        
        mapped = data['mapped']
        self.assertEqual(mapped['data_inicio_producao'], '2023-01-01')
        self.assertEqual(mapped['data_inicio_efetivo'], '2023-02-01')
        self.assertEqual(mapped['data_final_implantacao'], '2023-03-01')
        self.assertEqual(mapped['status_implantacao'], 'Em Andamento')
        self.assertEqual(mapped['nivel_atendimento'], 'Ouro')
        self.assertEqual(mapped['nivel_receita'], 'Alta')

    @patch('backend.project.database.external_db.query_external_db')
    def test_field_mapping_alternatives(self, mock_query):
        # Test alternative field names
        mock_query.return_value = [{
            'codigofinanceiro': 123,
            'dt_inicio_producao': '2023-01-01',
            'dataimplantacao': '2023-02-01',
            'dt_final_implantacao': '2023-03-01',
        }]

        response = self.client.get('/api/consultar_empresa?id_favorecido=123')
        data = response.get_json()
        
        mapped = data['mapped']
        self.assertEqual(mapped['data_inicio_producao'], '2023-01-01')
        self.assertEqual(mapped['data_inicio_efetivo'], '2023-02-01')
        self.assertEqual(mapped['data_final_implantacao'], '2023-03-01')

if __name__ == '__main__':
    unittest.main()
