import unittest
import os
import sys
import uuid
from datetime import datetime

# Adiciona o diretório pai ao path para importar o backend
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.project import create_app
from backend.project.db import get_db_connection


class TestCommentsAndTagsBehavior(unittest.TestCase):
    def setUp(self):
        self.db_filename = f'test_db_{uuid.uuid4()}.sqlite'
        self.db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), self.db_filename))

        self.app = create_app({
            'TESTING': True,
            'USE_SQLITE_LOCALLY': True,
            'DATABASE_URL': f'sqlite:///{self.db_path}',
            'WTF_CSRF_ENABLED': False,
            'AUTH0_CLIENT_ID': 'mock_client_id',
            'AUTH0_CLIENT_SECRET': 'mock_client_secret',
            'AUTH0_DOMAIN': 'mock_domain',
            'SECRET_KEY': 'mock_secret_key'
        })
        self.client = self.app.test_client()

        with self.app.app_context():
            self._init_db()

        # Autenticação simulada
        with self.client.session_transaction() as sess:
            sess['user'] = {'email': 'test@example.com', 'name': 'Test User'}
            sess['user_email'] = 'test@example.com'
            sess['logged_in'] = True
            sess['is_manager'] = True

    def tearDown(self):
        if os.path.exists(self.db_path):
            try:
                os.remove(self.db_path)
            except (PermissionError, OSError):
                pass

    def _init_db(self):
        conn, _ = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS planos_sucesso (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                descricao TEXT,
                estrutura_json TEXT,
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                dias_duracao INTEGER,
                criado_por TEXT,
                data_atualizacao TIMESTAMP,
                ativo BOOLEAN DEFAULT 1
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS implantacoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plano_id INTEGER,
                cliente_id INTEGER,
                data_inicio TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data_inicio_efetivo TIMESTAMP,
                status TEXT,
                checklist_json TEXT,
                nome_empresa TEXT,
                email_responsavel TEXT,
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                usuario_cs TEXT DEFAULT 'test@example.com'
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS checklist_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                implantacao_id INTEGER,
                plano_id INTEGER,
                parent_id INTEGER,
                ordem INTEGER,
                title TEXT NOT NULL,
                status TEXT DEFAULT 'Pendente',
                tag TEXT,
                data_conclusao TIMESTAMP,
                tipo_item TEXT,
                comment TEXT,
                level INTEGER,
                obrigatoria BOOLEAN,
                completed INTEGER DEFAULT 0,
                descricao TEXT,
                responsavel TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS comentarios_h (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                checklist_item_id INTEGER,
                texto TEXT NOT NULL,
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                usuario_cs TEXT,
                visibilidade TEXT DEFAULT 'interno'
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS perfil_usuario (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario TEXT UNIQUE NOT NULL,
                nome TEXT,
                cargo TEXT,
                perfil_acesso TEXT,
                foto_url TEXT
            )
        ''')

        conn.commit()

    def test_tags_in_tree_response(self):
        estrutura = {
            "items": [
                {
                    "title": "Fase 1",
                    "tipo_item": "plano_fase",
                    "children": [
                        {
                            "title": "Grupo 1",
                            "tipo_item": "plano_grupo",
                            "children": [
                                {
                                    "title": "Tarefa Interna",
                                    "tipo_item": "plano_tarefa",
                                    "tag": "Ação interna",
                                    "children": []
                                },
                                {
                                    "title": "Tarefa Reunião",
                                    "tipo_item": "plano_tarefa",
                                    "tag": "Reunião",
                                    "children": []
                                }
                            ]
                        }
                    ]
                }
            ]
        }

        resp = self.client.post('/planos/', json={
            'nome': 'Plano Tags',
            'estrutura': estrutura
        })
        self.assertEqual(resp.status_code, 201)
        plano_id = resp.get_json()['plano_id']

        with self.app.app_context():
            conn, _ = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO implantacoes (nome_empresa, email_responsavel, status, usuario_cs) VALUES (?, ?, ?, ?)",
                           ('Empresa Tags', 'resp@empresa.com', 'em_andamento', 'test@example.com'))
            impl_id = cursor.lastrowid
            conn.commit()

            from backend.project.domain.planos_sucesso_service import aplicar_plano_a_implantacao_checklist
            aplicar_plano_a_implantacao_checklist(impl_id, plano_id, 'test@example.com')

        tree_resp = self.client.get(f'/api/checklist/tree?implantacao_id={impl_id}&format=nested')
        self.assertEqual(tree_resp.status_code, 200)
        data = tree_resp.get_json()
        self.assertTrue(data['ok'])
        items = data['items']
        self.assertIsInstance(items, list)
        # Navegar até as duas tarefas e confirmar tags
        fase = items[0]
        grupo = fase['children'][0]
        tarefa_interna = grupo['children'][0]
        tarefa_reuniao = grupo['children'][1]
        self.assertEqual(tarefa_interna.get('tag'), 'Ação interna')
        self.assertEqual(tarefa_reuniao.get('tag'), 'Reunião')

    def test_comments_endpoint_includes_task_ref(self):
        with self.app.app_context():
            conn, _ = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO implantacoes (nome_empresa, email_responsavel, status, usuario_cs) VALUES (?, ?, ?, ?)",
                           ('Empresa Comentários', 'resp@empresa.com', 'em_andamento', 'test@example.com'))
            impl_id = cursor.lastrowid
            cursor.execute("INSERT INTO checklist_items (implantacao_id, title, tipo_item, status) VALUES (?, ?, ?, ?)",
                           (impl_id, 'Tarefa Comentada', 'tarefa', 'Pendente'))
            item_id = cursor.lastrowid
            conn.commit()

        # Adiciona comentário via API para garantir colunas corretas
        add_resp = self.client.post(f'/api/checklist/comment/{item_id}', json={
            'texto': 'Comentário de teste',
            'visibilidade': 'interno'
        })
        self.assertEqual(add_resp.status_code, 200)
        self.assertTrue(add_resp.get_json()['ok'])

        # Lista globais
        list_resp = self.client.get(f'/api/checklist/implantacao/{impl_id}/comments?page=1&per_page=10')
        self.assertEqual(list_resp.status_code, 200)
        payload = list_resp.get_json()
        self.assertTrue(payload['ok'])
        self.assertGreaterEqual(len(payload['comments']), 1)
        c0 = payload['comments'][0]
        self.assertEqual(c0['item_id'], item_id)
        self.assertEqual(c0['item_title'], 'Tarefa Comentada')

    def test_frontend_includes_id_and_visibility_helpers(self):
        # Verifica que o renderer usa id="checklist-item-<id>" e que há ensureItemVisible
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        with open(os.path.join(base_dir, 'frontend', 'static', 'js', 'checklist_renderer.js'), 'r', encoding='utf-8') as f:
            js = f.read()
            self.assertIn('id="checklist-item-${item.id}"', js)
            self.assertIn('ensureItemVisible(itemId)', js)

        with open(os.path.join(base_dir, 'frontend', 'static', 'js', 'implantacao_detalhes_ui.js'), 'r', encoding='utf-8') as f:
            ui_js = f.read()
            self.assertIn('task-scroll-link', ui_js)
            self.assertIn('ensureItemVisible(taskId)', ui_js)


if __name__ == '__main__':
    unittest.main()
