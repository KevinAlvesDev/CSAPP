"""
Migration: Adiciona CASCADE na foreign key de comentarios_h

Problema: Quando deletamos checklist_items, os comentários ficam órfãos
porque a FK está com ON DELETE NO ACTION.

Solução: Recriar a FK com ON DELETE CASCADE para deletar comentários automaticamente.
"""

import psycopg2

def migrate_add_cascade_fk(conn):
    """
    Adiciona CASCADE na foreign key comentarios_h -> checklist_items
    """
    cursor = conn.cursor()
    
    try:
        print("Iniciando migration: Adicionar CASCADE na FK...")
        
        # 1. Dropar a constraint antiga
        print("[1/2] Removendo constraint antiga fk_comentarios_item...")
        cursor.execute("""
            ALTER TABLE comentarios_h 
            DROP CONSTRAINT IF EXISTS fk_comentarios_item
        """)
        
        # 2. Adicionar nova constraint com CASCADE
        print("[2/2] Adicionando nova constraint com ON DELETE CASCADE...")
        cursor.execute("""
            ALTER TABLE comentarios_h 
            ADD CONSTRAINT fk_comentarios_item 
            FOREIGN KEY (checklist_item_id) 
            REFERENCES checklist_items(id) 
            ON DELETE CASCADE
        """)
        
        conn.commit()
        print("[OK] Migration concluida com sucesso!")
        
    except Exception as e:
        conn.rollback()
        print(f"[ERRO] Erro durante migration: {e}")
        raise
    finally:
        cursor.close()


if __name__ == '__main__':
    print("=" * 80)
    print("MIGRATION: Adicionar CASCADE na FK comentarios_h")
    print("=" * 80)
    
    conn = psycopg2.connect("postgresql://postgres:sChnKAdWRKtVXxTIDcQSPKKYrEMbTxNi@switchyard.proxy.rlwy.net:48993/railway")
    
    try:
        migrate_add_cascade_fk(conn)
        print("\n" + "=" * 80)
        print("MIGRATION FINALIZADA")
        print("=" * 80)
    except Exception as e:
        print(f"\nERRO: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()
        print("\nConexao fechada.")
