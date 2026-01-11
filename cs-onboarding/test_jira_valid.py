
import os
import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv

load_dotenv(override=True)

def test_valid_jql():
    url = os.getenv('JIRA_URL')
    user = os.getenv('JIRA_USER')
    token = os.getenv('JIRA_API_TOKEN')

    if url.endswith('/'): url = url[:-1]
    
    # Rota correta
    target_url = f"{url}/rest/api/3/search/jql"
    
    auth = HTTPBasicAuth(user, token)
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    
    # Query restritiva válida
    jql_query = 'project IS NOT EMPTY ORDER BY created DESC'
    
    print(f"--- Testando NOVA rota com query VALIDA: {target_url} ---\n")

    try:
        payload = {
            "jql": jql_query,
            "maxResults": 1,
            "fields": ["summary", "status", "created"]
        }
        resp = requests.post(
            target_url, 
            auth=auth, 
            headers=headers,
            json=payload
        )
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            print("SUCESSO!")
            data = resp.json()
            print("Estrutura da resposta:")
            # Printar chaves de topo para ver se é 'issues' ou 'values'
            print(data.keys())
            if 'issues' in data:
                print("Formato mantido: 'issues' presente.")
                print(f"Exemplo: {data['issues'][0]['key']}")
            else:
                print("FORMATO ALTERADO! Verifique output.")
                print(data)
        else:
            print(f"Erro: {resp.text}")

    except Exception as e:
        print(f"Exceção: {e}")

if __name__ == "__main__":
    test_valid_jql()
