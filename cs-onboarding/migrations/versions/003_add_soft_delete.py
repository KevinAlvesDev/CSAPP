"""Add soft delete support

Revision ID: 003
Revises: 002
Create Date: 2025-01-13

Adiciona suporte a soft delete (exclusão lógica) nas tabelas principais.
"""

from alembic import op
import sqlalchemy as sa

revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade():
    """
    Adiciona coluna deleted_at para soft delete.
    
    Tabelas afetadas:
    - implantacoes
    - tarefas
    - comentarios
    """
    
    conn = op.get_bind()
    dialect = conn.dialect.name
    
    if dialect == 'postgresql':

        op.execute("""
            ALTER TABLE implantacoes 
            ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP NULL;
        """)
        
        op.execute("""
            ALTER TABLE tarefas 
            ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP NULL;
        """)
        
        op.execute("""
            ALTER TABLE comentarios 
            ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP NULL;
        """)

        op.execute("""
            CREATE INDEX IF NOT EXISTS idx_impl_deleted 
            ON implantacoes(deleted_at);
        """)
        
        op.execute("""
            CREATE INDEX IF NOT EXISTS idx_tarefas_deleted 
            ON tarefas(deleted_at);
        """)
        
        op.execute("""
            CREATE INDEX IF NOT EXISTS idx_comentarios_deleted 
            ON comentarios(deleted_at);
        """)
        
    elif dialect == 'sqlite':



        try:
            op.execute("""
                ALTER TABLE implantacoes 
                ADD COLUMN deleted_at DATETIME NULL;
            """)
        except:
            pass                    
        
        try:
            op.execute("""
                ALTER TABLE tarefas 
                ADD COLUMN deleted_at DATETIME NULL;
            """)
        except:
            pass
        
        try:
            op.execute("""
                ALTER TABLE comentarios 
                ADD COLUMN deleted_at DATETIME NULL;
            """)
        except:
            pass
        
        op.execute("""
            CREATE INDEX IF NOT EXISTS idx_impl_deleted 
            ON implantacoes(deleted_at);
        """)
        
        op.execute("""
            CREATE INDEX IF NOT EXISTS idx_tarefas_deleted 
            ON tarefas(deleted_at);
        """)
        
        op.execute("""
            CREATE INDEX IF NOT EXISTS idx_comentarios_deleted 
            ON comentarios(deleted_at);
        """)


def downgrade():
    """Remove suporte a soft delete."""
    
    conn = op.get_bind()
    dialect = conn.dialect.name

    op.execute("DROP INDEX IF EXISTS idx_impl_deleted;")
    op.execute("DROP INDEX IF EXISTS idx_tarefas_deleted;")
    op.execute("DROP INDEX IF EXISTS idx_comentarios_deleted;")
    
    if dialect == 'postgresql':

        op.execute("ALTER TABLE implantacoes DROP COLUMN IF EXISTS deleted_at;")
        op.execute("ALTER TABLE tarefas DROP COLUMN IF EXISTS deleted_at;")
        op.execute("ALTER TABLE comentarios DROP COLUMN IF EXISTS deleted_at;")
    
    elif dialect == 'sqlite':



        pass

