"""create checklist items table

Revision ID: 001_checklist
Revises: 
Create Date: 2025-01-13

Cria tabela unificada para checklist hierárquico infinito usando padrão Adjacency List.
Suporta profundidade infinita através de parent_id auto-referenciado.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision = '001_checklist'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """
    Cria a tabela checklist_items com todas as colunas necessárias.
    
    Estrutura:
    - Adjacency List pattern para hierarquia infinita
    - Suporte a comentários por item
    - Campos de ordenação e nível
    - Timestamps para auditoria
    """
    conn = op.get_bind()
    dialect = conn.dialect.name
    
    if dialect == 'postgresql':
        # PostgreSQL
        op.execute(text("""
            CREATE TABLE IF NOT EXISTS checklist_items (
                id SERIAL PRIMARY KEY,
                parent_id INTEGER REFERENCES checklist_items(id) ON DELETE CASCADE,
                title VARCHAR(500) NOT NULL,
                completed BOOLEAN NOT NULL DEFAULT false,
                comment TEXT,
                level INTEGER DEFAULT 0,
                ordem INTEGER DEFAULT 0,
                implantacao_id INTEGER,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                
                -- Constraints
                CONSTRAINT chk_title_not_empty CHECK (LENGTH(TRIM(title)) > 0)
            )
        """))
        
        # Índices para performance
        op.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_checklist_parent_id 
            ON checklist_items(parent_id)
        """))
        
        op.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_checklist_implantacao_id 
            ON checklist_items(implantacao_id)
        """))
        
        op.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_checklist_completed 
            ON checklist_items(completed)
        """))
        
        op.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_checklist_ordem 
            ON checklist_items(ordem)
        """))
        
        # Índice composto para queries frequentes
        op.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_checklist_parent_ordem 
            ON checklist_items(parent_id, ordem)
        """))
        
        # Trigger para atualizar updated_at automaticamente
        op.execute(text("""
            CREATE OR REPLACE FUNCTION update_checklist_items_updated_at()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.updated_at = CURRENT_TIMESTAMP;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql
        """))
        
        op.execute(text("""
            DROP TRIGGER IF EXISTS trigger_checklist_items_updated_at ON checklist_items;
            CREATE TRIGGER trigger_checklist_items_updated_at
            BEFORE UPDATE ON checklist_items
            FOR EACH ROW
            EXECUTE FUNCTION update_checklist_items_updated_at()
        """))
        
    else:
        # SQLite
        op.execute(text("""
            CREATE TABLE IF NOT EXISTS checklist_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                parent_id INTEGER,
                title TEXT NOT NULL,
                completed INTEGER NOT NULL DEFAULT 0,
                comment TEXT,
                level INTEGER DEFAULT 0,
                ordem INTEGER DEFAULT 0,
                implantacao_id INTEGER,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                
                FOREIGN KEY (parent_id) REFERENCES checklist_items(id) ON DELETE CASCADE,
                CHECK (LENGTH(TRIM(title)) > 0)
            )
        """))
        
        # Índices para performance
        op.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_checklist_parent_id 
            ON checklist_items(parent_id)
        """))
        
        op.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_checklist_implantacao_id 
            ON checklist_items(implantacao_id)
        """))
        
        op.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_checklist_completed 
            ON checklist_items(completed)
        """))
        
        op.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_checklist_ordem 
            ON checklist_items(ordem)
        """))
        
        op.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_checklist_parent_ordem 
            ON checklist_items(parent_id, ordem)
        """))
        
        # Trigger para atualizar updated_at no SQLite
        op.execute(text("""
            CREATE TRIGGER IF NOT EXISTS trigger_checklist_items_updated_at
            AFTER UPDATE ON checklist_items
            FOR EACH ROW
            WHEN NEW.updated_at = OLD.updated_at
            BEGIN
                UPDATE checklist_items 
                SET updated_at = CURRENT_TIMESTAMP 
                WHERE id = NEW.id;
            END
        """))
    
    print("✅ Tabela checklist_items criada com sucesso!")
    print("📊 Índices de performance criados")


def downgrade():
    """Remove a tabela checklist_items e todos os seus índices."""
    conn = op.get_bind()
    dialect = conn.dialect.name
    
    if dialect == 'postgresql':
        op.execute(text("DROP TRIGGER IF EXISTS trigger_checklist_items_updated_at ON checklist_items"))
        op.execute(text("DROP FUNCTION IF EXISTS update_checklist_items_updated_at()"))
    
    op.execute(text("DROP TABLE IF EXISTS checklist_items CASCADE"))
    
    print("✅ Tabela checklist_items removida")

