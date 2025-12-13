from sqlite3 import IntegrityError as Sqlite3IntegrityError
import secrets
from werkzeug.security import generate_password_hash
from psycopg2 import IntegrityError as Psycopg2IntegrityError
from flask import current_app

from ..config.logging_config import auth_logger
from ..constants import ADMIN_EMAIL, PERFIL_ADMIN
from ..db import execute_db, query_db

def sync_user_profile_service(user_email, user_name, auth0_user_id):
    """Garante que o usuário do Auth0 exista no DB local e defina o perfil inicial."""
    try:
        usuario_existente = query_db("SELECT usuario FROM usuarios WHERE usuario = %s", (user_email,), one=True)
        perfil_existente = query_db("SELECT nome FROM perfil_usuario WHERE usuario = %s", (user_email,), one=True)

        perfil_acesso_final = None
        if user_email == ADMIN_EMAIL:
            perfil_acesso_final = PERFIL_ADMIN
            auth_logger.info(f'Admin user [service] {user_email} detected')

        if not usuario_existente:
            try:
                senha_placeholder = generate_password_hash(secrets.token_urlsafe(32))
                execute_db(
                    "INSERT INTO usuarios (usuario, senha) VALUES (%s, %s)",
                    (user_email, senha_placeholder)
                )
                auth_logger.info(f'User account created [service]: {user_email}')
            except (Psycopg2IntegrityError, Sqlite3IntegrityError):
                raise ValueError("Usuário já cadastrado")
            except Exception as db_error:
                raise db_error

        if not perfil_existente:
            execute_db(
                "INSERT INTO perfil_usuario (usuario, nome, perfil_acesso) VALUES (%s, %s, %s)",
                (user_email, user_name, perfil_acesso_final)
            )
            auth_logger.info(f'User profile created [service]: {user_email} with role {perfil_acesso_final}')
        elif user_email == ADMIN_EMAIL:
            perfil_acesso_atual = query_db("SELECT perfil_acesso FROM perfil_usuario WHERE usuario = %s", (user_email,), one=True)
            if perfil_acesso_atual.get('perfil_acesso') != PERFIL_ADMIN:
                execute_db("UPDATE perfil_usuario SET perfil_acesso = %s WHERE usuario = %s", (PERFIL_ADMIN, user_email))
                auth_logger.info(f'Admin role enforced [service] for user: {user_email}')

    except ValueError as ve:
        raise ve
    except Exception as db_error:
        auth_logger.error(f'Critical error syncing user profile {user_email}: {str(db_error)}')
        raise db_error

def get_user_profile_service(user_email):
    return query_db("SELECT * FROM perfil_usuario WHERE usuario = %s", (user_email,), one=True)

def update_user_role_service(user_email, role):
    execute_db("UPDATE perfil_usuario SET perfil_acesso = %s WHERE usuario = %s", (role, user_email))

def find_cs_user_external_service(email):
    if not current_app.config.get('EXTERNAL_DB_URL'):
        return None
    from ..database.external_db import find_cs_user_by_email
    return find_cs_user_by_email(email)


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
    execute_db(
        "UPDATE perfil_usuario SET nome = %s, cargo = %s, foto_url = %s WHERE usuario = %s",
        (nome, cargo, foto_url, usuario_email)
    )
    return True

