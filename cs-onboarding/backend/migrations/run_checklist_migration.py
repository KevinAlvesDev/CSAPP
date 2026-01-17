"""
Script para executar a migração do checklist de finalização
"""

import sys
from pathlib import Path

# Adicionar o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.project import create_app
from backend.project.database import get_db_connection


def run_migration():
    """Executa a migração 003_add_checklist_finalizacao"""
    app = create_app()

    with app.app_context():
        conn, db_type = get_db_connection()
        cursor = conn.cursor()

        try:
            # Importar a migração
            from versions import add_checklist_finalizacao_003 as migration

            print(f"[INFO] Executando migracao para {db_type}...")

            if db_type == "postgres":
                migration.upgrade_postgres(cursor)
            else:
                migration.upgrade_sqlite(cursor)

            conn.commit()
            print("[OK] Migracao executada com sucesso!")
            print("[INFO] Tabelas criadas:")
            print("   - checklist_finalizacao_templates")
            print("   - checklist_finalizacao_items")
            print("[OK] 10 templates padrao inseridos")

        except Exception as e:
            conn.rollback()
            print(f"[ERRO] Erro ao executar migracao: {e}")
            import traceback

            traceback.print_exc()
            sys.exit(1)
        finally:
            cursor.close()
            conn.close()


if __name__ == "__main__":
    run_migration()
