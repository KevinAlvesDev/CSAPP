
import os
import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv

# Carrega ambiente
load_dotenv(override=True)

def inspect_jira_v3():
    # Caminho do .env manual caso nao carregue automatico
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    env_path = os.path.join(project_root, '.env')
    load_dotenv(env_path, override=True)
    
    url = os.getenv('JIRA_URL')
    user = os.getenv('JIRA_USER')
    token = os.getenv('JIRA_API_TOKEN')

    if not all([url, user, token]):
        print("XXX Credenciais ausentes no .env")
        return

    if url.endswith('/'): url = url[:-1]
    
    auth = HTTPBasicAuth(user, token)
    headers = {"Accept": "application/json"}
    
    print(f"Inspecionando Jira: {url}\n")
    
    # 1. Projetos
    print("--- PROJETOS ---")
    try:
        resp = requests.get(f"{url}/rest/api/3/project", auth=auth, headers=headers)
        if resp.status_code == 200:
            projects = resp.json()
            print(f"Total: {len(projects)}")
            for p in projects:
                print(f" - [{p['key']}] {p['name']} (ID: {p['id']})")
        else:
            print(f"Erro ao buscar projetos: {resp.status_code}")
    except Exception as e:
        print(f"Erro projetos: {e}")

    # 2. Tipos de Issue
    print("\n--- TIPOS DE ISSUE (Globais) ---")
    try:
        resp = requests.get(f"{url}/rest/api/3/issuetype", auth=auth, headers=headers)
        if resp.status_code == 200:
            types = resp.json()
            for t in types:
                if not t.get('subtask'): 
                    print(f" - {t['name']} (ID: {t['id']})")
        else:
            print(f"Erro ao buscar tipos: {resp.status_code}")
    except Exception as e:
        print(f"Erro tipos: {e}")

    # 3. Prioridades
    print("\n--- PRIORIDADES ---")
    try:
        resp = requests.get(f"{url}/rest/api/3/priority", auth=auth, headers=headers)
        if resp.status_code == 200:
            priorities = resp.json()
            for p in priorities:
                print(f" - {p['name']} (ID: {p['id']})")
        else:
            print(f"Erro ao buscar prioridades: {resp.status_code}")
    except Exception as e:
        print(f"Erro prioridades: {e}")

    # 4. Campos Customizados
    print("\n--- CAMPOS (Procurando Keywords relevantes) ---")
    keywords = ['sla', 'origem', 'nota', 'e-nota', 'cliente', 'empresa', 'contact', 'contato', 'sprint']
    try:
        resp = requests.get(f"{url}/rest/api/3/field", auth=auth, headers=headers)
        if resp.status_code == 200:
            fields = resp.json()
            found_count = 0
            for f in fields:
                name_lower = f['name'].lower()
                if any(k in name_lower for k in keywords):
                    print(f" - [{f['id']}] {f['name']} (Custom: {f['custom']})")
                    found_count += 1
            if found_count == 0:
                print("Nenhum campo especifico encontrado.")
        else:
            print(f"Erro ao buscar campos: {resp.status_code}")
    except Exception as e:
        print(f"Erro campos: {e}")

if __name__ == "__main__":
    inspect_jira_v3()
