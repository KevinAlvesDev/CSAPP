
import os
import sys
from dotenv import load_dotenv
import requests
from requests.auth import HTTPBasicAuth

# Carrega var de ambiente
load_dotenv(override=True)

def test_jira():
    url = os.getenv('JIRA_URL')
    user = os.getenv('JIRA_USER')
    token = os.getenv('JIRA_API_TOKEN')

    print(f"URL Configurada: {url}")
    print(f"Usuario: {user}")
    
    if not token:
        print("ERRO: Token nao encontrado.")
        return

    # Remover barra final se existir
    if url.endswith('/'):
        url = url[:-1]

    # Teste 1: Endpoint de Autenticacao (Myself) - API v3
    myself_url = f"{url}/rest/api/3/myself"
    print(f"\n--- Testando Autenticacao (v3) ---")
    print(f"GET {myself_url}")
    
    try:
        resp = requests.get(myself_url, auth=HTTPBasicAuth(user, token), timeout=10)
        print(f"Status Code: {resp.status_code}")
        
        if resp.status_code == 200:
            data = resp.json()
            print(f"Sucesso! Conectado como: {data.get('displayName')} ({data.get('emailAddress')})")
        else:
            print(f"Falha na autenticacao: {resp.text}")
            
            # Se falhar v3, tenta v2
            print(f"\n--- Tentando Autenticacao (v2) ---")
            myself_url_v2 = f"{url}/rest/api/2/myself"
            resp2 = requests.get(myself_url_v2, auth=HTTPBasicAuth(user, token), timeout=10)
            print(f"Status Code v2: {resp2.status_code}")
            if resp2.status_code == 200:
                 print("Sucesso na v2!")
            else:
                 print(f"Falha tambem na v2: {resp2.text}")

    except Exception as e:
        print(f"Excecao ao conectar: {e}")

    # Teste 2: Busca (Search)
    print(f"\n--- Testando Busca (JQL) ---")
    search_url = f"{url}/rest/api/3/search"
    try:
        resp = requests.get(
            search_url, 
            auth=HTTPBasicAuth(user, token),
            params={'jql': 'order by created DESC', 'maxResults': 1}, 
            timeout=10
        )
        print(f"Status Busca v3: {resp.status_code}")
        if resp.status_code == 200:
            print("Busca v3 OK.")
        elif resp.status_code == 404 or resp.status_code == 410:
             print("v3 nao encontrada, tentando v2...")
             search_url_v2 = f"{url}/rest/api/2/search"
             resp2 = requests.get(
                search_url_v2, 
                auth=HTTPBasicAuth(user, token),
                params={'jql': 'order by created DESC', 'maxResults': 1}, 
                timeout=10
            )
             print(f"Status Busca v2: {resp2.status_code}")
             if resp2.status_code == 200:
                 print("Busca v2 OK.")
             else:
                 print(f"Erro busca v2: {resp2.text}")
        else:
            print(f"Erro busca v3: {resp.text}")

    except Exception as e:
        print(f"Excecao na busca: {e}")

if __name__ == "__main__":
    test_jira()
