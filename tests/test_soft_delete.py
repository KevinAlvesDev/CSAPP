\
\

import pytest
import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))

from project import create_app
from project.soft_delete import (
    soft_delete,
    restore,
    hard_delete,
    get_deleted_records,
    cleanup_old_deleted_records,
    exclude_deleted
)
from project.db import query_db, execute_db


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
    
    yield app
    
        \
    with app.app_context():
        conn, _ = from project.db import get_db_connection
        conn, _ = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM implantacoes WHERE nome_empresa LIKE 'Test%'")
        conn.commit()
        conn.close()


class TestSoftDelete:
    """Testes para soft delete."""
    
    def test_soft_delete_marca_registro(self, app):
        """Testa que soft delete marca registro como excluído."""
        with app.app_context():
            \
            impl_id = execute_db(
                """INSERT INTO implantacoes 
                   (nome_empresa, email_responsavel, usuario_cs, status) 
                   VALUES (?, ?, ?, ?)""",
                ('Test Company Soft Delete', 'test@test.com', 'test@example.com', 'andamento')
            )
            
                        \
            result = soft_delete('implantacoes', impl_id)
            assert result is True
            
                        \
            impl = query_db(
                "SELECT * FROM implantacoes WHERE id = ?",
                (impl_id,),
                one=True
            )
            
            assert impl is not None
            assert impl.get('deleted_at') is not None
    
    def test_soft_delete_nao_duplica(self, app):
        """Testa que soft delete não duplica marcação."""
        with app.app_context():
            \
            impl_id = execute_db(
                """INSERT INTO implantacoes 
                   (nome_empresa, email_responsavel, usuario_cs, status) 
                   VALUES (?, ?, ?, ?)""",
                ('Test Company Duplicate', 'test@test.com', 'test@example.com', 'andamento')
            )
            
                        \
            result1 = soft_delete('implantacoes', impl_id)
            assert result1 is True
            
                        \
            result2 = soft_delete('implantacoes', impl_id)
            assert result2 is False                      
    
    def test_restore_recupera_registro(self, app):
        """Testa que restore recupera registro excluído."""
        with app.app_context():
            \
            impl_id = execute_db(
                """INSERT INTO implantacoes 
                   (nome_empresa, email_responsavel, usuario_cs, status) 
                   VALUES (?, ?, ?, ?)""",
                ('Test Company Restore', 'test@test.com', 'test@example.com', 'andamento')
            )
            
            soft_delete('implantacoes', impl_id)
            
                        \
            result = restore('implantacoes', impl_id)
            assert result is True
            
                        \
            impl = query_db(
                "SELECT * FROM implantacoes WHERE id = ?",
                (impl_id,),
                one=True
            )
            
            assert impl is not None
            assert impl.get('deleted_at') is None
    
    def test_get_deleted_records(self, app):
        """Testa listagem de registros excluídos."""
        with app.app_context():
            \
            impl_id1 = execute_db(
                """INSERT INTO implantacoes 
                   (nome_empresa, email_responsavel, usuario_cs, status) 
                   VALUES (?, ?, ?, ?)""",
                ('Test Deleted 1', 'test@test.com', 'test@example.com', 'andamento')
            )
            
            impl_id2 = execute_db(
                """INSERT INTO implantacoes 
                   (nome_empresa, email_responsavel, usuario_cs, status) 
                   VALUES (?, ?, ?, ?)""",
                ('Test Deleted 2', 'test@test.com', 'test@example.com', 'andamento')
            )
            
            soft_delete('implantacoes', impl_id1)
            soft_delete('implantacoes', impl_id2)
            
                        \
            deleted = get_deleted_records('implantacoes')
            
            assert len(deleted) >= 2
            deleted_ids = [d['id'] for d in deleted]
            assert impl_id1 in deleted_ids
            assert impl_id2 in deleted_ids
    
    def test_exclude_deleted_filter(self):
        """Testa filtro exclude_deleted."""
        \
        query1 = "SELECT * FROM implantacoes"
        result1 = exclude_deleted(query1)
        assert "WHERE deleted_at IS NULL" in result1
        
                \
        query2 = "SELECT * FROM implantacoes WHERE usuario_cs = %s"
        result2 = exclude_deleted(query2)
        assert "AND deleted_at IS NULL" in result2

