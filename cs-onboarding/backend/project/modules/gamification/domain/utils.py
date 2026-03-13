import logging
logger = logging.getLogger(__name__)
"""
Módulo de Utilidades de Gamificação
Funções auxiliares de cache e listagem de usuários.
Princípio SOLID: Single Responsibility
"""

from ....common.context_profiles import resolve_context
from ....db import query_db


def clear_gamification_cache():
    """Limpa o cache de regras de gamificação."""
    from ....core.extensions import gamification_rules_cache

    try:
        gamification_rules_cache.clear()
        return True
    except Exception as exc:
        logger.exception("Unhandled exception", exc_info=True)
        return False


def get_all_cs_users_for_gamification(context=None):
    """Busca todos os usuários com nome e e-mail para o filtro de gamificação."""
    ctx = resolve_context(context)
    result = query_db(
        """
        SELECT u.usuario AS usuario, u.nome, u.cargo
        FROM perfil_usuario u
        LEFT JOIN perfil_usuario_contexto puc ON puc.usuario = u.usuario AND puc.contexto = %s
        WHERE COALESCE(puc.perfil_acesso, 'Sem Acesso') IS NOT NULL
            AND COALESCE(puc.perfil_acesso, 'Sem Acesso') != ''
        ORDER BY u.nome
        """,
        (ctx,),
    )
    return result if result is not None else []