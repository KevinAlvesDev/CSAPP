"""
Script para executar a migração 005 (Schema Fix)
Adiciona tabelas faltantes (tags_sistema, etc.) e coluna contexto em planos_sucesso.
"""

import sys
from pathlib import Path

# Adicionar o diretório raiz ao path para imports funcionarem
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.project import create_app
from backend.project.database import get_db, get_db_connection

def run_migration():
    """Executa a migração 005_add_missing_schema"""
    
    # Inicializa app para contexto
    app = create_app()

    with app.app_context():
        # Obtém conexão usando a funcão do projeto
        try:
            conn, db_type = get_db_connection()
        except Exception as e:
            print(f"[ERRO] Falha ao conectar ao banco: {e}")
            sys.exit(1)
            
        cursor = conn.cursor()

        try:
            # Importar a migração dinamicamente
            # Assume que o script está em backend/migrations/ e versions em backend/migrations/versions/
            from versions import add_missing_schema_005 as migration

            print(f"🚀 [INFO] Iniciando migração 005 para ambiente: {db_type.upper()}...")

            if db_type == "postgres":
                print("   - Executando upgrade_postgres()...")
                migration.upgrade_postgres(cursor)
            else:
                print("   - Executando upgrade_sqlite()...")
                migration.upgrade_sqlite(cursor)

            conn.commit()
            print("✅ [SUCESSO] Migração 005 executada!")
            print("   - Tabela 'tags_sistema' verificada/criada.")
            print("   - Coluna 'contexto' em 'planos_sucesso' verificada/adicionada.")
            print("   - Tabelas de configuração (status, motivos, etc.) verificadas.")

        except ImportError as ie:
            print(f"[ERRO] Não foi possível importar a migração 'versions.add_missing_schema_005': {ie}")
            print("Verifique se o arquivo existe em backend/migrations/versions/")
        except Exception as e:
            conn.rollback()
            print(f"❌ [ERRO] Falha durante a migração: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
        finally:
            cursor.close()
            conn.close()


if __name__ == "__main__":
    run_migration()
