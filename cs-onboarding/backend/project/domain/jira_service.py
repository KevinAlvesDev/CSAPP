import os

import requests
from requests.auth import HTTPBasicAuth

from ..config.logging_config import get_logger

logger = get_logger("jira_integration")


def get_jira_credentials():
    """
    Retrieves Jira credentials from environment variables.
    """
    url = os.getenv("JIRA_URL")
    user = os.getenv("JIRA_USER")
    token = os.getenv("JIRA_API_TOKEN")

    # Remove trailing slash from URL if present
    if url and url.endswith("/"):
        url = url[:-1]

    return url, user, token


def search_issues_by_context(implantacao_data, max_results=50, extra_keys=None):
    """
    Searches Jira issues based on implantation data using the new Jira Cloud v3 API.
    Refactored to ensure 'extra_keys' are always returned, even if they would be excluded by pagination in a combined query.
    """
    url, user, token = get_jira_credentials()

    if not all([url, user, token]):
        logger.warning("Credenciais do Jira (JIRA_URL, JIRA_USER, JIRA_API_TOKEN) não configuradas.")
        return {"error": "Jira não configurado", "issues": []}

    # Ensure URL formatting
    if url.endswith("/"):
        url = url[:-1]

    api_endpoint = f"{url}/rest/api/3/search/jql"
    auth = HTTPBasicAuth(user, token)
    headers = {"Content-Type": "application/json", "Accept": "application/json"}

    found_issues_map = {}  # Key -> Issue Data

    # 1. Fetch Extra Keys (Strategic Priority)
    if extra_keys and isinstance(extra_keys, list) and len(extra_keys) > 0:
        safe_keys = [k.strip() for k in extra_keys if k.strip()]
        if safe_keys:
            keys_str = ",".join(safe_keys)
            jql_keys = f"key in ({keys_str}) ORDER BY created DESC"
            logger.info(f"DEBUG: Fetching extra keys JQL: {jql_keys}")

            try:
                payload = {
                    "jql": jql_keys,
                    "maxResults": len(safe_keys),
                    "fields": [
                        "summary",
                        "status",
                        "created",
                        "updated",
                        "priority",
                        "issuetype",
                        "reporter",
                        "assignee",
                    ],
                }
                response = requests.post(api_endpoint, json=payload, auth=auth, headers=headers, timeout=15)
                if response.status_code == 200:
                    data = response.json()
                    for issue in data.get("issues", []):
                        found_issues_map[issue.get("key")] = issue
            except Exception as e:
                logger.error(f"Erro ao buscar extra keys: {e}")

    # 2. Fetch Company Context
    company_name = implantacao_data.get("nome_empresa", "")
    if company_name:
        safe_company_name = company_name.replace('"', '\\"')
        jql_context = f'cf[10046] ~ "{safe_company_name}"'

        # Exclude already found keys to avoid duplicates in this batch (optional, but cleaner)
        if found_issues_map:
            keys_to_exclude = ",".join(found_issues_map.keys())
            jql_context += f" AND key not in ({keys_to_exclude})"

        jql_context += " ORDER BY created DESC"

        logger.info(f"DEBUG: Fetching context JQL: {jql_context}")

        try:
            payload = {
                "jql": jql_context,
                "maxResults": max_results,
                "fields": ["summary", "status", "created", "updated", "priority", "issuetype", "reporter", "assignee"],
            }
            response = requests.post(api_endpoint, json=payload, auth=auth, headers=headers, timeout=15)

            if response.status_code == 200:
                data = response.json()
                for issue in data.get("issues", []):
                    found_issues_map[issue.get("key")] = issue
            elif response.status_code == 400:
                logger.warning(f"Erro JQL Contexto: {response.text}")
                # Não falha tudo, apenas retorna o que já temos localmente (extra keys)

        except Exception as e:
            logger.error(f"Erro ao buscar contexto da empresa: {e}")

    # 3. Process Result
    final_issues = []
    # Normalizar chaves para uppercase para is_linked check
    extra_keys_set = {str(k).strip().upper() for k in extra_keys} if extra_keys else set()

    # Sort distinct values by created date descending?
    # Converting map values to list
    all_raw_issues = list(found_issues_map.values())

    # Sort in Python (created is ISO string, so string sort works for ISO8601)
    all_raw_issues.sort(key=lambda x: x.get("fields", {}).get("created", ""), reverse=True)

    for issue in all_raw_issues:
        fields = issue.get("fields", {})
        key = issue.get("key")
        key_upper = str(key).upper() if key else ""

        final_issues.append(
            {
                "key": key,
                "summary": fields.get("summary"),
                "status": fields.get("status", {}).get("name"),
                "status_color": fields.get("status", {}).get("statusCategory", {}).get("colorName", "blue-gray"),
                "created": fields.get("created"),
                "updated": fields.get("updated"),
                "link": f"{url}/browse/{key}",
                "priority": fields.get("priority", {}).get("name", "N/A"),
                "priority_icon": fields.get("priority", {}).get("iconUrl"),
                "type": fields.get("issuetype", {}).get("name"),
                "type_icon": fields.get("issuetype", {}).get("iconUrl"),
                "reporter": fields.get("reporter", {}).get("displayName", "Desconhecido"),
                "is_linked": key_upper in extra_keys_set,
            }
        )

    return {"issues": final_issues}


# Mapeamentos Estáticos (IDs descobertos via inspect_jira)
PROJECT_IDS = {
    "M1": "11149",
    "MJ": "11160",
    "M5": "11154",
    "GC": "11151",
    "PAY": "10132",
    "TW": "11157",
    "IN": "10029",
    "APPS": "11153",
    "E2": "10125",
}


def create_jira_issue(implantacao_data, issue_data, files=None):
    """
    Cria um ticket no Jira (API v3) e opcionalmente anexa arquivos.
    """
    url, user, token = get_jira_credentials()
    if not all([url, user, token]):
        return {"error": "Jira não configurado"}

    # Preparar Dados
    project_key = issue_data.get("project")  # Vem como M1, MJ etc.
    project_id = PROJECT_IDS.get(project_key)

    if not project_id:
        return {"error": f"Projeto inválido ou não mapeado: {project_key}"}

    summary = issue_data.get("summary")
    description_text = issue_data.get("description", "")
    issue_type_id = issue_data.get("issuetype", "10021")  # Default Bug
    priority_id = issue_data.get("priority", "3")  # Default Normal

    # Custom Fields
    ticket_origin = issue_data.get("custom_origin", "")
    contact_name = issue_data.get("custom_contact", "")
    enotas_link = issue_data.get("custom_enotas_link", "")

    company_name = implantacao_data.get("nome_empresa", "")

    # Construção da Descrição Rica (ADF) - API v3 requirement
    full_description_text = description_text or ""

    if contact_name:
        full_description_text += f"\n\nContato: {contact_name}"
    if enotas_link:
        full_description_text += f"\nLink E-notas: {enotas_link}"

    # Helper simple parágrafo
    adf_description = {
        "type": "doc",
        "version": 1,
        "content": [
            {
                "type": "paragraph",
                "content": [
                    {
                        "type": "text",
                        "text": full_description_text if full_description_text.strip() else "Sem descrição.",
                    }
                ],
            }
        ],
    }

    # Payload
    fields = {
        "project": {"id": project_id},
        "summary": summary,
        "issuetype": {"id": issue_type_id},
        "description": adf_description,
        "priority": {"id": priority_id},
        # Campos Customizados Descobertos
        "customfield_10046": company_name,  # Nome Empresa
    }

    # Tratamento condicional de campos
    if ticket_origin:
        # Erro "matriz de cadeias de caracteres" indica que espera um array de strings
        fields["customfield_11567"] = [ticket_origin]

    payload = {"fields": fields}

    try:
        api_endpoint = f"{url}/rest/api/3/issue"
        logger.info(f"Criando issue no Jira: {summary} (Proj: {project_key})")

        response = requests.post(
            api_endpoint,
            json=payload,
            auth=HTTPBasicAuth(user, token),
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            timeout=20,
        )

        if response.status_code == 201:
            data = response.json()
            key = data.get("key")
            issue_id = data.get("id")

            # --- PROCESSAMENTO DE ARQUIVOS ---
            if files:
                attach_results = []
                for file_obj in files:
                    # file_obj deve ser um objeto FileStorage do Werkzeug ou tupla (nome, bytes, type)
                    # Aqui esperamos FileStorage ou similar que tenha .filename, .read(), .content_type
                    try:
                        res_att = attach_file_to_issue(key, file_obj)
                        attach_results.append(res_att)
                    except Exception as e_att:
                        logger.error(f"Erro anexando arquivo {file_obj}: {e_att}")

            return {"success": True, "key": key, "id": issue_id, "link": f"{url}/browse/{key}"}
        else:
            logger.error(f"Erro Jira Create Body: {response.text}")
            return {"error": f"Falha ao criar ticket: {response.status_code}"}

    except Exception as e:
        logger.error(f"Exceção create_jira_issue: {e}")
        return {"error": str(e)}


def attach_file_to_issue(issue_key, file_storage):
    """
    Anexa um arquivo a uma issue existente.
    """
    url, user, token = get_jira_credentials()
    if not all([url, user, token]):
        return {"error": "Configuração Jira inválida"}

    # Ensure URL formatting
    if url.endswith("/"):
        url = url[:-1]

    endpoint = f"{url}/rest/api/3/issue/{issue_key}/attachments"

    # FileStorage (Flask) behaves like a file, but requests needs (filename, fileobj, content_type)
    # file_storage.stream.seek(0) might be needed if already read, but usually it's at 0.

    try:
        files = {"file": (file_storage.filename, file_storage.stream, file_storage.content_type)}

        # Jira requer header 'X-Atlassian-Token: no-check' para uploads
        headers = {"X-Atlassian-Token": "no-check", "Accept": "application/json"}

        response = requests.post(endpoint, files=files, auth=HTTPBasicAuth(user, token), headers=headers, timeout=30)

        if response.status_code == 200:
            return {"success": True, "data": response.json()}
        else:
            logger.warning(f"Erro ao anexar arquivo no Jira {issue_key}: {response.status_code} - {response.text}")
            return {"success": False, "error": response.text}

    except Exception as e:
        logger.error(f"Exceção attach_file_to_issue: {e}")
        return {"success": False, "error": str(e)}


def get_issue_details(issue_key):
    """
    Busca detalhes de um ticket específico pela chave (ex: M1-1234).
    """
    url, user, token = get_jira_credentials()
    if not all([url, user, token]):
        return {"error": "Jira não configurado"}

    # Ensure URL formatting
    if url.endswith("/"):
        url = url[:-1]

    endpoint = f"{url}/rest/api/3/issue/{issue_key}"

    try:
        response = requests.get(
            endpoint, auth=HTTPBasicAuth(user, token), headers={"Accept": "application/json"}, timeout=10
        )

        if response.status_code == 404:
            return {"error": f"Ticket {issue_key} não encontrado no Jira."}

        if response.status_code == 401:
            return {"error": "Erro de autenticação no Jira."}

        response.raise_for_status()

        data = response.json()
        fields = data.get("fields", {})

        issue_obj = {
            "key": data.get("key"),
            "summary": fields.get("summary"),
            "status": fields.get("status", {}).get("name"),
            "status_color": fields.get("status", {}).get("statusCategory", {}).get("colorName", "blue-gray"),
            "created": fields.get("created"),
            "updated": fields.get("updated"),
            "link": f"{url}/browse/{data.get('key')}",
            "priority": fields.get("priority", {}).get("name", "N/A"),
            "priority_icon": fields.get("priority", {}).get("iconUrl"),
            "type": fields.get("issuetype", {}).get("name"),
            "type_icon": fields.get("issuetype", {}).get("iconUrl"),
            "reporter": fields.get("reporter", {}).get("displayName", "Desconhecido"),
        }
        return {"issue": issue_obj}

    except Exception as e:
        logger.error(f"Erro ao buscar issue {issue_key}: {e}")
        return {"error": f"Erro ao buscar ticket: {e!s}"}


# ==========================================
# PERSISTÊNCIA DE VÍNCULOS (Database Layer)
# ==========================================


def _get_app_config():
    from flask import current_app

    return current_app.config


def _get_db_conn():
    from ..database import get_db_connection

    return get_db_connection()


def ensure_jira_links_table(cur, db_type):
    """
    Garante que a tabela implantacao_jira_links existe.
    (Auto-migration para ambientes sem migration system)
    """
    try:
        if db_type == "sqlite":
            cur.execute("SELECT 1 FROM implantacao_jira_links LIMIT 1")
        else:
            cur.execute("SELECT 1 FROM implantacao_jira_links LIMIT 1")
    except Exception:
        # Tabela não existe, vamos criar
        if hasattr(cur.connection, "rollback"):
            cur.connection.rollback()

        logger.warning(f"Tabela implantacao_jira_links não encontrada ({db_type}). Criando...")

        if db_type == "sqlite":
            cur.execute("""
                CREATE TABLE IF NOT EXISTS implantacao_jira_links (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    implantacao_id INTEGER NOT NULL,
                    jira_key VARCHAR(20) NOT NULL,
                    data_vinculo DATETIME DEFAULT CURRENT_TIMESTAMP,
                    vinculado_por TEXT,
                    FOREIGN KEY (implantacao_id) REFERENCES implantacoes(id) ON DELETE CASCADE,
                    UNIQUE(implantacao_id, jira_key)
                )
            """)
        else:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS implantacao_jira_links (
                    id SERIAL PRIMARY KEY,
                    implantacao_id INTEGER NOT NULL REFERENCES implantacoes(id) ON DELETE CASCADE,
                    jira_key VARCHAR(20) NOT NULL,
                    data_vinculo TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    vinculado_por TEXT,
                    UNIQUE(implantacao_id, jira_key)
                );
            """)
        cur.connection.commit()


def save_jira_link(implantacao_id, jira_key, user_email):
    """
    Salva o vínculo entre uma implantação e um ticket Jira.
    """
    conn, db_type = _get_db_conn()
    if not conn:
        raise Exception("Falha de conexão com banco de dados")

    try:
        cur = conn.cursor()
        ensure_jira_links_table(cur, db_type)

        use_sqlite = _get_app_config().get("USE_SQLITE_LOCALLY")

        logger.info(f"DB: Salvando vínculo Link Impl={implantacao_id} Key={jira_key}")

        if use_sqlite:
            try:
                cur.execute(
                    "INSERT INTO implantacao_jira_links (implantacao_id, jira_key, vinculado_por) VALUES (?, ?, ?)",
                    (implantacao_id, jira_key, user_email),
                )
                conn.commit()
            except Exception as e_sql:
                if "UNIQUE" in str(e_sql).upper():
                    logger.info("DB: Vínculo já existe (UNIQUE).")
                else:
                    raise e_sql
        else:
            # Postgres: ON CONFLICT DO NOTHING
            cur.execute(
                "INSERT INTO implantacao_jira_links (implantacao_id, jira_key, vinculado_por) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
                (implantacao_id, jira_key, user_email),
            )
            conn.commit()

    except Exception as e:
        logger.error(f"Erro critical salvar link Jira: {e}")
        if conn:
            conn.rollback()
        raise e
    finally:
        conn.close()


def remove_jira_link(implantacao_id, jira_key):
    """
    Remove o vínculo entre implantação e ticket Jira.
    Retorna True se removido ou se já não existia.
    """
    conn, _db_type = _get_db_conn()
    if not conn:
        raise Exception("Falha de conexão com banco de dados")

    try:
        cur = conn.cursor()
        use_sqlite = _get_app_config().get("USE_SQLITE_LOCALLY")

        if use_sqlite:
            cur.execute(
                "DELETE FROM implantacao_jira_links WHERE implantacao_id = ? AND jira_key = ?",
                (implantacao_id, jira_key),
            )
        else:
            cur.execute(
                "DELETE FROM implantacao_jira_links WHERE implantacao_id = %s AND jira_key = %s",
                (implantacao_id, jira_key),
            )

        conn.commit()
        return True  # Always success (idempotent)

    except Exception as e:
        logger.error(f"Erro ao remover link Jira: {e}")
        if conn:
            conn.rollback()
        raise e
    finally:
        conn.close()


def get_linked_jira_keys(implantacao_id):
    """
    Retorna lista de chaves Jira vinculadas manualmente a uma implantação.
    """
    conn, db_type = _get_db_conn()
    if not conn:
        return []

    try:
        cur = conn.cursor()
        ensure_jira_links_table(cur, db_type)

        use_sqlite = _get_app_config().get("USE_SQLITE_LOCALLY")

        if use_sqlite:
            cur.execute("SELECT jira_key FROM implantacao_jira_links WHERE implantacao_id = ?", (implantacao_id,))
        else:
            cur.execute("SELECT jira_key FROM implantacao_jira_links WHERE implantacao_id = %s", (implantacao_id,))

        rows = cur.fetchall()
        return [r[0] for r in rows]

    except Exception as e:
        logger.warning(f"Erro ao buscar links Jira (DB): {e}")
        return []
    finally:
        conn.close()
