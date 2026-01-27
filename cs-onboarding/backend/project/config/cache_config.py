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

    redis_url = os.environ.get("REDIS_URL")

    if redis_url:
        cache_config = {
            "CACHE_TYPE": "redis",
            "CACHE_REDIS_URL": redis_url,
            "CACHE_DEFAULT_TIMEOUT": 300,
            "CACHE_KEY_PREFIX": "csapp_",
        }
        app.logger.info("Cache initialized with Redis backend")
    else:
        cache_config = {"CACHE_TYPE": "SimpleCache", "CACHE_DEFAULT_TIMEOUT": 300, "CACHE_THRESHOLD": 500}
        app.logger.info("Cache initialized with SimpleCache backend (development)")

    cache = Cache(app, config=cache_config)

    return cache


def clear_user_cache(user_email):
    """
    Limpa o cache relacionado a um usuário específico.
    Útil quando dados do usuário são atualizados.
    
    IMPORTANTE: Também limpa o cache de gestores que podem estar
    filtrando por este usuário no dashboard.
    """
    if cache:
        cache.delete(f"user_profile_{user_email}")
        cache.delete(f"user_implantacoes_{user_email}")
        
        # Limpar variações de dashboard_data (com e sem contexto)
        contexts = ["onboarding", "grandes_contas", "ongoing", "all"]
        pages = [None, 1, 2, 3, 4, 5]  # Páginas comuns
        per_pages = [None, 25, 50, 100]  # Tamanhos de página comuns
        
        for ctx in contexts:
            for page in pages:
                for per_page in per_pages:
                    # Cache do próprio usuário (sem filtro de CS)
                    cache.delete(f"dashboard_data_{user_email}_all_{ctx}_p{page}_pp{per_page}")
        
        # Limpar cache de gestores que podem estar filtrando por este CS
        clear_filtered_dashboard_cache(user_email)


def clear_filtered_dashboard_cache(cs_email):
    """
    Limpa o cache de dashboard de gestores que estão filtrando por um CS específico.
    
    Quando os dados de um CS são alterados, precisamos invalidar não apenas
    o cache dele, mas também o cache de qualquer gestor que esteja
    visualizando o dashboard filtrado por aquele CS.
    
    Args:
        cs_email: Email do CS cujos dados foram alterados
    """
    if not cache:
        return
    
    # Buscar todos os gestores (Admin, Gerente, Coordenador)
    try:
        from ..db import query_db
        from ..constants import PERFIS_COM_GESTAO
        
        # Query para buscar todos os gestores
        placeholders = ",".join(["%s"] * len(PERFIS_COM_GESTAO))
        managers = query_db(
            f"SELECT usuario FROM perfil_usuario WHERE perfil_acesso IN ({placeholders})",
            tuple(PERFIS_COM_GESTAO)
        )
        
        if not managers:
            return
        
        # Contextos e paginações a limpar
        contexts = ["onboarding", "grandes_contas", "ongoing", "all"]
        pages = [None, 1, 2, 3, 4, 5]
        per_pages = [None, 25, 50, 100]
        
        # Para cada gestor, limpar o cache do dashboard filtrado por este CS
        for manager in managers:
            manager_email = manager.get("usuario") if isinstance(manager, dict) else manager[0]
            if not manager_email:
                continue
                
            for ctx in contexts:
                for page in pages:
                    for per_page in per_pages:
                        # Cache key: dashboard_data_{gestor}_{cs_filtrado}_{contexto}_p{page}_pp{per_page}
                        cache.delete(f"dashboard_data_{manager_email}_{cs_email}_{ctx}_p{page}_pp{per_page}")
                        
    except Exception as e:
        # Log mas não falha - cache é otimização, não pode quebrar a aplicação
        import logging
        logging.getLogger(__name__).warning(f"Erro ao limpar cache de gestores: {e}")


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


def clear_all_cache():
    """
    Limpa todo o cache.
    Útil para manutenção ou após mudanças estruturais.
    """
    if cache:
        cache.clear()
        return True
    return False
