"""
Script de migração: Adiciona índices de performance no banco de dados.

Índices adicionados:
1. implantacoes.status - Muito usado em filtros e agrupamentos
2. implantacoes.usuario_cs - Usado em todos os filtros por CS
3. implantacoes.data_criacao - Usado em ordenação
4. implantacoes.data_finalizacao - Usado em relatórios
5. timeline_log.implantacao_id - Usado para buscar logs
6. timeline_log.data_evento - Usado para ordenar timeline
7. comentarios_h.data_criacao - Usado para ordenar comentários
8. comentarios_h.usuario_cs - Usado para relatório de tags

Execute em produção: python migrate_performance_indexes.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def add_performance_indexes():
    """Adiciona índices para melhorar performance das queries."""
    
    from backend.project import create_app
    from backend.project.db import execute_db, query_db
    
    app = create_app()
    
    indexes = [
        # Tabela implantacoes
        ("idx_implantacoes_status", "implantacoes", "status"),
        ("idx_implantacoes_usuario_cs", "implantacoes", "usuario_cs"),
        ("idx_implantacoes_data_criacao", "implantacoes", "data_criacao"),
        ("idx_implantacoes_data_finalizacao", "implantacoes", "data_finalizacao"),
        ("idx_implantacoes_tipo", "implantacoes", "tipo"),
        
        # Tabela timeline_log
        ("idx_timeline_log_implantacao_id", "timeline_log", "implantacao_id"),
        ("idx_timeline_log_data_evento", "timeline_log", "data_evento"),
        
        # Tabela comentarios_h
        ("idx_comentarios_h_data_criacao", "comentarios_h", "data_criacao"),
        ("idx_comentarios_h_usuario_cs", "comentarios_h", "usuario_cs"),
        
        # Tabela checklist_items
        ("idx_checklist_items_completed", "checklist_items", "completed"),
        ("idx_checklist_items_data_conclusao", "checklist_items", "data_conclusao"),
        
        # Tabela perfil_usuario
        ("idx_perfil_usuario_perfil_acesso", "perfil_usuario", "perfil_acesso"),
    ]
    
    with app.app_context():
        is_sqlite = app.config.get('USE_SQLITE_LOCALLY', False)
        
        print("=== Adicionando Indices de Performance ===\n")
        
        created = 0
        skipped = 0
        failed = 0
        
        for idx_name, table, column in indexes:
            try:
                sql = f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table} ({column})"
                execute_db(sql)
                print(f"  [OK] {idx_name} ({table}.{column})")
                created += 1
            except Exception as e:
                if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                    print(f"  [SKIP] {idx_name} (ja existe)")
                    skipped += 1
                else:
                    print(f"  [ERRO] {idx_name}: {e}")
                    failed += 1
        
        # Índices compostos para queries específicas
        composite_indexes = [
            ("idx_implantacoes_status_usuario", "implantacoes", "status, usuario_cs"),
            ("idx_comentarios_h_item_data", "comentarios_h", "checklist_item_id, data_criacao"),
        ]
        
        print("\n=== Indices Compostos ===\n")
        
        for idx_name, table, columns in composite_indexes:
            try:
                sql = f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table} ({columns})"
                execute_db(sql)
                print(f"  [OK] {idx_name}")
                created += 1
            except Exception as e:
                if "already exists" in str(e).lower():
                    print(f"  [SKIP] {idx_name} (ja existe)")
                    skipped += 1
                else:
                    print(f"  [ERRO] {idx_name}: {e}")
                    failed += 1
        
        print(f"\n=== Resultado ===")
        print(f"Criados: {created}")
        print(f"Ja existiam: {skipped}")
        print(f"Erros: {failed}")


if __name__ == '__main__':
    add_performance_indexes()
