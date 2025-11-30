"""add campos para consolidacao em checklist_items

Revision ID: 004_consolidacao_campos
Revises: 003_tag_data_conclusao
Create Date: 2025-01-13

Adiciona campos necessários em checklist_items para consolidar todas as estruturas
hierárquicas (fases/grupos/tarefas_h/subtarefas_h e planos_*) em uma única tabela.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision = '004_consolidacao_campos'
down_revision = '003_tag_data_conclusao'
branch_labels = None
depends_on = None


def upgrade():
    """
    Adiciona campos necessários para consolidar todas as estruturas hierárquicas.
    
    Campos adicionados:
    - responsavel: Responsável pelo item (fases, grupos, tarefas_h, subtarefas_h)
    - status: Status da tarefa (pendente, concluida, etc.) - para tarefas_h
    - percentual_conclusao: Percentual de conclusão (0-100) - para tarefas_h
    - tag: Categoria da subtarefa (Ação interna, Reunião) - já existe em subtarefas_h
    - data_conclusao: Data de conclusão - já existe em subtarefas_h
    - obrigatoria: Se a tarefa é obrigatória - para planos_tarefas
    - tipo_item: Tipo do item (fase, grupo, tarefa, subtarefa, plano_fase, etc.)
    - descricao: Descrição detalhada (para grupos e planos)
    """
    conn = op.get_bind()
    dialect = conn.dialect.name
    
    if dialect == 'postgresql':
        # PostgreSQL
        
        # Adicionar campo responsavel
        op.execute(text("""
            ALTER TABLE checklist_items 
            ADD COLUMN IF NOT EXISTS responsavel VARCHAR(255)
        """))
        
        # Adicionar campo status
        op.execute(text("""
            ALTER TABLE checklist_items 
            ADD COLUMN IF NOT EXISTS status VARCHAR(50) DEFAULT 'pendente'
        """))
        
        # Adicionar campo percentual_conclusao
        op.execute(text("""
            ALTER TABLE checklist_items 
            ADD COLUMN IF NOT EXISTS percentual_conclusao INTEGER DEFAULT 0
        """))
        
        # Adicionar campo obrigatoria
        op.execute(text("""
            ALTER TABLE checklist_items 
            ADD COLUMN IF NOT EXISTS obrigatoria BOOLEAN DEFAULT false
        """))
        
        # Adicionar campo tipo_item
        op.execute(text("""
            ALTER TABLE checklist_items 
            ADD COLUMN IF NOT EXISTS tipo_item VARCHAR(50)
        """))
        
        # Adicionar campo descricao (diferente de comment)
        op.execute(text("""
            ALTER TABLE checklist_items 
            ADD COLUMN IF NOT EXISTS descricao TEXT
        """))
        
        # Verificar se tag e data_conclusao já existem (da migration 003)
        # Se não existirem, adicionar
        cursor = conn.connection.cursor()
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'checklist_items' 
            AND column_name IN ('tag', 'data_conclusao')
        """)
        existing_columns = [row[0] for row in cursor.fetchall()]
        
        if 'tag' not in existing_columns:
            op.execute(text("""
                ALTER TABLE checklist_items 
                ADD COLUMN tag VARCHAR(100)
            """))
        
        if 'data_conclusao' not in existing_columns:
            op.execute(text("""
                ALTER TABLE checklist_items 
                ADD COLUMN data_conclusao TIMESTAMP
            """))
        
        # Criar índices para performance
        op.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_checklist_responsavel 
            ON checklist_items(responsavel)
        """))
        
        op.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_checklist_status 
            ON checklist_items(status)
        """))
        
        op.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_checklist_tipo_item 
            ON checklist_items(tipo_item)
        """))
        
        op.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_checklist_implantacao_tipo 
            ON checklist_items(implantacao_id, tipo_item)
        """))
        
        op.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_checklist_plano_tipo 
            ON checklist_items(plano_id, tipo_item)
        """))
        
        # Adicionar constraint para percentual_conclusao
        # Primeiro remover se existir, depois adicionar
        try:
            op.execute(text("""
                ALTER TABLE checklist_items 
                DROP CONSTRAINT IF EXISTS chk_percentual_range
            """))
        except Exception:
            pass
        
        op.execute(text("""
            ALTER TABLE checklist_items 
            ADD CONSTRAINT chk_percentual_range 
            CHECK (percentual_conclusao >= 0 AND percentual_conclusao <= 100)
        """))
        
    else:
        # SQLite
        cursor = conn.connection.cursor()
        cursor.execute("PRAGMA table_info(checklist_items)")
        columns = [col[1] for col in cursor.fetchall()]
        
        # Adicionar responsavel
        if 'responsavel' not in columns:
            op.execute(text("""
                ALTER TABLE checklist_items 
                ADD COLUMN responsavel TEXT
            """))
            op.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_checklist_responsavel 
                ON checklist_items(responsavel)
            """))
        
        # Adicionar status
        if 'status' not in columns:
            op.execute(text("""
                ALTER TABLE checklist_items 
                ADD COLUMN status TEXT DEFAULT 'pendente'
            """))
            op.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_checklist_status 
                ON checklist_items(status)
            """))
        
        # Adicionar percentual_conclusao
        if 'percentual_conclusao' not in columns:
            op.execute(text("""
                ALTER TABLE checklist_items 
                ADD COLUMN percentual_conclusao INTEGER DEFAULT 0
            """))
        
        # Adicionar obrigatoria
        if 'obrigatoria' not in columns:
            op.execute(text("""
                ALTER TABLE checklist_items 
                ADD COLUMN obrigatoria INTEGER DEFAULT 0
            """))
        
        # Adicionar tipo_item
        if 'tipo_item' not in columns:
            op.execute(text("""
                ALTER TABLE checklist_items 
                ADD COLUMN tipo_item TEXT
            """))
            op.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_checklist_tipo_item 
                ON checklist_items(tipo_item)
            """))
            op.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_checklist_implantacao_tipo 
                ON checklist_items(implantacao_id, tipo_item)
            """))
            op.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_checklist_plano_tipo 
                ON checklist_items(plano_id, tipo_item)
            """))
        
        # Adicionar descricao
        if 'descricao' not in columns:
            op.execute(text("""
                ALTER TABLE checklist_items 
                ADD COLUMN descricao TEXT
            """))
        
        # Verificar tag e data_conclusao
        if 'tag' not in columns:
            op.execute(text("""
                ALTER TABLE checklist_items 
                ADD COLUMN tag TEXT
            """))
            op.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_checklist_tag 
                ON checklist_items(tag)
            """))
        
        if 'data_conclusao' not in columns:
            op.execute(text("""
                ALTER TABLE checklist_items 
                ADD COLUMN data_conclusao DATETIME
            """))
            op.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_checklist_data_conclusao 
                ON checklist_items(data_conclusao)
            """))
    
    print("✅ Campos de consolidação adicionados à tabela checklist_items")
    print("📊 Índices de performance criados")


def downgrade():
    """Remove os campos adicionados para consolidação."""
    conn = op.get_bind()
    dialect = conn.dialect.name
    
    # Remover índices primeiro
    op.execute(text("DROP INDEX IF EXISTS idx_checklist_plano_tipo"))
    op.execute(text("DROP INDEX IF EXISTS idx_checklist_implantacao_tipo"))
    op.execute(text("DROP INDEX IF EXISTS idx_checklist_tipo_item"))
    op.execute(text("DROP INDEX IF EXISTS idx_checklist_status"))
    op.execute(text("DROP INDEX IF EXISTS idx_checklist_responsavel"))
    
    if dialect == 'postgresql':
        # PostgreSQL
        try:
            op.execute(text("ALTER TABLE checklist_items DROP CONSTRAINT IF EXISTS chk_percentual_range"))
        except Exception:
            pass
        
        op.execute(text("ALTER TABLE checklist_items DROP COLUMN IF EXISTS descricao"))
        op.execute(text("ALTER TABLE checklist_items DROP COLUMN IF EXISTS tipo_item"))
        op.execute(text("ALTER TABLE checklist_items DROP COLUMN IF EXISTS obrigatoria"))
        op.execute(text("ALTER TABLE checklist_items DROP COLUMN IF EXISTS percentual_conclusao"))
        op.execute(text("ALTER TABLE checklist_items DROP COLUMN IF EXISTS status"))
        op.execute(text("ALTER TABLE checklist_items DROP COLUMN IF EXISTS responsavel"))
    else:
        # SQLite não suporta DROP COLUMN facilmente
        print("⚠️ SQLite não suporta DROP COLUMN. As colunas permanecerão na tabela.")
        print("   Se necessário, recrie a tabela manualmente.")
    
    print("✅ Campos de consolidação removidos (ou marcados para remoção)")

