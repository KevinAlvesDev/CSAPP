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
    except Exception:
        return False


def get_all_cs_users_for_gamification(context=None):
    """Busca todos os usuários com nome e e-mail para o filtro de gamificação."""
    ctx = resolve_context(context)
    result = query_db(
        """
        SELECT pu.usuario, pu.nome, pu.cargo
        FROM perfil_usuario pu
        LEFT JOIN perfil_usuario_contexto puc ON pu.usuario = puc.usuario AND puc.contexto = %s
        WHERE COALESCE(puc.perfil_acesso, pu.perfil_acesso) IS NOT NULL
            AND COALESCE(puc.perfil_acesso, pu.perfil_acesso) != ''
        ORDER BY pu.nome
        """,
        (ctx,),
    )
    return result if result is not None else []
