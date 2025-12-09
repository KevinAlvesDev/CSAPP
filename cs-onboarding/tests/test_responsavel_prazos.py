import unittest
from flask import Flask
from backend.project import create_app
from backend.project.db import init_db, query_db, execute_db

class ResponsavelPrazosTests(unittest.TestCase):
    def setUp(self):
        os.environ['FLASK_ENV'] = 'development'
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['USE_SQLITE_LOCALLY'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.app.config['AUTH0_ENABLED'] = False
        self.app.config['DEBUG'] = True
        with self.app.app_context():
            init_db()
        self.client = self.app.test_client()
        # login dev
        self.client.post('/dev-login-as', data={'email': 'tester@example.com', 'name': 'Tester'})

    def test_apply_plan_sets_responsavel_and_previsao(self):
        with self.app.app_context():
            execute_db("INSERT OR IGNORE INTO usuarios (usuario, senha) VALUES (?, ?)", ("tester@example.com", "x"))
            execute_db("INSERT OR IGNORE INTO perfil_usuario (usuario, nome) VALUES (?, ?)", ("tester@example.com", "Tester"))
            execute_db("INSERT INTO implantacoes (usuario_cs, nome_empresa) VALUES (?, ?)", ("tester@example.com", "Empresa X"))
            impl = query_db("SELECT id FROM implantacoes ORDER BY id DESC LIMIT 1", one=True)
            impl_id = impl['id']
            execute_db("INSERT INTO planos_sucesso (nome, criado_por, dias_duracao) VALUES (?, ?, ?)", ("Plano A", "tester@example.com", 10))
            plano = query_db("SELECT id FROM planos_sucesso ORDER BY id DESC LIMIT 1", one=True)
            plano_id = plano['id']
            execute_db("INSERT INTO checklist_items (title, implantacao_id, plano_id, ordem, tipo_item) VALUES (?, NULL, ?, ?, ?)", ("Tarefa 1", plano_id, 1, "plano_tarefa"))
            rv = self.client.post(f"/planos/implantacao/{impl_id}/aplicar", json={"plano_id": plano_id})
            self.assertEqual(rv.status_code, 200)
            items = query_db("SELECT responsavel, previsao_original FROM checklist_items WHERE implantacao_id = ?", (impl_id,))
            self.assertTrue(len(items) >= 1)
            self.assertIsNotNone(items[0]['responsavel'])
    
    def test_update_responsavel_history(self):
        with self.app.app_context():
            item = query_db("SELECT id FROM checklist_items ORDER BY id DESC LIMIT 1", one=True)
            item_id = item['id']
            rv = self.client.patch(f"/api/checklist/item/{item_id}/responsavel", json={"responsavel": "novo@resp.com"})
            self.assertEqual(rv.status_code, 200)
            hist = query_db("SELECT COUNT(*) as c FROM checklist_responsavel_history WHERE checklist_item_id = ?", (item_id,), one=True)
            self.assertTrue(hist['c'] >= 1)

    def test_update_nova_previsao(self):
        with self.app.app_context():
            item = query_db("SELECT id FROM checklist_items ORDER BY id DESC LIMIT 1", one=True)
            item_id = item['id']
            rv = self.client.patch(f"/api/checklist/item/{item_id}/prazos", json={"nova_previsao": "2025-12-31"})
            self.assertEqual(rv.status_code, 200)
            item2 = query_db("SELECT nova_previsao FROM checklist_items WHERE id = ?", (item_id,), one=True)
            self.assertIsNotNone(item2['nova_previsao'])

if __name__ == '__main__':
    unittest.main()
import os
