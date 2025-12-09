"""
Configuração de cache para a aplicação.
Usa Flask-Caching com backend configurável (Redis em produção, Simple em desenvolvimento).
"""

import os

from flask_caching import Cache

cache = None


def init_cache(app):
    """
    Inicializa o sistema de cache.

    Em produção (com REDIS_URL): usa Redis
    Em desenvolvimento (sem REDIS_URL): usa SimpleCache (memória)
    """
    global cache

    redis_url = os.environ.get('REDIS_URL')

    if redis_url:
        cache_config = {
            'CACHE_TYPE': 'redis',
            'CACHE_REDIS_URL': redis_url,
            'CACHE_DEFAULT_TIMEOUT': 300,
            'CACHE_KEY_PREFIX': 'csapp_'
        }
        app.logger.info("Cache initialized with Redis backend")
    else:
        cache_config = {
            'CACHE_TYPE': 'SimpleCache',
            'CACHE_DEFAULT_TIMEOUT': 300,
            'CACHE_THRESHOLD': 500
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
        cache.delete(f'dashboard_data_{user_email}')
        cache.delete(f'dashboard_data_{user_email}_all_pNone_ppNone')
        cache.delete(f'user_profile_{user_email}')
        cache.delete(f'user_implantacoes_{user_email}')


def clear_implantacao_cache(implantacao_id):
    """
    Limpa o cache relacionado a uma implantação específica.
    Útil quando a implantação é atualizada.
    """
    if cache:
        cache.delete(f'implantacao_details_{implantacao_id}')
        cache.delete(f'implantacao_tasks_{implantacao_id}')
        cache.delete(f'implantacao_timeline_{implantacao_id}')
        cache.delete(f'progresso_impl_{implantacao_id}')


def clear_all_cache():
    """
    Limpa todo o cache.
    Útil para manutenção ou após mudanças estruturais.
    """
    if cache:
        cache.clear()
        return True
    return False
