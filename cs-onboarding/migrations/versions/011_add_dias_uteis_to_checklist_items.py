"""add_dias_uteis_to_checklist_items

Revision ID: 011
Revises: 010
Create Date: 2026-02-13 14:00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '011'
down_revision = '010'
branch_labels = None
depends_on = None


def upgrade():
    """
    Adiciona coluna dias_uteis à tabela checklist_items.
    Permite definir se o prazo deve ser calculado apenas em dias úteis.
    """
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('checklist_items')]

    if 'dias_uteis' not in columns:
        op.add_column('checklist_items',
            sa.Column('dias_uteis', sa.Boolean(), server_default='0', nullable=False)
        )


def downgrade():
    """
    Remove a coluna dias_uteis
    """
    op.drop_column('checklist_items', 'dias_uteis')
