import secrets
from datetime import datetime
from sqlite3 import IntegrityError as Sqlite3IntegrityError

from flask import current_app
from psycopg2 import IntegrityError as Psycopg2IntegrityError
from werkzeug.security import generate_password_hash

from ....config.logging_config import auth_logger
from ....constants import MASTER_ADMIN_EMAIL, PERFIL_ADMIN, PERFIL_IMPLANTADOR
from ....db import execute_db, query_db


def sync_user_profile_service(user_email, user_name, auth0_user_id):
    """Garante que o usuário do Auth0 exista no DB local e defina o perfil inicial."""
    try:
        usuario_existente = query_db("SELECT usuario FROM usuarios WHERE usuario = %s", (user_email,), one=True)
        perfil_existente = query_db("SELECT nome FROM perfil_usuario WHERE usuario = %s", (user_email,), one=True)

        # Definir perfil padrão
        # ADMIN_EMAIL recebe PERFIL_ADMIN, todos os outros recebem PERFIL_IMPLANTADOR
        if user_email == MASTER_ADMIN_EMAIL:
            auth_logger.info(f"Admin user [service] {user_email} detected")
        else:
            perfil_acesso_final = PERFIL_IMPLANTADOR
            auth_logger.info(f"New user [service] {user_email} will receive default role: {PERFIL_IMPLANTADOR}")

        if not usuario_existente:
            try:
                senha_placeholder = generate_password_hash(secrets.token_urlsafe(32))
                execute_db("INSERT INTO usuarios (usuario, senha) VALUES (%s, %s)", (user_email, senha_placeholder))
                auth_logger.info(f"User account created [service]: {user_email}")
            except (Psycopg2IntegrityError, Sqlite3IntegrityError):
                raise ValueError("Usuário já cadastrado")
            except Exception as db_error:
                raise db_error

        if not perfil_existente:
            execute_db(
                "INSERT INTO perfil_usuario (usuario, nome, perfil_acesso) VALUES (%s, %s, %s)",
                (user_email, user_name, perfil_acesso_final),
            )
            auth_logger.info(f"User profile created [service]: {user_email} with role {perfil_acesso_final}")
        elif user_email == MASTER_ADMIN_EMAIL:
            perfil_acesso_atual = query_db(
                "SELECT perfil_acesso FROM perfil_usuario WHERE usuario = %s", (user_email,), one=True
            )
            if perfil_acesso_atual.get("perfil_acesso") != PERFIL_ADMIN:
                execute_db(
                    "UPDATE perfil_usuario SET perfil_acesso = %s WHERE usuario = %s", (PERFIL_ADMIN, user_email)
                )
                auth_logger.info(f"Admin role enforced [service] for user: {user_email}")

    except ValueError as ve:
        raise ve
    except Exception as db_error:
        auth_logger.error(f"Critical error syncing user profile {user_email}: {db_error!s}")
        raise db_error


def get_user_profile_service(user_email):
    return query_db("SELECT * FROM perfil_usuario WHERE usuario = %s", (user_email,), one=True)


def update_user_role_service(user_email, role):
    execute_db("UPDATE perfil_usuario SET perfil_acesso = %s WHERE usuario = %s", (role, user_email))
    # Invalidar cache do perfil
    from ....config.cache_config import clear_user_cache

    clear_user_cache(user_email)


def find_cs_user_external_service(email):
    if not current_app.config.get("EXTERNAL_DB_URL"):
        return None
    from ....database.external_db import find_cs_user_by_email

    return find_cs_user_by_email(email)


def marcar_sucesso_check_externo_service(email):
    """Atualiza o timestamp do último check externo bem-sucedido."""
    try:
        execute_db("UPDATE perfil_usuario SET ultimo_check_externo = %s WHERE usuario = %s", (datetime.now(), email))
    except Exception as e:
        auth_logger.warning(f"Falha ao atualizar timestamp de check externo para {email}: {e}")


def buscar_ultimo_check_externo_service(email):
    """Retorna o timestamp do último check externo bem-sucedido."""
    try:
        row = query_db("SELECT ultimo_check_externo FROM perfil_usuario WHERE usuario = %s", (email,), one=True)
        return row.get("ultimo_check_externo") if row else None
    except Exception:
        return None


def atualizar_dados_perfil_service(usuario_email, nome, cargo, foto_url):
    """
    Atualiza os dados do perfil do usuário (nome, cargo, foto).

    Args:
        usuario_email: Email do usuário
        nome: Nome completo
        cargo: Cargo/função
        foto_url: URL da foto de perfil

    Returns:
        bool: True se sucesso
    """
    # Obter nome anterior para sincronizar responsáveis
    try:
        row = query_db("SELECT nome FROM perfil_usuario WHERE usuario = %s", (usuario_email,), one=True)
        old_nome = (row or {}).get("nome")
    except Exception:
        old_nome = None

    execute_db(
        "UPDATE perfil_usuario SET nome = %s, cargo = %s, foto_url = %s WHERE usuario = %s",
        (nome, cargo, foto_url, usuario_email),
    )

    # Invalidar cache do perfil
    from ....config.cache_config import clear_user_cache

    clear_user_cache(usuario_email)

    # Sincronizar responsáveis nos itens do checklist:
    # - Se responsável for exatamente o nome antigo, substituir pelo novo nome
    # - Se responsável for o email do usuário, substituir pelo novo nome
    try:
        if nome and isinstance(nome, str):
            if old_nome and old_nome.strip():
                execute_db(
                    "UPDATE checklist_items SET responsavel = %s WHERE responsavel = %s",
                    (nome.strip(), old_nome.strip()),
                )
            execute_db(
                "UPDATE checklist_items SET responsavel = %s WHERE responsavel = %s", (nome.strip(), usuario_email)
            )
    except Exception:
        # Sincronização é best-effort; falhas não bloqueiam atualização de perfil
        pass
    return True
