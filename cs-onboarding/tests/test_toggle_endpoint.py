import unittest
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.project import create_app
from backend.project.db import init_db, query_db
from backend.project.domain.planos_sucesso_service import (
    criar_plano_sucesso_checklist,
    aplicar_plano_a_implantacao_checklist,
)


class ToggleEndpointTests(unittest.TestCase):
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
            from backend.project.db import execute_db
            execute_db("DELETE FROM implantacoes")
            execute_db("DELETE FROM checklist_items")
            execute_db("DELETE FROM comentarios_h")
            # Implantação mínima
            execute_db(
                "INSERT INTO implantacoes (nome_empresa, email_responsavel, status, usuario_cs) VALUES (%s, %s, %s, %s)",
                ('Empresa Teste', 'resp@example.com', 'em_andamento', 'tester@example.com')
            )
            impl = query_db("SELECT id FROM implantacoes ORDER BY id DESC LIMIT 1", one=True)
            self.impl_id = impl['id']

            estrutura = {
                'items': [
                    {
                        'title': 'Fase 1',
                        'children': [
                            {
                                'title': 'Grupo 1',
                                'children': [
                                    {'title': 'Tarefa 1'}
                                ]
                            }
                        ]
                    }
                ]
            }
            plano_id = criar_plano_sucesso_checklist('Plano Auto', 'Teste', 'tester@example.com', estrutura=estrutura, dias_duracao=10)
            aplicar_plano_a_implantacao_checklist(self.impl_id, plano_id, 'tester@example.com')

            item = query_db(
                "SELECT id FROM checklist_items WHERE implantacao_id = %s AND tipo_item IN ('tarefa','subtarefa') ORDER BY id LIMIT 1",
                (self.impl_id,),
                one=True
            )
            self.item_id = item['id']

        self.client = self.app.test_client()

    def test_toggle_with_invalid_json_body(self):
        resp = self.client.post(f"/api/checklist/toggle/{self.item_id}", data="{", headers={'Content-Type': 'application/json'})
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data.get('ok'))
        self.assertIn('completed', data)

    def test_toggle_with_string_boolean(self):
        resp = self.client.post(f"/api/checklist/toggle/{self.item_id}", json={'completed': 'false'})
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data.get('ok'))
        self.assertEqual(data.get('completed'), False)


if __name__ == '__main__':
    unittest.main()

