"""add plano_id to checklist_items

Revision ID: 002_plano_id
Revises: 001_checklist
Create Date: 2025-01-13

Adiciona coluna plano_id na tabela checklist_items para vincular itens a planos de sucesso.
Permite que planos tenham sua estrutura armazenada em checklist_items antes de serem aplicados.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision = '002_plano_id'
down_revision = '001_checklist'
branch_labels = None
depends_on = None


def upgrade():
    """
    Adiciona coluna plano_id na tabela checklist_items.
    - Permite NULL (para itens de implantações)
    - Foreign key para planos_sucesso
    - Índice para performance
    """
    conn = op.get_bind()
    dialect = conn.dialect.name
    
    if dialect == 'postgresql':
        # PostgreSQL
        # Adicionar coluna plano_id
        op.execute(text("""
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'checklist_items' AND column_name = 'plano_id') THEN
                    ALTER TABLE checklist_items ADD COLUMN plano_id INTEGER REFERENCES planos_sucesso(id) ON DELETE CASCADE;
                END IF;
            END$$;
        """))
        
        # Criar índice para performance
        op.execute(text("""
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE c.relname = 'idx_checklist_plano_id' AND n.nspname = 'public') THEN
                    CREATE INDEX idx_checklist_plano_id ON checklist_items(plano_id);
                END IF;
            END$$;
        """))
        
        # Criar índice composto para queries frequentes
        op.execute(text("""
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE c.relname = 'idx_checklist_plano_ordem' AND n.nspname = 'public') THEN
                    CREATE INDEX idx_checklist_plano_ordem ON checklist_items(plano_id, ordem);
                END IF;
            END$$;
        """))
        
        # Criar índice composto para buscar itens raiz de um plano
        op.execute(text("""
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE c.relname = 'idx_checklist_plano_parent' AND n.nspname = 'public') THEN
                    CREATE INDEX idx_checklist_plano_parent ON checklist_items(plano_id, parent_id);
                END IF;
            END$$;
        """))
        
    else:
        # SQLite
        # SQLite não suporta ALTER TABLE ADD COLUMN IF NOT EXISTS diretamente
        # Precisamos verificar se a coluna já existe
        
        # Verificar se coluna já existe
        cursor = conn.connection.cursor()
        cursor.execute("PRAGMA table_info(checklist_items)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'plano_id' not in columns:
            # Adicionar coluna (SQLite não suporta FK na alteração, então será apenas INT)
            op.execute(text("""
                ALTER TABLE checklist_items 
                ADD COLUMN plano_id INTEGER
            """))
            
            # Criar índice
            op.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_checklist_plano_id 
                ON checklist_items(plano_id)
            """))
            
            op.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_checklist_plano_ordem 
                ON checklist_items(plano_id, ordem)
            """))
            
            op.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_checklist_plano_parent 
                ON checklist_items(plano_id, parent_id)
            """))
    
    print("Coluna plano_id adicionada à tabela checklist_items")
    print("Índices de performance criados")


def downgrade():
    """Remove a coluna plano_id da tabela checklist_items."""
    conn = op.get_bind()
    dialect = conn.dialect.name
    
    # Remover índices primeiro
    op.execute(text("DROP INDEX IF EXISTS idx_checklist_plano_parent"))
    op.execute(text("DROP INDEX IF EXISTS idx_checklist_plano_ordem"))
    op.execute(text("DROP INDEX IF EXISTS idx_checklist_plano_id"))
    
    if dialect == 'postgresql':
        # PostgreSQL
        op.execute(text("ALTER TABLE checklist_items DROP COLUMN IF EXISTS plano_id"))
    else:
        # SQLite não suporta DROP COLUMN facilmente
        # Em produção, seria necessário recriar a tabela
        print("SQLite não suporta DROP COLUMN. A coluna plano_id permanecerá na tabela.")
        print("   Se necessário, recrie a tabela manualmente.")
    
    print("Coluna plano_id removida (ou marcada para remoção)")

