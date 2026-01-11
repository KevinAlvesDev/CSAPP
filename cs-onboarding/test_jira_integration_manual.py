import sys
import os
sys.path.append(os.getcwd())

from flask import Flask, g
from backend.project.config import Config
from backend.project.database import get_db_connection
from backend.project.domain.jira_service import search_issues_by_context

app = Flask(__name__)
app.config.from_object(Config)

def test_jira_service():
    print("--- Teste Jira Service ---")
    with app.app_context():
        # 1. Recuperar extra_keys do DB para ID 99999 (criado pelo verify_db.py)
        implantacao_id = 99999
        conn, db_type = get_db_connection()
        print(f"DB Type: {db_type}")
        
        extra_keys = []
        try:
            cur = conn.cursor()
            query = "SELECT jira_key FROM implantacao_jira_links WHERE implantacao_id = ?" if db_type == 'sqlite' else "SELECT jira_key FROM implantacao_jira_links WHERE implantacao_id = %s"
            cur.execute(query, (implantacao_id,))
            rows = cur.fetchall()
            extra_keys = [r[0] for r in rows]
            print(f"Extra Keys encontradas no DB: {extra_keys}")
        except Exception as e:
            print(f"Erro ao ler DB: {e}")
        finally:
            conn.close()

        if not extra_keys:
            print("Nenhuma key encontrada. Execute verify_db.py primeiro para popular o mock.")
            # Vamos forçar uma key para testar a busca mesmo assim
            extra_keys = ['TEST-123']
            print(f"Usando keys fallback: {extra_keys}")

        # 2. Chamar search_issues_by_context
        # Mock de dados da implantação
        implantacao = {'nome_empresa': 'DebugCompanyIgnore'} 
        
        print("Chamando search_issues_by_context...")
        result = search_issues_by_context(implantacao, extra_keys=extra_keys)
        print("Resultado da busca:")
        print(result)

        if 'issues' in result:
            print(f"Total issues retornadas: {len(result['issues'])}")
            for issue in result['issues']:
                print(f" - {issue['key']} (Linked: {issue.get('is_linked')})")
        else:
            print("Erro retornado na busca.")

if __name__ == "__main__":
    test_jira_service()
