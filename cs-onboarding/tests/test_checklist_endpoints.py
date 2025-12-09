import unittest
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.project import create_app
from backend.project.db import init_db, query_db

class ChecklistEndpointsTests(unittest.TestCase):
    def setUp(self):
        os.environ['FLASK_ENV'] = 'development'
        self.app = create_app({
            'TESTING': True,
            'USE_SQLITE_LOCALLY': True,
            'WTF_CSRF_ENABLED': False,
            'AUTH0_ENABLED': False,
            'DEBUG': True,
        })
        with self.app.app_context():
            init_db()
        self.client = self.app.test_client()

    def test_list_users_endpoint(self):
        resp = self.client.get('/api/checklist/users')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data.get('ok'))
        self.assertIsInstance(data.get('users'), list)

    def test_prazos_history_flow(self):
        # Preparar implantação e plano mínimo
        with self.app.app_context():
            # Criar implantação simples
            query_db("DELETE FROM implantacoes")
            from backend.project.db import execute_db
            execute_db("INSERT INTO implantacoes (nome_empresa, email_responsavel, status, usuario_cs) VALUES (%s, %s, %s, %s)", (
                'Empresa Teste', 'resp@example.com', 'em_andamento', 'tester@example.com'
            ))
            impl = query_db("SELECT id FROM implantacoes ORDER BY id DESC LIMIT 1", one=True)
            impl_id = impl['id']

            # Criar plano com uma tarefa
            from backend.project.domain.planos_sucesso_service import criar_plano_sucesso_checklist, aplicar_plano_a_implantacao_checklist
            estrutura = {
                'items': [
                    {
                        'title': 'Fase 1',
                        'children': [
                            {
                                'title': 'Grupo 1',
                                'children': [
                                    { 'title': 'Tarefa 1' }
                                ]
                            }
                        ]
                    }
                ]
            }
            plano_id = criar_plano_sucesso_checklist('Plano Auto', 'Teste', 'tester@example.com', estrutura=estrutura, dias_duracao=10)
            aplicar_plano_a_implantacao_checklist(impl_id, plano_id, 'tester@example.com')

            # Encontrar um item folha para alterar prazo
            item = query_db("SELECT id FROM checklist_items WHERE implantacao_id = %s AND tipo_item IN ('tarefa','subtarefa') ORDER BY id LIMIT 1", (impl_id,), one=True)
            item_id = item['id']

        # Alterar prazo
        resp = self.client.patch(f'/api/checklist/item/{item_id}/prazos', json={'nova_previsao': '2030-01-01'})
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data.get('ok'))
        self.assertEqual(data.get('item_id'), item_id)

        # Consultar histórico
        hist = self.client.get(f'/api/checklist/item/{item_id}/prazos/history')
        self.assertEqual(hist.status_code, 200)
        hist_data = hist.get_json()
        self.assertTrue(hist_data.get('ok'))
        self.assertIsInstance(hist_data.get('history'), list)
        self.assertIsInstance(hist_data.get('history'), list)

if __name__ == '__main__':
    unittest.main()
