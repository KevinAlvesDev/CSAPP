"""restore_missing_dates_from_timeline

Revision ID: 010_restore_missing_dates_from_timeline
Revises: 009_populate_finalization_dates
Create Date: 2026-02-15 04:10:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text

# revision identifiers, used by Alembic.
revision = '010_restore_missing_dates_from_timeline'
down_revision = '009_populate_finalization_dates'
branch_labels = None
depends_on = None

def upgrade():
    conn = op.get_bind()
    
    # Esta migração tenta recuperar datas perdidas consultando o histórico (timeline_log)
    # Isso corrige registros em que o status 'finalizada' não gravou a data na tabela principal.

    # 1. Recuperar Data Finalização para status 'finalizada' (Universal SQL)
    conn.execute(text("""
        UPDATE implantacoes
        SET data_finalizacao = (
            SELECT MAX(data_criacao)
            FROM timeline_log
            WHERE timeline_log.implantacao_id = implantacoes.id
              AND (timeline_log.detalhes LIKE '%finalizada%' OR timeline_log.detalhes LIKE '%concluída%')
              AND timeline_log.tipo_evento = 'status_alterado'
        )
        WHERE status IN ('finalizada', 'concluida')
          AND data_finalizacao IS NULL
          AND data_final_implantacao IS NULL
          AND EXISTS (
            SELECT 1 
            FROM timeline_log 
            WHERE timeline_log.implantacao_id = implantacoes.id
              AND (timeline_log.detalhes LIKE '%finalizada%' OR timeline_log.detalhes LIKE '%concluída%')
              AND timeline_log.tipo_evento = 'status_alterado'
          )
    """))

    # 2. Recuperar Data Finalização para status 'parada' (Universal SQL)
    conn.execute(text("""
        UPDATE implantacoes 
        SET data_finalizacao = (
            SELECT MAX(data_criacao)
            FROM timeline_log
            WHERE timeline_log.implantacao_id = implantacoes.id
              AND timeline_log.detalhes LIKE '%parada%'
              AND timeline_log.tipo_evento = 'status_alterado'
        )
        WHERE status = 'parada'
          AND data_finalizacao IS NULL
          AND data_final_implantacao IS NULL
          AND EXISTS (
            SELECT 1 
            FROM timeline_log 
            WHERE timeline_log.implantacao_id = implantacoes.id
              AND timeline_log.detalhes LIKE '%parada%'
              AND timeline_log.tipo_evento = 'status_alterado'
          )
    """))

    # 3. Réplica para data_final_implantacao para garantir consistência legado
    conn.execute(text("""
        UPDATE implantacoes 
        SET data_final_implantacao = data_finalizacao 
        WHERE data_final_implantacao IS NULL 
          AND data_finalizacao IS NOT NULL
    """))

def downgrade():
    pass
