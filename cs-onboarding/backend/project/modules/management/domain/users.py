import logging
logger = logging.getLogger(__name__)
"""
Módulo de Usuários do Gerenciamento
Listagem e consulta de usuários.
Princípio SOLID: Single Responsibility
"""

from flask import current_app, g

from ....common.context_navigation import normalize_context
from ....db import query_db


def _resolve_context(context=None):
    current_ctx = None
    try:
        current_ctx = getattr(g, "modulo_atual", None)
    except Exception as exc:
        logger.exception("Unhandled exception", exc_info=True)
        current_ctx = None
    ctx = normalize_context(context) or normalize_context(current_ctx)
    return ctx or "onboarding"


def listar_usuarios_service(context=None, page=1, per_page=20):
    """Retorna lista paginada de usuários com seus perfis, ordenados alfabeticamente."""
    ctx = _resolve_context(context)
    offset = (page - 1) * per_page

    # Busca o total de usuários para cálculo de páginas (ISOLADO POR CONTEXTO)
    count_res = query_db(
        """
        SELECT COUNT(*) as total
        FROM perfil_usuario u
        JOIN perfil_usuario_contexto puc
            ON puc.usuario = u.usuario AND puc.contexto = %s
        """,
        (ctx,),
        one=True,
    )
    total = count_res["total"] if count_res else 0
    pages = (total + per_page - 1) // per_page

    users = (
        query_db(
            """
            SELECT
                u.usuario as usuario,
                u.nome,
                COALESCE(puc.perfil_acesso, 'Sem Acesso') AS perfil_acesso
            FROM perfil_usuario u
            JOIN perfil_usuario_contexto puc
                ON puc.usuario = u.usuario AND puc.contexto = %s
            ORDER BY COALESCE(LOWER(u.nome), LOWER(u.usuario))
            LIMIT %s OFFSET %s
            """,
            (ctx, per_page, offset),
        )
        or []
    )

    return {
        "items": users,
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": pages
    }


def verificar_usuario_existe(usuario_email):
    """Verifica se um usuário existe no sistema."""
    return query_db("SELECT 1 FROM perfil_usuario WHERE usuario = %s", (usuario_email,), one=True) is not None


def obter_perfil_usuario(usuario_email, context=None):
    """Obtém o perfil completo de um usuário."""
    ctx = _resolve_context(context)
    return query_db(
        """
        SELECT
            COALESCE(puc.perfil_acesso, 'Sem Acesso') AS perfil_acesso,
            u.foto_url
        FROM perfil_usuario u
        LEFT JOIN perfil_usuario_contexto puc
            ON puc.usuario = u.usuario AND puc.contexto = %s
        WHERE u.usuario = %s
        """,
        (ctx, usuario_email),
        one=True,
    )


def obter_perfis_disponiveis():
    """Retorna lista de perfis de acesso disponíveis no sistema."""
    return current_app.config.get("PERFIS_DE_ACESSO", ["Visitante", "Implantador", "Gestor", "Administrador"])


def listar_todos_cs_com_cache(context=None):
    """
    Busca a lista de todos os CS com nome e e-mail para filtros.

    PERFORMANCE: Cacheado por 10 minutos (600s) pois lista de CS muda raramente.

    Returns:
        list: Lista de dicionários com usuario, nome, perfil_acesso
    """
    from ....config.cache_config import cache

    ctx = _resolve_context(context)
    if cache:
        cache_key = f"all_customer_success_{ctx}"
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result

    result = query_db(
        """
        SELECT
            u.usuario as usuario,
            u.nome,
            COALESCE(puc.perfil_acesso, 'Sem Acesso') AS perfil_acesso
        FROM perfil_usuario u
        JOIN perfil_usuario_contexto puc
            ON puc.usuario = u.usuario AND puc.contexto = %s
        WHERE COALESCE(puc.perfil_acesso, 'Sem Acesso') IS NOT NULL
            AND COALESCE(puc.perfil_acesso, 'Sem Acesso') != ''
        ORDER BY u.nome
        """,
        (ctx,),
    )
    result = result if result is not None else []

    if cache:
        cache.set(cache_key, result, timeout=600)

    return result