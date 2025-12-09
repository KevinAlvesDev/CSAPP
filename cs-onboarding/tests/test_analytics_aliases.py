import unittest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.project import create_app
from backend.project.db import init_db, execute_db, query_db
from backend.project.domain.analytics_service import get_analytics_data
from datetime import datetime
from backend.project.domain.gamification_service import get_gamification_report_data


class AnalyticsAliasesTests(unittest.TestCase):
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
            # Seed minimal data with tag and conclusion date
            execute_db("INSERT INTO implantacoes (nome_empresa, email_responsavel, status, usuario_cs) VALUES (%s, %s, %s, %s)", (
                'Empresa Alias', 'alias@example.com', 'andamento', 'tester@example.com'
            ))
            impl = query_db("SELECT id FROM implantacoes ORDER BY id DESC LIMIT 1", one=True)
            impl_id = impl['id']
            # Create a subtarefa completed with tag
            execute_db("INSERT INTO checklist_items (parent_id, title, completed, comment, level, ordem, implantacao_id, obrigatoria, tipo_item, descricao, status, responsavel, tag, data_conclusao) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)", (
                None, 'Tarefa Alias', True, '', 3, 1, impl_id, 0, 'subtarefa', '', 'Concluída', 'tester@example.com', 'Ação interna', '2030-01-01'
            ))
        self.client = self.app.test_client()

    def test_get_analytics_data_aliases(self):
        with self.app.app_context():
            data = get_analytics_data(task_start_date='2029-12-31', task_end_date='2030-01-02')
            self.assertIsInstance(data, dict)

    def test_gamification_sql_aliases(self):
        with self.app.app_context():
            report = get_gamification_report_data(mes=datetime.now().month, ano=datetime.now().year)
            self.assertTrue(isinstance(report, list))


if __name__ == '__main__':
    unittest.main()
