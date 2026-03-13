import logging
from datetime import datetime, timezone
logger = logging.getLogger(__name__)

from flask import current_app, g

from ..constants import PERFIL_SEM_ACESSO
from ..db import db_connection, execute_db, query_db
from .context_navigation import normalize_context

VALID_CONTEXTS = ("onboarding", "grandes_contas", "ongoing")


def resolve_context(context=None):
    current_ctx = None
    try:
        current_ctx = getattr(g, "modulo_atual", None)
    except Exception as exc:
        logger.exception("Unhandled exception", exc_info=True)
        current_ctx = None
    ctx = normalize_context(context) or normalize_context(current_ctx)
    return ctx or "onboarding"


def ensure_context_profile_schema():
    """
    Sem-op: a replicação de perfis por contexto é gerenciada exclusivamente
    pelo seed em database/schema.py (_popular_dados_iniciais_perfis).
    Manter essa função como no-op evita que perfis sejam criados em módulos
    nos quais não deveriam existir (ex: Implantador não existe em 'ongoing').
    """
    pass


def _upsert_user_context_profile(user_email, contexto, perfil_acesso, updated_by="system"):
    now = datetime.now(timezone.utc)
    # Compatibilidade Postgres 9.3: Lógica manual em 2 passos
    existing = query_db(
        "SELECT 1 FROM perfil_usuario_contexto WHERE usuario = %s AND contexto = %s",
        (user_email, contexto),
        one=True
    )
    
    if existing:
        execute_db(
            """
            UPDATE perfil_usuario_contexto 
            SET perfil_acesso = %s, atualizado_em = %s, atualizado_por = %s
            WHERE usuario = %s AND contexto = %s
            """,
            (perfil_acesso, now, updated_by, user_email, contexto),
        )
    else:
        execute_db(
            """
            INSERT INTO perfil_usuario_contexto (usuario, contexto, perfil_acesso, atualizado_em, atualizado_por)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (user_email, contexto, perfil_acesso, now, updated_by),
        )


def set_user_role_for_context(user_email, role, context=None, updated_by="system"):
    ctx = resolve_context(context)
    _upsert_user_context_profile(user_email, ctx, role, updated_by=updated_by)


def set_user_role_for_all_contexts(user_email, role, updated_by="system"):
    for ctx in VALID_CONTEXTS:
        _upsert_user_context_profile(user_email, ctx, role, updated_by=updated_by)


def ensure_user_context_profiles(user_email, role, updated_by="system"):
    for ctx in VALID_CONTEXTS:
        now = datetime.now(timezone.utc)
        execute_db(
            """
            INSERT INTO perfil_usuario_contexto (usuario, contexto, perfil_acesso, atualizado_em, atualizado_por)
            SELECT %s, %s, %s, %s, %s
            WHERE NOT EXISTS (
                SELECT 1 FROM perfil_usuario_contexto 
                WHERE usuario = %s AND contexto = %s
            )
            """,
            (user_email, ctx, role, now, updated_by, user_email, ctx),
        )


def get_contextual_profile(user_email, context=None):
    ctx = resolve_context(context)
    row = query_db(
        """
        SELECT
            u.usuario as usuario,
            u.nome,
            u.foto_url,
            u.cargo,
            puc.perfil_acesso AS perfil_contextual,
            COALESCE(puc.perfil_acesso, 'Sem Acesso') AS perfil_acesso
        FROM perfil_usuario u
        LEFT JOIN perfil_usuario_contexto puc
            ON puc.usuario = u.usuario AND puc.contexto = %s
        WHERE u.usuario = %s
        """,
        (ctx, user_email),
        one=True,
    )
    if not row:
        return None

    # Auto-heal: cria linha contextual se não existir.
    if not row.get("perfil_contextual"):
        _upsert_user_context_profile(
            user_email=user_email,
            contexto=ctx,
            perfil_acesso=PERFIL_SEM_ACESSO,
            updated_by="autoheal",
        )

    row.pop("perfil_contextual", None)
    row["contexto"] = ctx
    return row