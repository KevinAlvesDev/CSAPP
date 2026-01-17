"""
Migration: Fix timezone na coluna data_criacao da tabela comentarios_h

Problema: A coluna data_criacao está como 'timestamp without time zone',
causando problemas de cálculo de diferença de tempo quando comparado com NOW() (que retorna UTC).

Solução: Converter para 'timestamp with time zone' assumindo que os dados existentes
estão em 'America/Sao_Paulo' (UTC-3).
"""


def migrate_comentarios_timezone(conn):
    """
    Migra a coluna data_criacao de comentarios_h para timestamp with time zone.

    Args:
        conn: Conexão com o banco de dados (psycopg2 ou sqlite3)
    """
    cursor = conn.cursor()

    try:
        # Detectar tipo de banco
        cursor.execute("SELECT version()")
        version = cursor.fetchone()[0]
        is_postgres = "PostgreSQL" in version

        if is_postgres:
            print("Iniciando migration para PostgreSQL...")

            # 1. Verificar se a coluna já está com timezone
            cursor.execute("""
                SELECT data_type 
                FROM information_schema.columns 
                WHERE table_name = 'comentarios_h' 
                AND column_name = 'data_criacao'
            """)
            result = cursor.fetchone()

            if result and "with time zone" in result[0]:
                print("[OK] Coluna data_criacao ja esta com timezone. Migration nao necessaria.")
                return

            print("[1/6] Coluna atual: timestamp without time zone")

            # 2. Adicionar coluna temporária com timezone
            print("[2/6] Criando coluna temporaria data_criacao_tz...")
            cursor.execute("""
                ALTER TABLE comentarios_h 
                ADD COLUMN IF NOT EXISTS data_criacao_tz TIMESTAMP WITH TIME ZONE
            """)

            # 3. Copiar dados convertendo para timezone correto
            # Assumimos que os dados existentes estão em 'America/Sao_Paulo'
            print("[3/6] Copiando dados e convertendo timezone...")
            cursor.execute("""
                UPDATE comentarios_h 
                SET data_criacao_tz = timezone('America/Sao_Paulo', data_criacao)
                WHERE data_criacao_tz IS NULL
            """)

            rows_updated = cursor.rowcount
            print(f"[3/6] {rows_updated} registros convertidos")

            # 4. Remover coluna antiga
            print("[4/6] Removendo coluna antiga...")
            cursor.execute("""
                ALTER TABLE comentarios_h 
                DROP COLUMN data_criacao
            """)

            # 5. Renomear coluna nova
            print("[5/6] Renomeando coluna nova...")
            cursor.execute("""
                ALTER TABLE comentarios_h 
                RENAME COLUMN data_criacao_tz TO data_criacao
            """)

            # 6. Recriar índice
            print("[6/6] Recriando indices...")
            cursor.execute("""
                DROP INDEX IF EXISTS idx_comentarios_h_data_criacao
            """)
            cursor.execute("""
                CREATE INDEX idx_comentarios_h_data_criacao 
                ON comentarios_h (data_criacao)
            """)
            cursor.execute("""
                DROP INDEX IF EXISTS idx_comentarios_h_item_data
            """)
            cursor.execute("""
                CREATE INDEX idx_comentarios_h_item_data 
                ON comentarios_h (checklist_item_id, data_criacao)
            """)

            conn.commit()
            print("[OK] Migration concluida com sucesso!")

        else:
            # SQLite não tem timezone nativo, então não fazemos nada
            print("SQLite detectado - timezone sera gerenciado pela aplicacao")

    except Exception as e:
        conn.rollback()
        print(f"[ERRO] Erro durante migration: {e}")
        raise
    finally:
        cursor.close()


if __name__ == "__main__":
    """
    Script standalone para executar a migration
    """
    import os
    import sys

    # Adicionar path do backend
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

    from project import create_app
    from project.db import get_db_connection

    app = create_app()

    with app.app_context():
        print("=" * 80)
        print("MIGRATION: Fix Timezone em comentarios_h.data_criacao")
        print("=" * 80)

        conn = get_db_connection()

        try:
            migrate_comentarios_timezone(conn)
            print("\n" + "=" * 80)
            print("MIGRATION FINALIZADA")
            print("=" * 80)
        except Exception as e:
            print(f"\nERRO: {e}")
            sys.exit(1)
        finally:
            conn.close()
