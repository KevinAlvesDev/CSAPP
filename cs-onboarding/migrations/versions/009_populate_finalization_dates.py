"""populate_finalization_dates

Revision ID: 009_populate_finalization_dates
Revises: 008_add_cancelamento_fields_to_implantacoes
Create Date: 2026-02-15 03:45:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text

# revision identifiers, used by Alembic.
revision = '009_populate_finalization_dates'
down_revision = '008_add_cancelamento_fields_to_implantacoes'
branch_labels = None
depends_on = None

def upgrade():
    conn = op.get_bind()
    
    # 1. Copiar data_final_implantacao -> data_finalizacao (para finalizadas)
    conn.execute(text("""
        UPDATE implantacoes 
        SET data_finalizacao = data_final_implantacao 
        WHERE status IN ('finalizada', 'concluida', 'entregue') 
          AND data_finalizacao IS NULL 
          AND data_final_implantacao IS NOT NULL
    """))

    # 2. Copiar data_finalizacao -> data_final_implantacao (para garantir consistência legada)
    conn.execute(text("""
        UPDATE implantacoes 
        SET data_final_implantacao = data_finalizacao 
        WHERE status IN ('finalizada', 'concluida', 'entregue') 
          AND data_final_implantacao IS NULL 
          AND data_finalizacao IS NOT NULL
    """))

    # 3. Copiar data_final_implantacao -> data_finalizacao (para paradas)
    conn.execute(text("""
        UPDATE implantacoes 
        SET data_finalizacao = data_final_implantacao 
        WHERE status = 'parada' 
          AND data_finalizacao IS NULL 
          AND data_final_implantacao IS NOT NULL
    """))

    # 4. Copiar data_finalizacao -> data_final_implantacao (para paradas)
    conn.execute(text("""
        UPDATE implantacoes 
        SET data_final_implantacao = data_finalizacao 
        WHERE status = 'parada' 
          AND data_final_implantacao IS NULL 
          AND data_finalizacao IS NOT NULL
    """))

def downgrade():
    # Não há downgrade para updates de dados, apenas estruturais.
    pass
