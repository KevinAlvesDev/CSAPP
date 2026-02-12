"""add_dias_offset_to_checklist_items

Revision ID: 009
Revises: 008
Create Date: 2026-02-12 11:00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '009'
down_revision = '008'
branch_labels = None
depends_on = None


def upgrade():
    """
    Adiciona coluna dias_offset à tabela checklist_items.
    Permite definir prazo individual por tarefa no plano de sucesso.
    Quando o plano é aplicado, cada tarefa terá previsao_original = data_inicio + dias_offset.
    """
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('checklist_items')]

    if 'dias_offset' not in columns:
        op.add_column('checklist_items',
            sa.Column('dias_offset', sa.Integer(), nullable=True)
        )


def downgrade():
    """
    Remove a coluna dias_offset
    """
    op.drop_column('checklist_items', 'dias_offset')
