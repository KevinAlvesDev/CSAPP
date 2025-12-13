"""add checklist_item_id to comentarios_h

Revision ID: 007_add_checklist_item_id
Revises: 006_status_history
Create Date: 2025-05-20

Adiciona coluna checklist_item_id na tabela comentarios_h.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision = '007_add_checklist_item_id'
down_revision = '006_status_history'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    dialect = conn.dialect.name
    
    if dialect == 'postgresql':
        # Check if column exists first to avoid errors
        conn = op.get_bind()
        cursor = conn.connection.cursor()
        cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name='comentarios_h' AND column_name='checklist_item_id'")
        if not cursor.fetchone():
            op.execute(text("""
                ALTER TABLE comentarios_h 
                ADD COLUMN checklist_item_id INTEGER REFERENCES checklist_items(id)
            """))
            
            op.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_comentarios_h_checklist_item_id 
                ON comentarios_h(checklist_item_id)
            """))
            print("✅ Coluna checklist_item_id adicionada em comentarios_h")
        else:
            print("ℹ️ Coluna checklist_item_id já existe em comentarios_h")
            
    else:
        # SQLite - Alembic usually handles this via batch operations, but here we use raw SQL
        # SQLite doesn't support adding FK in ALTER TABLE easily without recreation, 
        # but we can add the column.
        op.execute(text("ALTER TABLE comentarios_h ADD COLUMN checklist_item_id INTEGER REFERENCES checklist_items(id)"))
        op.execute(text("CREATE INDEX IF NOT EXISTS idx_comentarios_h_checklist_item_id ON comentarios_h(checklist_item_id)"))


def downgrade():
    conn = op.get_bind()
    dialect = conn.dialect.name
    
    if dialect == 'postgresql':
        op.execute(text("ALTER TABLE comentarios_h DROP COLUMN IF EXISTS checklist_item_id"))
    else:
        # SQLite doesn't support DROP COLUMN in older versions, but let's try
        try:
            op.execute(text("ALTER TABLE comentarios_h DROP COLUMN checklist_item_id"))
        except:
            pass
