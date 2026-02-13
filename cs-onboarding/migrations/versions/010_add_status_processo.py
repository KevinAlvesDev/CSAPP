"""add status and processo_id to planos_sucesso

Revision ID: 010_add_status_processo
Revises: 009_add_prazo_fields
Create Date: 2026-02-12

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = '010_add_status_processo'
down_revision = '009_add_prazo_fields'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    dialect = conn.dialect.name

    if dialect == 'postgresql':
        op.execute(text("""
            ALTER TABLE planos_sucesso
            ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'em_andamento',
            ADD COLUMN IF NOT EXISTS processo_id INTEGER
        """))
        # criar índice em processo_id para buscas por processo
        op.create_index('ix_planos_sucesso_processo_id', 'planos_sucesso', ['processo_id'])
    else:
        # SQLite: adicionar colunas uma a uma
        try:
            op.execute(text("ALTER TABLE planos_sucesso ADD COLUMN status TEXT DEFAULT 'em_andamento'"))
        except Exception:
            pass
        try:
            op.execute(text('ALTER TABLE planos_sucesso ADD COLUMN processo_id INTEGER'))
        except Exception:
            pass

    print('✅ Colunas status e processo_id adicionadas em planos_sucesso')


def downgrade():
    # Downgrade: remover colunas (SQLite não suporta DROP COLUMN facilmente)
    conn = op.get_bind()
    dialect = conn.dialect.name
    if dialect == 'postgresql':
        op.drop_index('ix_planos_sucesso_processo_id', table_name='planos_sucesso')
        op.drop_column('planos_sucesso', 'processo_id')
        op.drop_column('planos_sucesso', 'status')
    else:
        # Não implementado para SQLite downgrade (manter compatibilidade)
        pass