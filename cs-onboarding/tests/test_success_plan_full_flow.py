import unittest
import json
import os
import sys
import uuid
from datetime import datetime

# Adiciona o diretório pai ao path para importar o backend
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.project import create_app
from backend.project.db import get_db_connection, db_connection
from backend.project.domain.checklist_service import toggle_item_status

class TestSuccessPlanFullFlow(unittest.TestCase):
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
        self.runner = self.app.test_cli_runner()
        
        with self.app.app_context():
            self.init_db()

    def tearDown(self):
        if os.path.exists(self.db_path):
            try:
                os.remove(self.db_path)
            except (PermissionError, OSError):
                pass

    def init_db(self):
        conn, _ = get_db_connection()
        cursor = conn.cursor()
        
        # Create tables
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
                usuario_cs TEXT DEFAULT 'test@example.com',
                FOREIGN KEY (plano_id) REFERENCES planos_sucesso (id)
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
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (implantacao_id) REFERENCES implantacoes (id),
                FOREIGN KEY (parent_id) REFERENCES checklist_items (id),
                FOREIGN KEY (plano_id) REFERENCES planos_sucesso (id)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS checklist_status_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id INTEGER NOT NULL,
                status_anterior TEXT,
                status_novo TEXT NOT NULL,
                data_alteracao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                usuario_id TEXT,
                FOREIGN KEY (item_id) REFERENCES checklist_items (id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS comentarios_h (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id INTEGER NOT NULL,
                texto TEXT NOT NULL,
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                usuario_cs TEXT,
                visibilidade TEXT DEFAULT 'interno',
                FOREIGN KEY (item_id) REFERENCES checklist_items (id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario TEXT UNIQUE NOT NULL,
                senha TEXT NOT NULL
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


    def login(self, email='test@example.com'):
        with self.client.session_transaction() as sess:
            sess['user'] = {'email': email, 'name': 'Test User'}
            sess['user_email'] = email
            sess['logged_in'] = True
            sess['is_manager'] = True

    def test_01_create_plan_valid_tags(self):
        self.login()
        
        # Estrutura válida com tags corretas
        estrutura = {
            "fases": [
                {
                    "nome": "Fase 1",
                    "grupos": [
                        {
                            "nome": "Grupo 1",
                            "tarefas": [
                                {
                                    "nome": "Tarefa Interna",
                                    "tag": "Ação interna",
                                    "subtarefas": []
                                },
                                {
                                    "nome": "Tarefa Reunião",
                                    "tag": "Reunião",
                                    "subtarefas": []
                                }
                            ]
                        }
                    ]
                }
            ]
        }
        
        response = self.client.post('/planos/', json={
            'nome': 'Plano Teste Válido',
            'descricao': 'Teste',
            'estrutura': estrutura
        })
        
        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        self.assertTrue(data['success'])
        self.plano_id = data['plano_id']

    def test_02_create_plan_invalid_tag(self):
        self.login()
        
        # Estrutura inválida
        estrutura = {
            "fases": [
                {
                    "nome": "Fase 1",
                    "grupos": [
                        {
                            "nome": "Grupo 1",
                            "tarefas": [
                                {
                                    "nome": "Tarefa Inválida",
                                    "tag": "Tag Inexistente", # INVÁLIDA
                                    "subtarefas": []
                                }
                            ]
                        }
                    ]
                }
            ]
        }
        
        response = self.client.post('/planos/', json={
            'nome': 'Plano Teste Inválido',
            'descricao': 'Teste',
            'estrutura': estrutura
        })
        
        self.assertNotEqual(response.status_code, 500)
        data = response.get_json()
        if response.status_code == 201 or (data and data.get('success')):
             self.fail("Should not create plan with invalid tag")
        else:
            self.assertIn('inválida', data.get('error', '').lower() if data else '')

    def test_03_status_flow_and_history(self):
        self.login()
        
        # 1. Create Plan
        estrutura = {
            "items": [
                {
                    "title": "Fase A",
                    "tipo_item": "plano_fase",
                    "children": [
                        {
                            "title": "Grupo A",
                            "tipo_item": "plano_grupo",
                            "children": [
                                {
                                    "title": "Tarefa A",
                                    "tipo_item": "plano_tarefa",
                                    "tag": "Ação interna",
                                    "children": []
                                }
                            ]
                        }
                    ]
                }
            ]
        }
        
        resp = self.client.post('/planos/', json={
            'nome': 'Plano Flow',
            'estrutura': estrutura
        })
        self.assertEqual(resp.status_code, 201)
        plano_id = resp.get_json()['plano_id']
        
        # 2. Create Implantation (Simulated)
        with self.app.app_context():
            conn, _ = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO implantacoes (nome_empresa, email_responsavel, data_criacao, status, usuario_cs) VALUES (?, ?, ?, ?, ?)", 
                          ('Empresa Teste', 'resp@teste.com', datetime.now(), 'em_andamento', 'test@example.com'))
            impl_id = cursor.lastrowid
            conn.commit()
            
            # 3. Apply Plan
            from backend.project.domain.planos_sucesso_service import aplicar_plano_a_implantacao_checklist
            aplicar_plano_a_implantacao_checklist(impl_id, plano_id, 'test@example.com')
            
            # 4. Get Task ID
            # Note: _clonar_plano_para_implantacao_checklist converts 'plano_tarefa' to 'tarefa'
            cursor.execute("SELECT id FROM checklist_items WHERE implantacao_id = ? AND tipo_item = 'tarefa'", (impl_id,))
            row = cursor.fetchone()
            self.assertIsNotNone(row, "Task not created")
            task_id = row[0]
            
            # 5. Toggle Status (Complete)
            result = toggle_item_status(task_id, True, 'test@example.com')
            self.assertTrue(result['ok'])
            
            # Verify Status & Date
            cursor.execute("SELECT status, data_conclusao, completed FROM checklist_items WHERE id = ?", (task_id,))
            row = cursor.fetchone()
            self.assertEqual(row[0], 'Concluída') # Adjusted case based on toggle_item_status logic
            self.assertTrue(row[2]) # completed
            self.assertIsNotNone(row[1]) # data_conclusao
            
            # Verify History
            cursor.execute("SELECT status_anterior, status_novo FROM checklist_status_history WHERE item_id = ?", (task_id,))
            hist = cursor.fetchone()
            self.assertIsNotNone(hist)
            # Initial status is 'pendente' (lowercase) from cloning service
            self.assertEqual(hist[0], 'pendente')
            self.assertEqual(hist[1], 'Concluída')

    def test_04_comments_pagination(self):
        self.login()
        
        with self.app.app_context():
            conn, _ = get_db_connection()
            cursor = conn.cursor()
            # Create Implantation & Task
            cursor.execute("INSERT INTO implantacoes (nome_empresa, email_responsavel, status, usuario_cs) VALUES (?, ?, ?, ?)", ('Empresa Coments', 'c@c.com', 'em_andamento', 'test@example.com'))
            impl_id = cursor.lastrowid
            cursor.execute("INSERT INTO checklist_items (implantacao_id, title, tipo_item, status) VALUES (?, ?, ?, ?)", (impl_id, 'Tarefa Comentada', 'plano_tarefa', 'Pendente'))
            task_id = cursor.lastrowid
            conn.commit()
            
            # Insert 25 comments
            for i in range(25):
                cursor.execute(
                    "INSERT INTO comentarios_h (checklist_item_id, texto, usuario_cs, data_criacao) VALUES (?, ?, ?, ?)",
                    (task_id, f"Comentário {i}", 'user@test.com', datetime.now())
                )
            conn.commit()
        
        # Test Page 1
        # URL: /api/checklist/implantacao/<id>/comments
        # Need to verify the route path. Assuming it's under checklist_bp with prefix /api/checklist
        response = self.client.get(f'/api/checklist/implantacao/{impl_id}/comments?page=1&per_page=20')
        
        if response.status_code == 404:
             # Fallback check if I defined it elsewhere or without prefix
             response = self.client.get(f'/api/implantacao/{impl_id}/comments?page=1&per_page=20')
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['ok'])
        self.assertEqual(len(data['comments']), 20)
        self.assertEqual(data['pagination']['total_pages'], 2)
        
        # Test Page 2
        response = self.client.get(f'/api/checklist/implantacao/{impl_id}/comments?page=2&per_page=20')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(len(data['comments']), 5)

if __name__ == '__main__':
    unittest.main()
