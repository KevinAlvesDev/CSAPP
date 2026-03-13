import logging
logger = logging.getLogger(__name__)
"""
Configuração de cache para a aplicação.
Usa Flask-Caching com backend configurável (Redis em produção, Simple em desenvolvimento).
"""

import os

from flask_caching import Cache

cache = None


def _dashboard_version_key(user_email: str) -> str:
    return f"dashboard_version_{user_email}"


def get_dashboard_cache_version(user_email: str) -> int:
    if not cache:
        return 0
    try:
        version = cache.get(_dashboard_version_key(user_email))
        return int(version) if version is not None else 0
    except Exception as exc:
        logger.exception("Unhandled exception", exc_info=True)
        return 0


def bump_dashboard_cache_version(user_email: str) -> int:
    if not cache:
        return 0
    try:
        version = get_dashboard_cache_version(user_email) + 1
        cache.set(_dashboard_version_key(user_email), version, timeout=60 * 60 * 24 * 7)
        return version
    except Exception as exc:
        logger.exception("Unhandled exception", exc_info=True)
        return 0


def init_cache(app):
    """
    Inicializa o sistema de cache.

    Em produção (com REDIS_URL): usa Redis
    Em desenvolvimento (sem REDIS_URL): usa SimpleCache (memória)
    """
    global cache

    redis_url = os.environ.get("REDIS_URL")

    if redis_url:
        cache_config = {
            "CACHE_TYPE": "flask_caching.backends.rediscache.RedisCache",
            "CACHE_REDIS_URL": redis_url,
            "CACHE_DEFAULT_TIMEOUT": 30,  # 30 segundos - cache curto para dados frescos
            "CACHE_KEY_PREFIX": "csapp_",
        }
        app.logger.info("Cache initialized with Redis backend")
    else:
        cache_config = {
            "CACHE_TYPE": "flask_caching.backends.simplecache.SimpleCache",
            "CACHE_DEFAULT_TIMEOUT": 30,
            "CACHE_THRESHOLD": 500,
        }
        app.logger.info("Cache initialized with SimpleCache backend (development)")

    cache = Cache(app, config=cache_config)

    return cache


def clear_user_cache(user_email):
    """
    Limpa o cache relacionado a um usuário específico.
    Útil quando dados do usuário são atualizados.
    """
    if cache:
        cache.delete(f"user_profile_{user_email}")  # Cache de perfil
        cache.delete(f"user_implantacoes_{user_email}")
        bump_dashboard_cache_version(user_email)
        cache.delete(f"dashboard_data_{user_email}")  # legado


def clear_implantacao_cache(implantacao_id):
    """
    Limpa o cache relacionado a uma implantação específica.
    Útil quando a implantação é atualizada.
    """
    if cache:
        cache.delete(f"implantacao_details_{implantacao_id}")
        cache.delete(f"implantacao_tasks_{implantacao_id}")
        cache.delete(f"implantacao_timeline_{implantacao_id}")
        cache.delete(f"progresso_impl_{implantacao_id}")


def clear_dashboard_cache():
    """
    Limpa todo o cache de dashboard.
    Chamado quando há ações que afetam a exibição do dashboard (novos comentários, etc).
    Isso garante que todos os usuários vejam os dados atualizados.
    """
    if cache:
        # Como não temos acesso a todas as chaves no SimpleCache,
        # a solução mais robusta é limpar todo o cache
        # Em produção com Redis, poderíamos usar SCAN para deletar apenas chaves de dashboard
        cache.clear()


def clear_all_cache():
    """
    Limpa todo o cache.
    Útil para manutenção ou após mudanças estruturais.
    """
    if cache:
        cache.clear()
        return True
    return False