"""add_cancelamento_fields_to_implantacoes

Revision ID: 008
Revises: 007
Create Date: 2025-12-19 17:13:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '008'
down_revision = '007'
branch_labels = None
depends_on = None


def upgrade():
    """
    Adiciona colunas para suportar cancelamento de implantações:
    - data_cancelamento: Data em que a implantação foi cancelada
    - motivo_cancelamento: Motivo do cancelamento
    - comprovante_cancelamento_url: URL do comprovante (print do email)
    """
    # Verificar se as colunas já existem antes de adicionar
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('implantacoes')]
    
    if 'data_cancelamento' not in columns:
        op.add_column('implantacoes', 
            sa.Column('data_cancelamento', sa.Date(), nullable=True)
        )
    
    if 'motivo_cancelamento' not in columns:
        op.add_column('implantacoes', 
            sa.Column('motivo_cancelamento', sa.Text(), nullable=True)
        )
    
    if 'comprovante_cancelamento_url' not in columns:
        op.add_column('implantacoes', 
            sa.Column('comprovante_cancelamento_url', sa.String(500), nullable=True)
        )


def downgrade():
    """
    Remove as colunas de cancelamento
    """
    op.drop_column('implantacoes', 'comprovante_cancelamento_url')
    op.drop_column('implantacoes', 'motivo_cancelamento')
    op.drop_column('implantacoes', 'data_cancelamento')
