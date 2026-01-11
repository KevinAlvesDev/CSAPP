
import os
import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv

load_dotenv(override=True)

def test_search_post():
    url = os.getenv('JIRA_URL')
    user = os.getenv('JIRA_USER')
    token = os.getenv('JIRA_API_TOKEN')

    if url.endswith('/'): url = url[:-1]
    
    # Endpoint padrao POST
    api_url = f"{url}/rest/api/3/search"
    
    print(f"Tentando POST em {api_url}...")
    
    payload = {
        "jql": "order by created DESC",
        "maxResults": 1,
        "fields": ["summary", "status"]
    }
    
    try:
        resp = requests.post(
            api_url, 
            json=payload, 
            auth=HTTPBasicAuth(user, token),
            headers={"Content-Type": "application/json", "Accept": "application/json"}
        )
        print(f"Status POST: {resp.status_code}")
        if resp.status_code == 200:
            print("Sucesso via POST!")
            print(resp.json())
        else:
            print(f"Erro POST: {resp.text}")

    except Exception as e:
        print(f"Erro: {e}")

if __name__ == "__main__":
    test_search_post()
