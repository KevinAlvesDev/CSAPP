"""
Migração: Adicionar coluna definicao_carteira na tabela implantacoes

Esta migração adiciona um campo TEXT para armazenar informações detalhadas
sobre a definição de carteira de cada implantação.
"""

import os
import sqlite3

from dotenv import load_dotenv

load_dotenv()


def run_migration():
    """Executa a migração para adicionar a coluna definicao_carteira."""

    # Detectar tipo de banco de dados
    database_url = os.getenv("DATABASE_URL", "")

    if database_url.startswith("postgresql://"):
        run_postgres_migration()
    else:
        run_sqlite_migration()


def run_postgres_migration():
    """Executa a migração para PostgreSQL."""
    import psycopg2

    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    cur = conn.cursor()

    try:
        print("Iniciando migração PostgreSQL: adicionar coluna definicao_carteira...")

        # Verificar se a coluna já existe
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='implantacoes' 
            AND column_name='definicao_carteira'
        """)

        if cur.fetchone():
            print("✓ Coluna definicao_carteira já existe. Nada a fazer.")
            return

        # Adicionar coluna
        cur.execute("""
            ALTER TABLE implantacoes 
            ADD COLUMN definicao_carteira TEXT
        """)

        conn.commit()
        print("✓ Coluna definicao_carteira adicionada com sucesso!")

    except Exception as e:
        conn.rollback()
        print(f"✗ Erro na migração: {e}")
        raise

    finally:
        cur.close()
        conn.close()


def run_sqlite_migration():
    """Executa a migração para SQLite."""
    db_path = os.getenv("DATABASE_URL", "")

    if not db_path or not db_path.startswith("postgresql://"):
        # Usar caminho relativo ao diretório do projeto
        script_dir = os.path.dirname(os.path.abspath(__file__))
        # migrations -> database -> project -> backend -> cs-onboarding
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(script_dir))))
        db_path = os.path.join(project_root, "backend", "project", "dashboard_simples.db")
    elif db_path.startswith("sqlite:///"):
        db_path = db_path.replace("sqlite:///", "")

    print(f"Conectando ao banco: {db_path}")
    print(f"Banco existe: {os.path.exists(db_path)}")

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    try:
        print("Iniciando migracao SQLite: adicionar coluna definicao_carteira...")

        # Listar tabelas
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cur.fetchall()]
        print(f"Tabelas encontradas: {tables}")

        # Verificar se a coluna já existe
        cur.execute("PRAGMA table_info(implantacoes)")
        columns = [row[1] for row in cur.fetchall()]
        print(f"Colunas da tabela implantacoes: {len(columns)} colunas")

        if "definicao_carteira" in columns:
            print("OK - Coluna definicao_carteira ja existe. Nada a fazer.")
            return

        # Adicionar coluna
        print("Adicionando coluna definicao_carteira...")
        cur.execute("""
            ALTER TABLE implantacoes 
            ADD COLUMN definicao_carteira TEXT
        """)

        conn.commit()
        print("OK - Coluna definicao_carteira adicionada com sucesso!")

    except Exception as e:
        conn.rollback()
        print(f"ERRO na migracao: {e}")
        import traceback

        traceback.print_exc()
        raise

    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    run_migration()
