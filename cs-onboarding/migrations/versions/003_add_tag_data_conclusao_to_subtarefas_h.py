"""add tag and data_conclusao to subtarefas_h

Revision ID: 003_tag_data_conclusao
Revises: 002_plano_id
Create Date: 2025-01-13

Adiciona colunas tag e data_conclusao na tabela subtarefas_h para suportar
funcionalidades de analytics e gamificação que dependem desses campos.
Migração da estrutura antiga (tarefas) para estrutura hierárquica.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision = '003_tag_data_conclusao'
down_revision = '002_plano_id'
branch_labels = None
depends_on = None


def upgrade():
    """
    Adiciona colunas tag e data_conclusao na tabela subtarefas_h.
    - tag: VARCHAR(100) - Categoria da subtarefa (ex: 'Ação interna', 'Reunião')
    - data_conclusao: TIMESTAMP - Data/hora em que a subtarefa foi concluída
    - Ambos permitem NULL para compatibilidade com dados existentes
    - Índices criados para performance em queries de analytics/gamificação
    """
    conn = op.get_bind()
    dialect = conn.dialect.name
    
    if dialect == 'postgresql':
        # PostgreSQL
        # Adicionar coluna tag
        op.execute(text("""
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'subtarefas_h' AND column_name = 'tag') THEN
                    ALTER TABLE subtarefas_h ADD COLUMN tag VARCHAR(100);
                END IF;
            END$$;
        """))
        
        # Adicionar coluna data_conclusao
        op.execute(text("""
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'subtarefas_h' AND column_name = 'data_conclusao') THEN
                    ALTER TABLE subtarefas_h ADD COLUMN data_conclusao TIMESTAMP;
                END IF;
            END$$;
        """))
        
        # Criar índices para performance em queries de analytics/gamificação
        op.execute(text("""
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE c.relname = 'idx_subtarefas_h_tag' AND n.nspname = 'public') THEN
                    CREATE INDEX idx_subtarefas_h_tag ON subtarefas_h(tag);
                END IF;
            END$$;
        """))
        
        op.execute(text("""
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE c.relname = 'idx_subtarefas_h_data_conclusao' AND n.nspname = 'public') THEN
                    CREATE INDEX idx_subtarefas_h_data_conclusao ON subtarefas_h(data_conclusao);
                END IF;
            END$$;
        """))
        
        # Índice composto para queries frequentes (tag + data_conclusao + concluido)
        op.execute(text("""
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE c.relname = 'idx_subtarefas_h_tag_data_concluido' AND n.nspname = 'public') THEN
                    CREATE INDEX idx_subtarefas_h_tag_data_concluido ON subtarefas_h(tag, data_conclusao, concluido);
                END IF;
            END$$;
        """))
        
    else:
        # SQLite
        # Verificar se colunas já existem
        cursor = conn.connection.cursor()
        cursor.execute("PRAGMA table_info(subtarefas_h)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'tag' not in columns:
            # Adicionar coluna tag
            op.execute(text("""
                ALTER TABLE subtarefas_h 
                ADD COLUMN tag TEXT
            """))
            
            # Criar índice
            op.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_subtarefas_h_tag 
                ON subtarefas_h(tag)
            """))
        
        if 'data_conclusao' not in columns:
            # Adicionar coluna data_conclusao
            op.execute(text("""
                ALTER TABLE subtarefas_h 
                ADD COLUMN data_conclusao DATETIME
            """))
            
            # Criar índice
            op.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_subtarefas_h_data_conclusao 
                ON subtarefas_h(data_conclusao)
            """))
        
        # Índice composto (SQLite suporta índices compostos)
        op.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_subtarefas_h_tag_data_concluido 
            ON subtarefas_h(tag, data_conclusao, concluido)
        """))
    
    print("Colunas tag e data_conclusao adicionadas à tabela subtarefas_h")
    print("Índices de performance criados")


def downgrade():
    """Remove as colunas tag e data_conclusao da tabela subtarefas_h."""
    conn = op.get_bind()
    dialect = conn.dialect.name
    
    # Remover índices primeiro
    op.execute(text("DROP INDEX IF EXISTS idx_subtarefas_h_tag_data_concluido"))
    op.execute(text("DROP INDEX IF EXISTS idx_subtarefas_h_data_conclusao"))
    op.execute(text("DROP INDEX IF EXISTS idx_subtarefas_h_tag"))
    
    if dialect == 'postgresql':
        # PostgreSQL
        op.execute(text("ALTER TABLE subtarefas_h DROP COLUMN IF EXISTS data_conclusao"))
        op.execute(text("ALTER TABLE subtarefas_h DROP COLUMN IF EXISTS tag"))
    else:
        # SQLite não suporta DROP COLUMN facilmente
        # Em produção, seria necessário recriar a tabela
        print("SQLite não suporta DROP COLUMN. As colunas tag e data_conclusao permanecerão na tabela.")
        print("   Se necessário, recrie a tabela manualmente.")
    
    print("Colunas tag e data_conclusao removidas (ou marcadas para remoção)")

