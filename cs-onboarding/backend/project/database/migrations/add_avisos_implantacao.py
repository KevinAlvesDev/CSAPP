"""
Migração: Criar tabela avisos_implantacao

Esta migração cria uma tabela para armazenar avisos personalizados
associados a cada implantação.
"""

import os
import sqlite3

from dotenv import load_dotenv

load_dotenv()


def run_migration():
    """Executa a migração para criar a tabela avisos_implantacao."""

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
        print("Iniciando migracao PostgreSQL: criar tabela avisos_implantacao...")

        # Verificar se a tabela já existe
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_name='avisos_implantacao'
        """)

        if cur.fetchone():
            print("OK - Tabela avisos_implantacao ja existe. Nada a fazer.")
            return

        # Criar tabela
        cur.execute("""
            CREATE TABLE avisos_implantacao (
                id SERIAL PRIMARY KEY,
                implantacao_id INTEGER NOT NULL REFERENCES implantacoes(id) ON DELETE CASCADE,
                tipo VARCHAR(20) NOT NULL DEFAULT 'info',
                titulo VARCHAR(100) NOT NULL,
                mensagem TEXT NOT NULL,
                criado_por VARCHAR(255) NOT NULL,
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT avisos_tipo_check CHECK (tipo IN ('info', 'warning', 'danger', 'success'))
            )
        """)

        # Criar índice para busca rápida
        cur.execute("""
            CREATE INDEX idx_avisos_implantacao_id 
            ON avisos_implantacao(implantacao_id)
        """)

        conn.commit()
        print("OK - Tabela avisos_implantacao criada com sucesso!")
        print("OK - Indice idx_avisos_implantacao_id criado com sucesso!")

    except Exception as e:
        conn.rollback()
        print(f"ERRO na migracao: {e}")
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
        print("Iniciando migracao SQLite: criar tabela avisos_implantacao...")

        # Verificar se a tabela já existe
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='avisos_implantacao'")

        if cur.fetchone():
            print("OK - Tabela avisos_implantacao ja existe. Nada a fazer.")
            return

        # Criar tabela (SQLite não suporta CHECK constraint da mesma forma)
        cur.execute("""
            CREATE TABLE avisos_implantacao (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                implantacao_id INTEGER NOT NULL,
                tipo VARCHAR(20) NOT NULL DEFAULT 'info',
                titulo VARCHAR(100) NOT NULL,
                mensagem TEXT NOT NULL,
                criado_por VARCHAR(255) NOT NULL,
                data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (implantacao_id) REFERENCES implantacoes(id) ON DELETE CASCADE
            )
        """)

        # Criar índice para busca rápida
        cur.execute("""
            CREATE INDEX idx_avisos_implantacao_id 
            ON avisos_implantacao(implantacao_id)
        """)

        conn.commit()
        print("OK - Tabela avisos_implantacao criada com sucesso!")
        print("OK - Indice idx_avisos_implantacao_id criado com sucesso!")

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
