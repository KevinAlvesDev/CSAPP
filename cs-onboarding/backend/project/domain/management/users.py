"""
Módulo de Usuários do Gerenciamento
Listagem e consulta de usuários.
Princípio SOLID: Single Responsibility
"""

from flask import current_app

from ...db import query_db


def listar_usuarios_service():
    """Retorna lista de todos os usuários com seus perfis, ordenados alfabeticamente."""
    return (
        query_db(
            """SELECT usuario as usuario, nome, perfil_acesso
           FROM perfil_usuario
           ORDER BY COALESCE(LOWER(nome), LOWER(usuario))"""
        )
        or []
    )


def verificar_usuario_existe(usuario_email):
    """Verifica se um usuário existe no sistema."""
    return query_db("SELECT 1 FROM perfil_usuario WHERE usuario = %s", (usuario_email,), one=True) is not None


def obter_perfil_usuario(usuario_email):
    """Obtém o perfil completo de um usuário."""
    return query_db("SELECT perfil_acesso, foto_url FROM perfil_usuario WHERE usuario = %s", (usuario_email,), one=True)


def obter_perfis_disponiveis():
    """Retorna lista de perfis de acesso disponíveis no sistema."""
    return current_app.config.get("PERFIS_DE_ACESSO", ["Visitante", "Implantador", "Gestor", "Administrador"])


def listar_todos_cs_com_cache():
    """
    Busca a lista de todos os CS com nome e e-mail para filtros.

    PERFORMANCE: Cacheado por 10 minutos (600s) pois lista de CS muda raramente.

    Returns:
        list: Lista de dicionários com usuario, nome, perfil_acesso
    """
    from ...config.cache_config import cache

    if cache:
        cache_key = "all_customer_success"
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result

    result = query_db(
        "SELECT usuario, nome, perfil_acesso FROM perfil_usuario WHERE perfil_acesso IS NOT NULL AND perfil_acesso != '' ORDER BY nome",
        (),
    )
    result = result if result is not None else []

    if cache:
        cache.set(cache_key, result, timeout=600)

    return result
