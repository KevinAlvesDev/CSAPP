"""
Migration: Adicionar Índices Compostos para Otimização de Performance
Data: 2026-01-05
Objetivo: Melhorar performance de queries críticas do sistema

Índices criados:
1. idx_checklist_impl_completed - Para queries de progresso por implantação
2. idx_checklist_parent_ordem - Para navegação hierárquica ordenada
3. idx_implantacoes_user_status - Para dashboard filtrado por usuário
4. idx_comentarios_item_data - Para histórico de comentários
5. idx_timeline_impl_data - Para timeline ordenada
"""

import logging
import os

from ...database.db_pool import get_db_connection

logger = logging.getLogger(__name__)


def run_migration():
    """
    Executa a migration de índices compostos.
    """
    conn, db_type = get_db_connection()
    cursor = conn.cursor()
    
    try:
        logger.info("Iniciando migration de índices compostos...")
        
        # Helper para verificar se tabela existe
        def table_exists(table_name):
            if db_type == 'postgres':
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = %s
                    )
                """, (table_name,))
                return cursor.fetchone()[0]
            else:
                cursor.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name=?
                """, (table_name,))
                return cursor.fetchone() is not None
        
        # 1. Índice para queries de progresso do checklist
        if table_exists('checklist_items'):
            logger.info("Criando idx_checklist_impl_completed...")
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_checklist_impl_completed 
                ON checklist_items(implantacao_id, completed)
            """)
        
        # 2. Índice para navegação hierárquica com ordenação
        if table_exists('checklist_items'):
            logger.info("Criando idx_checklist_parent_ordem...")
            if db_type == 'postgres':
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_checklist_parent_ordem 
                    ON checklist_items(parent_id, ordem, id) 
                    WHERE parent_id IS NOT NULL
                """)
            else:
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_checklist_parent_ordem 
                    ON checklist_items(parent_id, ordem, id)
                """)
        
        # 3. Índice para dashboard filtrado por usuário e status
        if table_exists('implantacoes'):
            logger.info("Criando idx_implantacoes_user_status...")
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_implantacoes_user_status 
                ON implantacoes(usuario_cs, status, data_criacao)
            """)
        
        # 4. Índice para histórico de comentários por item
        if table_exists('comentarios_h'):
            logger.info("Criando idx_comentarios_item_data...")
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_comentarios_item_data 
                ON comentarios_h(checklist_item_id, data_criacao DESC)
            """)
        
        # 5. Índice para timeline ordenada por implantação
        if table_exists('timeline_log'):
            logger.info("Criando idx_timeline_impl_data...")
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_timeline_impl_data 
                ON timeline_log(implantacao_id, data_criacao DESC)
            """)
        else:
            logger.warning("Tabela 'timeline_log' não existe, pulando índice...")
        
        # 6. Índice para busca de responsáveis
        if table_exists('perfil_usuario'):
            logger.info("Criando idx_perfil_usuario...")
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_perfil_usuario 
                ON perfil_usuario(usuario)
            """)
        
        # 7. Índice para queries de checklist por tipo de item
        if table_exists('checklist_items'):
            logger.info("Criando idx_checklist_tipo...")
            if db_type == 'postgres':
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_checklist_tipo 
                    ON checklist_items(tipo_item, implantacao_id, completed) 
                    WHERE tipo_item IS NOT NULL
                """)
            else:
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_checklist_tipo 
                    ON checklist_items(tipo_item, implantacao_id, completed)
                """)
        
        conn.commit()
        logger.info("✅ Migration de índices compostos concluída com sucesso!")
        
        # Estatísticas dos índices criados
        if db_type == 'postgres':
            cursor.execute("""
                SELECT 
                    schemaname,
                    tablename,
                    indexname,
                    indexdef
                FROM pg_indexes
                WHERE indexname LIKE 'idx_%'
                ORDER BY tablename, indexname
            """)
            indices = cursor.fetchall()
            logger.info(f"Total de índices criados: {len(indices)}")
            for idx in indices:
                logger.info(f"  - {idx[2]} em {idx[1]}")
        
        return True
        
    except Exception as e:
        conn.rollback()
        logger.error(f"❌ Erro ao executar migration de índices: {e}", exc_info=True)
        return False
        
    finally:
        cursor.close()
        conn.close()


def rollback_migration():
    """
    Reverte a migration removendo os índices.
    """
    conn, db_type = get_db_connection()
    cursor = conn.cursor()
    
    try:
        logger.info("Revertendo migration de índices compostos...")
        
        indices = [
            'idx_checklist_impl_completed',
            'idx_checklist_parent_ordem',
            'idx_implantacoes_user_status',
            'idx_comentarios_item_data',
            'idx_timeline_impl_data',
            'idx_perfil_usuario',
            'idx_checklist_tipo'
        ]
        
        for idx_name in indices:
            logger.info(f"Removendo {idx_name}...")
            cursor.execute(f"DROP INDEX IF EXISTS {idx_name}")
        
        conn.commit()
        logger.info("✅ Rollback concluído com sucesso!")
        return True
        
    except Exception as e:
        conn.rollback()
        logger.error(f"❌ Erro ao reverter migration: {e}", exc_info=True)
        return False
        
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    # Detectar se é SQLite local ou Postgres
    use_sqlite = os.environ.get('USE_SQLITE_LOCALLY', '').lower() in ('true', '1', 'yes')
    
    if use_sqlite:
        print("⚠️  Executando em SQLite LOCAL")
    else:
        print("🐘 Executando em PostgreSQL")
    
    success = run_migration()
    
    if success:
        print("\n✅ Migration executada com sucesso!")
        print("\nPróximos passos:")
        print("1. Testar performance das queries")
        print("2. Monitorar uso dos índices com EXPLAIN ANALYZE")
        print("3. Ajustar índices conforme necessário")
    else:
        print("\n❌ Falha na migration. Verifique os logs.")
