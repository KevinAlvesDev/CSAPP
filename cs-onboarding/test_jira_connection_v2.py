
import os
import sys
from dotenv import load_dotenv

# Força o carregamento do .env atual
load_dotenv(override=True)

# Adiciona o diretório do backend ao path para garantir importações corretas se necessário,
# mas aqui vamos tentar usar um script standalone primeiro para isolar o problema.
# sys.path.append(os.path.join(os.getcwd(), 'backend'))

import requests
from requests.auth import HTTPBasicAuth

def test_jira():
    url = os.getenv('JIRA_URL')
    user = os.getenv('JIRA_USER')
    token = os.getenv('JIRA_API_TOKEN')

    print(f"URL: {url}")
    print(f"User: {user}")
    print(f"Token: {'*' * 5}{token[-5:] if token else 'None'}")

    if not all([url, user, token]):
        print("❌ Credenciais ausentes.")
        return

    try:
        # Tenta uma busca simples
        jql = 'order by created DESC'
        api_url = f"{url}/rest/api/3/search"
        
        print(f"Conectando a {api_url}...")
        
        response = requests.get(
            api_url,
            auth=HTTPBasicAuth(user, token),
            params={'jql': jql, 'maxResults': 1},
            headers={'Accept': 'application/json'},
            timeout=15
        )

        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Conexão BEM SUCEDIDA!")
            data = response.json()
            print(f"Total Issues Found: {data.get('total')}")
            if data.get('issues'):
                print(f"Exemplo: {data['issues'][0]['key']} - {data['issues'][0]['fields']['summary']}")
        else:
            print(f"❌ Falha: {response.text}")

    except Exception as e:
        print(f"❌ Erro de exceção: {e}")

if __name__ == "__main__":
    test_jira()
