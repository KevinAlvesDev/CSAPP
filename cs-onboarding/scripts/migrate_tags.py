import sqlite3
import os

# Caminho corrigido baseado no find_by_name
DB_PATH = 'backend/project/dashboard_simples.db'

def migrate_db():
    if not os.path.exists(DB_PATH):
        print(f"Banco de dados não encontrado em {DB_PATH}")
        # Tentar caminho absoluto como fallback
        abs_path = os.path.abspath(DB_PATH)
        print(f"Tentando caminho absoluto: {abs_path}")
        if not os.path.exists(abs_path):
             return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Adicionar tag_escopo
        try:
            cursor.execute("ALTER TABLE comentarios_h ADD COLUMN tag_escopo TEXT")
            print("Coluna tag_escopo adicionada.")
        except sqlite3.OperationalError:
            print("Coluna tag_escopo já existe.")

        # Adicionar tag_tipo
        try:
            cursor.execute("ALTER TABLE comentarios_h ADD COLUMN tag_tipo TEXT")
            print("Coluna tag_tipo adicionada.")
        except sqlite3.OperationalError:
            print("Coluna tag_tipo já existe.")
        
        conn.commit()
        print("Migração concluída com sucesso.")
    except Exception as e:
        print(f"Erro na migração: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_db()
