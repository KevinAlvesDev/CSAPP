
import os
import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv

load_dotenv(override=True)

def test_new_route():
    url = os.getenv('JIRA_URL')
    user = os.getenv('JIRA_USER')
    token = os.getenv('JIRA_API_TOKEN')

    if url.endswith('/'): url = url[:-1]
    
    # Rota sugerida pelo erro 410
    target_url = f"{url}/rest/api/3/search/jql"
    
    auth = HTTPBasicAuth(user, token)
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    
    jql_query = 'order by created DESC'
    
    print(f"--- Testando NOVA rota: {target_url} ---\n")

    # TENTATIVA 1: GET
    print("1. Tentando GET com query params...")
    try:
        resp = requests.get(
            target_url, 
            auth=auth, 
            headers=headers,
            params={'jql': jql_query, 'maxResults': 1}
        )
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            print("SUCESSO (GET)!")
            print(resp.json())
            return
        else:
            print(f"Erro: {resp.text[:200]}")
    except Exception as e:
        print(f"Exceção: {e}")

    print("\n2. Tentando POST com JSON (Schema antigo)...")
    try:
        payload = {
            "jql": jql_query,
            "maxResults": 1,
            "fields": ["summary", "status"]
        }
        resp = requests.post(
            target_url, 
            auth=auth, 
            headers=headers,
            json=payload
        )
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            print("SUCESSO (POST)!")
            print(resp.json())
            return
        else:
            print(f"Erro: {resp.text[:200]}")
    except Exception as e:
        print(f"Exceção: {e}")
        
    print("\n3. Tentando POST com JSON (Schema novo simples 'query'??)...")
    try:
        payload = {
            "query": jql_query, # Chute
        }
        resp = requests.post(
            target_url, 
            auth=auth, 
            headers=headers,
            json=payload
        )
        print(f"Status: {resp.status_code}")
        print(f"Body: {resp.text[:200]}")
    except Exception as e:
        print(f"Exceção: {e}")

if __name__ == "__main__":
    test_new_route()
