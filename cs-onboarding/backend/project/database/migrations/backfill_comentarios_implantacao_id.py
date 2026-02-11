"""
Migração: Preencher implantacao_id para comentários existentes em produção.

Executar UMA VEZ após o deploy para garantir que comentários existentes
tenham o implantacao_id preenchido corretamente.

Como executar:
    cd backend
    python -m project.database.migrations.backfill_comentarios_implantacao_id
"""

import os
import sys

# Adicionar o diretório raiz ao path para imports funcionarem
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from project.db import get_db_connection


def run_migration():
    """Preenche implantacao_id para comentários existentes."""
    conn = None
    try:
        conn, db_type = get_db_connection()
        cursor = conn.cursor()

        print("=" * 60)
        print("MIGRAÇÃO: Backfill implantacao_id em comentarios_h")
        print("=" * 60)

        # 1. Contar comentários sem implantacao_id
        if db_type == "postgres":
            cursor.execute("""
                SELECT COUNT(*) as total
                FROM comentarios_h
                WHERE implantacao_id IS NULL
                AND checklist_item_id IS NOT NULL
            """)
        else:
            cursor.execute("""
                SELECT COUNT(*) as total
                FROM comentarios_h
                WHERE implantacao_id IS NULL
                AND checklist_item_id IS NOT NULL
            """)

        result = cursor.fetchone()
        total_para_atualizar = result[0] if result else 0

        print(f"Comentários sem implantacao_id: {total_para_atualizar}")

        if total_para_atualizar == 0:
            print("✅ Nenhum comentário precisa ser atualizado.")
            return

        # 2. Atualizar comentários preenchendo implantacao_id
        if db_type == "postgres":
            cursor.execute("""
                UPDATE comentarios_h
                SET implantacao_id = ci.implantacao_id
                FROM checklist_items ci
                WHERE comentarios_h.checklist_item_id = ci.id
                AND comentarios_h.implantacao_id IS NULL
                AND comentarios_h.checklist_item_id IS NOT NULL
            """)
        else:
            # SQLite não suporta UPDATE com FROM, então usamos subquery
            cursor.execute("""
                UPDATE comentarios_h
                SET implantacao_id = (
                    SELECT ci.implantacao_id
                    FROM checklist_items ci
                    WHERE ci.id = comentarios_h.checklist_item_id
                )
                WHERE implantacao_id IS NULL
                AND checklist_item_id IS NOT NULL
            """)

        rows_updated = cursor.rowcount if hasattr(cursor, "rowcount") else total_para_atualizar

        conn.commit()

        print(f"✅ {rows_updated} comentários atualizados com sucesso!")
        print("=" * 60)

    except Exception as e:
        print(f"❌ Erro na migração: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    run_migration()
