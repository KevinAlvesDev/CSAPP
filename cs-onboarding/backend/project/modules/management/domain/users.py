"""
Módulo de Usuários do Gerenciamento
Listagem e consulta de usuários.
Princípio SOLID: Single Responsibility
"""

from flask import current_app
from flask import g

from ....common.context_navigation import normalize_context
from ....db import query_db


def _resolve_context(context=None):
    current_ctx = None
    try:
        current_ctx = getattr(g, "modulo_atual", None)
    except Exception:
        current_ctx = None
    ctx = normalize_context(context) or normalize_context(current_ctx)
    return ctx or "onboarding"


def listar_usuarios_service(context=None):
    """Retorna lista de todos os usuários com seus perfis, ordenados alfabeticamente."""
    ctx = _resolve_context(context)
    return (
        query_db(
            """
            SELECT
                pu.usuario as usuario,
                pu.nome,
                COALESCE(puc.perfil_acesso, pu.perfil_acesso) AS perfil_acesso
            FROM perfil_usuario pu
            LEFT JOIN perfil_usuario_contexto puc
                ON puc.usuario = pu.usuario AND puc.contexto = %s
            ORDER BY COALESCE(LOWER(pu.nome), LOWER(pu.usuario))
            """,
            (ctx,),
        )
        or []
    )


def verificar_usuario_existe(usuario_email):
    """Verifica se um usuário existe no sistema."""
    return query_db("SELECT 1 FROM perfil_usuario WHERE usuario = %s", (usuario_email,), one=True) is not None


def obter_perfil_usuario(usuario_email, context=None):
    """Obtém o perfil completo de um usuário."""
    ctx = _resolve_context(context)
    return query_db(
        """
        SELECT
            COALESCE(puc.perfil_acesso, pu.perfil_acesso) AS perfil_acesso,
            pu.foto_url
        FROM perfil_usuario pu
        LEFT JOIN perfil_usuario_contexto puc
            ON puc.usuario = pu.usuario AND puc.contexto = %s
        WHERE pu.usuario = %s
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
            pu.usuario,
            pu.nome,
            COALESCE(puc.perfil_acesso, pu.perfil_acesso) AS perfil_acesso
        FROM perfil_usuario pu
        LEFT JOIN perfil_usuario_contexto puc
            ON puc.usuario = pu.usuario AND puc.contexto = %s
        WHERE COALESCE(puc.perfil_acesso, pu.perfil_acesso) IS NOT NULL
            AND COALESCE(puc.perfil_acesso, pu.perfil_acesso) != ''
        ORDER BY pu.nome
        """,
        (ctx,),
    )
    result = result if result is not None else []

    if cache:
        cache.set(cache_key, result, timeout=600)

    return result
