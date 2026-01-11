
import sys
import os

# Adicionar diretório atual ao path para importar modulos
sys.path.append(os.getcwd())

from flask import Flask
from backend.project.database import get_db_connection
from backend.project.config import Config

app = Flask(__name__)
# Carregar config basica
app.config.from_object(Config)
print(f"DEBUG: Config USE_SQLITE_LOCALLY = {app.config.get('USE_SQLITE_LOCALLY')}")
print(f"DEBUG: Config DATABASE_URL = {app.config.get('DATABASE_URL')}")


def test_persistence():
    print("--- Teste de Persistência ---")
    try:
        conn, db_type = get_db_connection()
        print(f"Banco conectado: {db_type}")
        
        cursor = conn.cursor()
        
        # 1. Verificar Tabela
        try:
            cursor.execute("SELECT count(*) FROM implantacao_jira_links")
            count = cursor.fetchone()[0]
            print(f"Tabela existe. Contagem atual: {count}")
        except Exception as e:
            print(f"ERRO: Tabela não parece existir ou erro de acesso: {e}")
            return

        # 2. Tentar Inserir Mock
        implantacao_id = 99999
        jira_key = "TEST-123"
        print(f"Tentando inserir vínculo teste: {implantacao_id} -> {jira_key}")
        
        try:
            if db_type == 'sqlite':
                cursor.execute("INSERT OR IGNORE INTO implantacao_jira_links (implantacao_id, jira_key, vinculado_por) VALUES (?, ?, ?)", (implantacao_id, jira_key, 'debug'))
            else:
                cursor.execute("INSERT INTO implantacao_jira_links (implantacao_id, jira_key, vinculado_por) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING", (implantacao_id, jira_key, 'debug'))
            conn.commit()
            print("Commit realizado.")
        except Exception as e:
            print(f"ERRO no Insert: {e}")
            return
            
        # 3. Verificar Inserção
        try:
            if db_type == 'sqlite':
                cursor.execute("SELECT jira_key FROM implantacao_jira_links WHERE implantacao_id = ?", (implantacao_id,))
            else:
                cursor.execute("SELECT jira_key FROM implantacao_jira_links WHERE implantacao_id = %s", (implantacao_id,))
            rows = cursor.fetchall()
            print(f"Recuperado do banco: {rows}")
            if any(r[0] == jira_key for r in rows):
                print("SUCESSO: Persistência funcionou.")
                
                # Cleanup
                if db_type == 'sqlite':
                     cursor.execute("DELETE FROM implantacao_jira_links WHERE implantacao_id = ?", (implantacao_id,))
                else:
                     cursor.execute("DELETE FROM implantacao_jira_links WHERE implantacao_id = %s", (implantacao_id,))
                conn.commit()
                print("Limpeza realizada.")
            else:
                print("FALHA: Dado não encontrado após insert.")
        except Exception as e:
            print(f"ERRO no Select: {e}")
            
    except Exception as e:
        print(f"Erro Geral de Conexão: {e}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()

if __name__ == "__main__":
    with app.app_context():
        test_persistence()
