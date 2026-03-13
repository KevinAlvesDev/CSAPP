import secrets
import logging
logger = logging.getLogger(__name__)

from datetime import datetime, timezone



from psycopg2 import IntegrityError as Psycopg2IntegrityError

from werkzeug.security import generate_password_hash



from ....common.context_profiles import (

    ensure_user_context_profiles,

    get_contextual_profile,

    resolve_context,

    set_user_role_for_all_contexts,

    set_user_role_for_context,

)

from ....config.logging_config import auth_logger

from ....constants import ADMIN_EMAIL, MASTER_ADMIN_EMAIL, PERFIL_ADMIN, PERFIL_IMPLANTADOR, PERFIL_SEM_ACESSO

from ....db import execute_db, query_db

__all__ = [
    "sync_user_profile_service",
    "get_user_profile_service",
    "update_user_role_service",
    "normalize_text",
    "marcar_sucesso_check_externo_service",
    "buscar_ultimo_check_externo_service",
    "atualizar_dados_perfil_service",
]





def sync_user_profile_service(user_email, user_name, external_auth_id):

    """Garante que o usuário autenticado externamente exista no DB local e define o perfil inicial."""

    try:

        usuario_existente = query_db("SELECT usuario FROM usuarios WHERE usuario = %s", (user_email,), one=True)

        perfil_existente = query_db("SELECT nome FROM perfil_usuario WHERE usuario = %s", (user_email,), one=True)



        # Admins explícitos recebem Administrador; demais ficam sem acesso até liberação manual
        if user_email in (ADMIN_EMAIL, MASTER_ADMIN_EMAIL):
            perfil_acesso_final = PERFIL_ADMIN
        else:
            perfil_acesso_final = PERFIL_SEM_ACESSO

        auth_logger.info(f"User {user_email} set to default role: {perfil_acesso_final}")



        if not usuario_existente:

            try:

                senha_placeholder = generate_password_hash(secrets.token_urlsafe(32))

                execute_db("INSERT INTO usuarios (usuario, senha) VALUES (%s, %s) ON CONFLICT (usuario) DO NOTHING", (user_email, senha_placeholder))

                auth_logger.info(f"User account created [service]: {user_email}")

            except Psycopg2IntegrityError:

                raise ValueError("Usuário já cadastrado")

            except Exception as db_error:
                logger.exception("Unhandled exception", exc_info=True)

                raise db_error



        # Garante que existe linha em perfil_usuario (cargo fica nulo — é título profissional, não perfil de acesso)
        execute_db(
            "INSERT INTO perfil_usuario (usuario, nome) VALUES (%s, %s) ON CONFLICT (usuario) DO NOTHING",
            (user_email, user_name or user_email),
        )

        # Atualiza apenas o nome (nunca altera cargo via sync de login)
        execute_db(
            "UPDATE perfil_usuario SET nome = %s WHERE usuario = %s",
            (user_name or user_email, user_email),
        )

        set_user_role_for_all_contexts(user_email, perfil_acesso_final, updated_by="auth_sync_force_admin")

        auth_logger.info(f"User profile enforced [service]: {user_email} with role {perfil_acesso_final} em todos os contextos")



    except ValueError as ve:

        raise ve

    except Exception as db_error:

        auth_logger.error(f"Critical error syncing user profile {user_email}: {db_error!s}")

        raise db_error





def get_user_profile_service(user_email, context=None):

    ctx = resolve_context(context)

    profile = get_contextual_profile(user_email, ctx)

    if profile:

        return profile

    row = query_db(

        """

        SELECT

            u.usuario,

            u.nome,

            u.foto_url,

            u.cargo,

            COALESCE(puc.perfil_acesso, 'Sem Acesso') AS perfil_acesso

        FROM perfil_usuario u

        LEFT JOIN perfil_usuario_contexto puc

            ON puc.usuario = u.usuario AND puc.contexto = %s

        WHERE u.usuario = %s

        """,

        (ctx, user_email),

        one=True,

    )

    if row:

        row["contexto"] = ctx

    return row





def update_user_role_service(user_email, role, context=None):

    ctx = resolve_context(context)

    if context:

        set_user_role_for_context(user_email, role, context=ctx, updated_by="role_update")

    else:

        set_user_role_for_all_contexts(user_email, role, updated_by="role_update")

    # Invalidar cache do perfil

    from ....config.cache_config import clear_user_cache



    clear_user_cache(user_email)





import unicodedata





def normalize_text(text):

    """Remove acentos e converte para minúsculas."""

    if not text:

        return ""

    return unicodedata.normalize("NFKD", text).encode("ASCII", "ignore").decode("utf-8").lower()






def marcar_sucesso_check_externo_service(email):

    """Atualiza o timestamp do último check com o banco OAMD (CustomerSuccess) bem-sucedido."""

    try:

        execute_db("UPDATE perfil_usuario SET ultimo_check_externo = %s WHERE usuario = %s", (datetime.now(timezone.utc), email))

    except Exception as e:

        auth_logger.warning(f"Falha ao atualizar timestamp de check externo para {email}: {e}", exc_info=True)





def buscar_ultimo_check_externo_service(email):

    """Retorna o timestamp do último check externo bem-sucedido."""

    try:

        row = query_db("SELECT ultimo_check_externo FROM perfil_usuario WHERE usuario = %s", (email,), one=True)

        return row.get("ultimo_check_externo") if row else None

    except Exception as exc:

        logger.exception("Unhandled exception", exc_info=True)

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

    except Exception as exc:

        logger.exception("Unhandled exception", exc_info=True)

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

    except Exception as exc:

        logger.exception("Unhandled exception", exc_info=True)

        # Sincronização é best-effort; falhas não bloqueiam atualização de perfil

        pass

    return True
