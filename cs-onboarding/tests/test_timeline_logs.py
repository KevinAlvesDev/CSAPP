import unittest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.project import create_app
from backend.project.db import init_db, execute_db, query_db

class TimelineLogsTests(unittest.TestCase):
    def setUp(self):
        os.environ['FLASK_ENV'] = 'development'
        self.app = create_app({
            'TESTING': True,
            'USE_SQLITE_LOCALLY': True,
            'WTF_CSRF_ENABLED': False,
            'AUTH0_ENABLED': False,
            'DEBUG': True,
            'LOG_ROTATION_ENABLED': False
        })
        with self.app.app_context():
            init_db()
            execute_db("DELETE FROM implantacoes")
            execute_db("DELETE FROM timeline_log")
            execute_db("DELETE FROM checklist_items")
        self.client = self.app.test_client()
        self.client.get('/dev-login')

    def test_events_and_related_item_id(self):
        with self.app.app_context():
            execute_db("INSERT INTO implantacoes (nome_empresa, email_responsavel, status, usuario_cs) VALUES (%s, %s, %s, %s)", (
                'Empresa TL', 'resp@example.com', 'andamento', 'tester@example.com'
            ))
            impl = query_db("SELECT id FROM implantacoes ORDER BY id DESC LIMIT 1", one=True)
            impl_id = impl['id']
            # criar tarefa/subtarefa
            execute_db("INSERT INTO checklist_items (title, implantacao_id, tipo_item, level, ordem, completed, status) VALUES (%s, %s, %s, %s, %s, %s, %s)", (
                'Tarefa H', impl_id, 'tarefa', 2, 1, False, 'pendente'
            ))
            tarefa = query_db("SELECT id FROM checklist_items WHERE implantacao_id = %s AND tipo_item='tarefa'", (impl_id,), one=True)
            tarefa_id = tarefa['id']

            # toggle tarefa (gera log tarefa_alterada com id)
            self.client.post(f'/api/toggle_tarefa_h/{tarefa_id}')

            # adicionar comentário (gera novo_comentario)
            execute_db("INSERT INTO checklist_items (title, implantacao_id, tipo_item, level, ordem, completed, status) VALUES (%s, %s, %s, %s, %s, %s, %s)", (
                'Subtarefa', impl_id, 'subtarefa', 3, 1, False, 'pendente'
            ))
            sub = query_db("SELECT id FROM checklist_items WHERE implantacao_id = %s AND tipo_item='subtarefa'", (impl_id,), one=True)
            sub_id = sub['id']
            from backend.project.db import logar_timeline
            logar_timeline(impl_id, 'tester@example.com', 'novo_comentario', f"Item {sub_id} comentário criado")

            # carregar detalhes e timeline
            from backend.project.domain.implantacao_service import get_implantacao_details
            details = get_implantacao_details(impl_id, 'tester@example.com', {'nome': 'Tester'})
            logs = details['logs_timeline']
            self.assertTrue(isinstance(logs, list))
            self.assertGreaterEqual(len(logs), 2)
            # validar related_item_id presente em ao menos um
            has_related = any(l.get('related_item_id') for l in logs)
            self.assertTrue(has_related)

if __name__ == '__main__':
    unittest.main()
