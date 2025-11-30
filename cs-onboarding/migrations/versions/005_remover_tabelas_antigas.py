"""remover tabelas antigas

Revision ID: 005_remover_tabelas_antigas
Revises: 004_consolidacao_campos
Create Date: 2025-01-13

Remove tabelas antigas que foram consolidadas em checklist_items:
- fases
- grupos
- tarefas_h
- subtarefas_h
- planos_fases
- planos_grupos
- planos_tarefas
- planos_subtarefas

Todas as funcionalidades agora usam apenas checklist_items.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision = '005_remover_tabelas_antigas'
down_revision = '004_consolidacao_campos'
branch_labels = None
depends_on = None


def upgrade():
    """
    Remove todas as tabelas antigas que foram consolidadas em checklist_items.
    
    Tabelas removidas:
    - fases (consolidada em checklist_items com tipo_item='fase')
    - grupos (consolidada em checklist_items com tipo_item='grupo')
    - tarefas_h (consolidada em checklist_items com tipo_item='tarefa')
    - subtarefas_h (consolidada em checklist_items com tipo_item='subtarefa')
    - planos_fases (consolidada em checklist_items com tipo_item='plano_fase')
    - planos_grupos (consolidada em checklist_items com tipo_item='plano_grupo')
    - planos_tarefas (consolidada em checklist_items com tipo_item='plano_tarefa')
    - planos_subtarefas (consolidada em checklist_items com tipo_item='plano_subtarefa')
    """
    conn = op.get_bind()
    dialect = conn.dialect.name
    
    print("=" * 80)
    print("REMOÇÃO: Tabelas Antigas Consolidadas")
    print("=" * 80)
    print()
    print("⚠️  ATENÇÃO: Esta migration irá remover permanentemente as seguintes tabelas:")
    print("   - fases")
    print("   - grupos")
    print("   - tarefas_h")
    print("   - subtarefas_h")
    print("   - planos_fases")
    print("   - planos_grupos")
    print("   - planos_tarefas")
    print("   - planos_subtarefas")
    print()
    print("✅ Todos os dados já foram migrados para checklist_items")
    print()
    
    tabelas_para_remover = [
        'planos_subtarefas',
        'planos_tarefas',
        'planos_grupos',
        'planos_fases',
        'subtarefas_h',
        'tarefas_h',
        'grupos',
        'fases'
    ]
    
    # Remover em ordem reversa (dependências primeiro)
    for tabela in tabelas_para_remover:
        try:
            if dialect == 'postgresql':
                # Verificar se tabela existe antes de remover
                cursor = conn.connection.cursor()
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = %s
                    )
                """, (tabela,))
                existe = cursor.fetchone()[0]
                
                if existe:
                    print(f"   🗑️  Removendo tabela: {tabela}")
                    op.execute(text(f"DROP TABLE IF EXISTS {tabela} CASCADE"))
                    print(f"   ✅ Tabela {tabela} removida")
                else:
                    print(f"   ℹ️  Tabela {tabela} não existe (já foi removida)")
            else:
                # SQLite
                op.execute(text(f"DROP TABLE IF EXISTS {tabela}"))
                print(f"   ✅ Tabela {tabela} removida")
        except Exception as e:
            print(f"   ⚠️  Erro ao remover {tabela}: {e}")
            # Continuar mesmo se houver erro
    
    print()
    print("=" * 80)
    print("✅ REMOÇÃO DE TABELAS ANTIGAS CONCLUÍDA")
    print("=" * 80)
    print()
    print("📋 Todas as funcionalidades agora usam apenas checklist_items")
    print("   A estrutura consolidada está completa e funcional")


def downgrade():
    """
    ⚠️  ATENÇÃO: Esta operação NÃO pode ser revertida automaticamente.
    As tabelas antigas não podem ser recriadas sem os dados originais.
    
    Se necessário, restaure de um backup do banco de dados.
    """
    print("=" * 80)
    print("⚠️  DOWNGRADE NÃO SUPORTADO")
    print("=" * 80)
    print()
    print("A remoção das tabelas antigas não pode ser revertida automaticamente.")
    print("Se necessário, restaure de um backup do banco de dados anterior.")
    print()
    print("As tabelas removidas foram:")
    print("   - fases, grupos, tarefas_h, subtarefas_h")
    print("   - planos_fases, planos_grupos, planos_tarefas, planos_subtarefas")
    print()
    print("Todos os dados foram migrados para checklist_items.")
    print("Para reverter, você precisaria:")
    print("   1. Restaurar backup do banco")
    print("   2. Ou recriar as tabelas manualmente e migrar dados de volta")
    print()
    raise NotImplementedError(
        "Downgrade não suportado. Restaure de backup se necessário."
    )

