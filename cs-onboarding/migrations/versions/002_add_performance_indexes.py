"""Add performance indexes

Revision ID: 002
Revises: 001
Create Date: 2025-01-13

Adiciona índices para melhorar performance de queries frequentes.
"""

from alembic import op
import sqlalchemy as sa

revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade():
    """
    Adiciona índices de performance para queries frequentes.
    
    Índices criados:
    - implantacoes: data_criacao, data_finalizacao (para filtros de data)
    - comentarios: visibilidade, data_criacao (para filtros e ordenação)
    - gamificacao_metricas_mensais: ano, mes (para queries de período)
    - timeline_log: data_evento (para ordenação cronológica)
    """

    conn = op.get_bind()
    dialect = conn.dialect.name
    
    if dialect == 'postgresql':

        op.execute("""
            CREATE INDEX IF NOT EXISTS idx_impl_data_criacao 
            ON implantacoes(data_criacao);
        """)
        
        op.execute("""
            CREATE INDEX IF NOT EXISTS idx_impl_data_finalizacao 
            ON implantacoes(data_finalizacao);
        """)
        
        op.execute("""
            CREATE INDEX IF NOT EXISTS idx_comentarios_visibilidade 
            ON comentarios(visibilidade);
        """)
        
        op.execute("""
            CREATE INDEX IF NOT EXISTS idx_comentarios_data 
            ON comentarios(data_criacao);
        """)
        
        op.execute("""
            CREATE INDEX IF NOT EXISTS idx_gamificacao_ano_mes 
            ON gamificacao_metricas_mensais(ano, mes);
        """)
        
        op.execute("""
            CREATE INDEX IF NOT EXISTS idx_timeline_data 
            ON timeline_log(data_evento);
        """)

        op.execute("""
            CREATE INDEX IF NOT EXISTS idx_gamificacao_user_period 
            ON gamificacao_metricas_mensais(usuario_cs, ano, mes);
        """)
        
    elif dialect == 'sqlite':

        op.execute("""
            CREATE INDEX IF NOT EXISTS idx_impl_data_criacao 
            ON implantacoes(data_criacao);
        """)
        
        op.execute("""
            CREATE INDEX IF NOT EXISTS idx_impl_data_finalizacao 
            ON implantacoes(data_finalizacao);
        """)
        
        op.execute("""
            CREATE INDEX IF NOT EXISTS idx_comentarios_visibilidade 
            ON comentarios(visibilidade);
        """)
        
        op.execute("""
            CREATE INDEX IF NOT EXISTS idx_comentarios_data 
            ON comentarios(data_criacao);
        """)
        
        op.execute("""
            CREATE INDEX IF NOT EXISTS idx_gamificacao_ano_mes 
            ON gamificacao_metricas_mensais(ano, mes);
        """)
        
        op.execute("""
            CREATE INDEX IF NOT EXISTS idx_timeline_data 
            ON timeline_log(data_evento);
        """)
        
        op.execute("""
            CREATE INDEX IF NOT EXISTS idx_gamificacao_user_period 
            ON gamificacao_metricas_mensais(usuario_cs, ano, mes);
        """)


def downgrade():
    """Remove os índices criados."""
    
    conn = op.get_bind()
    dialect = conn.dialect.name

    op.execute("DROP INDEX IF EXISTS idx_impl_data_criacao;")
    op.execute("DROP INDEX IF EXISTS idx_impl_data_finalizacao;")
    op.execute("DROP INDEX IF EXISTS idx_comentarios_visibilidade;")
    op.execute("DROP INDEX IF EXISTS idx_comentarios_data;")
    op.execute("DROP INDEX IF EXISTS idx_gamificacao_ano_mes;")
    op.execute("DROP INDEX IF EXISTS idx_timeline_data;")
    op.execute("DROP INDEX IF EXISTS idx_gamificacao_user_period;")

