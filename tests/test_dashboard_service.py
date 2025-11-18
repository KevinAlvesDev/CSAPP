\
\

import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))

from project import create_app
from project.domain.dashboard_service import get_dashboard_data
from project.db import execute_db, query_db


@pytest.fixture
def app():
    """Cria uma instância do app para testes."""
    app = create_app()
    app.config.update({
        'TESTING': True,
        'USE_SQLITE_LOCALLY': True,
    })
    
    with app.app_context():
        from project.db import init_db
        init_db()
        
                \
        execute_db(
            "INSERT OR IGNORE INTO usuarios (usuario, senha) VALUES (?, ?)",
            ('dashboard@test.com', 'test123')
        )
        
        execute_db(
            """INSERT OR IGNORE INTO perfil_usuario 
               (usuario, nome, cargo, perfil_acesso) 
               VALUES (?, ?, ?, ?)""",
            ('dashboard@test.com', 'Dashboard Test User', 'Tester', 'Implantador')
        )
    
    yield app
    
        \
    with app.app_context():
        from project.db import get_db_connection
        conn, _ = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM implantacoes WHERE usuario_cs = 'dashboard@test.com'")
        cursor.execute("DELETE FROM perfil_usuario WHERE usuario = 'dashboard@test.com'")
        cursor.execute("DELETE FROM usuarios WHERE usuario = 'dashboard@test.com'")
        conn.commit()
        conn.close()


class TestDashboardService:
    """Testes para serviço de dashboard."""
    
    def test_get_dashboard_data_sem_implantacoes(self, app):
        """Testa dashboard sem implantações."""
        with app.app_context():
            data = get_dashboard_data('dashboard@test.com')
            
            assert data is not None
            assert isinstance(data, list)
            assert len(data) == 0
    
    def test_get_dashboard_data_com_implantacoes(self, app):
        """Testa dashboard com implantações."""
        with app.app_context():
            \
            execute_db(
                """INSERT INTO implantacoes 
                   (nome_empresa, email_responsavel, usuario_cs, status) 
                   VALUES (?, ?, ?, ?)""",
                ('Dashboard Test Company 1', 'test1@test.com', 'dashboard@test.com', 'andamento')
            )
            
            execute_db(
                """INSERT INTO implantacoes 
                   (nome_empresa, email_responsavel, usuario_cs, status) 
                   VALUES (?, ?, ?, ?)""",
                ('Dashboard Test Company 2', 'test2@test.com', 'dashboard@test.com', 'finalizada')
            )
            
            data = get_dashboard_data('dashboard@test.com')
            
            assert data is not None
            assert isinstance(data, list)
            assert len(data) >= 2
    
    def test_get_dashboard_data_com_paginacao(self, app):
        """Testa dashboard com paginação."""
        with app.app_context():
            \
            for i in range(15):
                execute_db(
                    """INSERT INTO implantacoes 
                       (nome_empresa, email_responsavel, usuario_cs, status) 
                       VALUES (?, ?, ?, ?)""",
                    (f'Dashboard Pagination Test {i}', f'test{i}@test.com', 'dashboard@test.com', 'andamento')
                )
            
            data, pagination = get_dashboard_data('dashboard@test.com', page=1, per_page=10)
            
            assert data is not None
            assert isinstance(data, list)
            assert len(data) == 10
            assert pagination is not None
            assert pagination.page == 1
            assert pagination.per_page == 10
            assert pagination.total >= 15
            assert pagination.has_next is True
            
                        \
            data2, pagination2 = get_dashboard_data('dashboard@test.com', page=2, per_page=10)
            
            assert len(data2) >= 5
            assert pagination2.page == 2
            assert pagination2.has_prev is True
    
    def test_get_dashboard_data_filtrado_por_cs(self, app):
        """Testa dashboard filtrado por CS."""
        with app.app_context():
            \
            execute_db(
                "INSERT OR IGNORE INTO usuarios (usuario, senha) VALUES (?, ?)",
                ('other_cs@test.com', 'test123')
            )
            
            execute_db(
                """INSERT OR IGNORE INTO perfil_usuario 
                   (usuario, nome, cargo, perfil_acesso) 
                   VALUES (?, ?, ?, ?)""",
                ('other_cs@test.com', 'Other CS', 'Tester', 'Implantador')
            )
            
                        \
            execute_db(
                """INSERT INTO implantacoes 
                   (nome_empresa, email_responsavel, usuario_cs, status) 
                   VALUES (?, ?, ?, ?)""",
                ('Dashboard CS Filter 1', 'test@test.com', 'dashboard@test.com', 'andamento')
            )
            
            execute_db(
                """INSERT INTO implantacoes 
                   (nome_empresa, email_responsavel, usuario_cs, status) 
                   VALUES (?, ?, ?, ?)""",
                ('Dashboard CS Filter 2', 'test@test.com', 'other_cs@test.com', 'andamento')
            )
            
                        \
            data = get_dashboard_data('dashboard@test.com', filtered_cs_email='dashboard@test.com')
            
            assert data is not None
            \
            for impl in data:
                assert impl['usuario_cs'] == 'dashboard@test.com'

