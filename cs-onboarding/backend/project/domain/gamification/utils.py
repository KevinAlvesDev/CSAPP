"""
Módulo de Utilidades de Gamificação
Funções auxiliares de cache e listagem de usuários.
Princípio SOLID: Single Responsibility
"""
from ...db import query_db


def clear_gamification_cache():
    """Limpa o cache de regras de gamificação."""
    from ...core.extensions import gamification_rules_cache

    try:
        gamification_rules_cache.clear()
        return True
    except Exception:
        return False


def get_all_cs_users_for_gamification():
    """Busca todos os usuários com nome e e-mail para o filtro de gamificação."""
    result = query_db(
        "SELECT usuario, nome, cargo FROM perfil_usuario WHERE perfil_acesso IS NOT NULL AND perfil_acesso != '' ORDER BY nome",
        ()
    )
    return result if result is not None else []
