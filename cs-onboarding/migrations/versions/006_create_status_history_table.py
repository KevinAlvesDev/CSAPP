"""create status history table

Revision ID: 006_status_history
Revises: 005_remover_tabelas_antigas
Create Date: 2025-12-04

Cria tabela para histórico de alterações de status dos itens do checklist.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision = '006_status_history'
down_revision = '005_remover_tabelas_antigas'
branch_labels = None
depends_on = None


def upgrade():
    """
    Cria a tabela checklist_status_history.
    """
    conn = op.get_bind()
    dialect = conn.dialect.name
    
    if dialect == 'postgresql':
        op.execute(text("""
            CREATE TABLE IF NOT EXISTS checklist_status_history (
                id SERIAL PRIMARY KEY,
                checklist_item_id INTEGER NOT NULL REFERENCES checklist_items(id) ON DELETE CASCADE,
                old_status VARCHAR(50),
                new_status VARCHAR(50) NOT NULL,
                changed_by VARCHAR(255),
                changed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """))
        
        op.execute(text("""
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE c.relname = 'idx_history_item_id' AND n.nspname = 'public') THEN
                    CREATE INDEX idx_history_item_id ON checklist_status_history(checklist_item_id);
                END IF;
            END$$;
        """))
        
    else:
        # SQLite
        op.execute(text("""
            CREATE TABLE IF NOT EXISTS checklist_status_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                checklist_item_id INTEGER NOT NULL,
                old_status TEXT,
                new_status TEXT NOT NULL,
                changed_by TEXT,
                changed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                
                FOREIGN KEY (checklist_item_id) REFERENCES checklist_items(id) ON DELETE CASCADE
            )
        """))
        
        op.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_history_item_id 
            ON checklist_status_history(checklist_item_id)
        """))
    
    print("Tabela checklist_status_history criada com sucesso!")


def downgrade():
    op.execute(text("DROP TABLE IF EXISTS checklist_status_history"))
    print("Tabela checklist_status_history removida")
