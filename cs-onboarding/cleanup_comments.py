"""
Script de limpeza: Limpa o campo 'comment' de checklist_items 
que não têm comentários no histórico (comentarios_h).

Execute este script no ambiente de produção para corrigir dados existentes.
"""
import os
import sys

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def cleanup_orphan_comments():
    """Limpa campos 'comment' órfãos (sem histórico correspondente)."""
    
    from backend.project import create_app
    from backend.project.db import query_db, execute_db
    
    app = create_app()
    
    with app.app_context():
        # Busca todos os itens que têm 'comment' preenchido
        items_with_comment = query_db("""
            SELECT id, title, comment 
            FROM checklist_items 
            WHERE comment IS NOT NULL AND comment != ''
        """)
        
        if not items_with_comment:
            print("Nenhum item com campo 'comment' preenchido encontrado.")
            return
        
        print(f"Encontrados {len(items_with_comment)} itens com campo 'comment' preenchido.")
        
        cleaned_count = 0
        
        for item in items_with_comment:
            item_id = item['id']
            
            # Verifica se há comentários no histórico para este item
            history = query_db(
                "SELECT COUNT(*) as cnt FROM comentarios_h WHERE checklist_item_id = %s",
                (item_id,), one=True
            )
            
            if history and history.get('cnt', 0) == 0:
                # Não há comentários no histórico, limpa o campo legado
                execute_db(
                    "UPDATE checklist_items SET comment = NULL WHERE id = %s",
                    (item_id,)
                )
                print(f"  [OK] Limpado: Item ID {item_id} - '{item.get('title', 'Sem titulo')[:50]}'")
                cleaned_count += 1
        
        print(f"\n=== Limpeza concluída ===")
        print(f"Total de itens verificados: {len(items_with_comment)}")
        print(f"Itens limpos: {cleaned_count}")
        print(f"Itens com histórico válido: {len(items_with_comment) - cleaned_count}")


if __name__ == '__main__':
    print("=== Limpeza de Comentários Órfãos ===\n")
    cleanup_orphan_comments()
