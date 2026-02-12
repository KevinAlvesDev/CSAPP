"""add prazo fields to checklist_items

Revision ID: 009_add_prazo_fields
Revises: 008
Create Date: 2026-02-12

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = '009_add_prazo_fields'
down_revision = '008'
branch_labels = None
depends_on = None

def upgrade():
    conn = op.get_bind()
    dialect = conn.dialect.name
    
    if dialect == 'postgresql':
        op.execute(text("""
            ALTER TABLE checklist_items 
            ADD COLUMN IF NOT EXISTS prazo_inicio DATE,
            ADD COLUMN IF NOT EXISTS prazo_fim DATE
        """))
    else:
        # SQLite
        op.execute(text("ALTER TABLE checklist_items ADD COLUMN prazo_inicio DATE"))
        op.execute(text("ALTER TABLE checklist_items ADD COLUMN prazo_fim DATE"))
    
    print("✅ Colunas prazo_inicio e prazo_fim adicionadas em checklist_items")

def downgrade():
    op.drop_column('checklist_items', 'prazo_fim')
    op.drop_column('checklist_items', 'prazo_inicio')
