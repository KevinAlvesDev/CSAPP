"""
Cache aprimorado com TTL configurável por recurso.

Permite definir TTLs diferentes para cada tipo de recurso,
cache warming no startup, e invalidação granular por tags.

Uso:
    from backend.project.config.cache_config_v2 import CacheManager

    cache_mgr = CacheManager()
    cache_mgr.init_app(app)

    # Buscar com cache
    data = cache_mgr.get_or_set("dashboard", key, fetch_fn, user_email=email)

    # Invalidar
    cache_mgr.invalidate_resource("implantacao", implantacao_id=123)
"""

from __future__ import annotations

import functools
import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger("app")


# ──────────────────────────────────────────────
# Configuração de TTL por recurso
# ──────────────────────────────────────────────
CACHE_TTL_CONFIG: dict[str, dict[str, Any]] = {
    "dashboard": {
        "ttl": 300,  # 5 minutos
        "description": "Dados do dashboard principal",
        "warm_on_startup": False,
    },
    "implantacao_list": {
        "ttl": 120,  # 2 minutos
        "description": "Lista de implantações",
        "warm_on_startup": False,
    },
    "implantacao_details": {
        "ttl": 60,  # 1 minuto
        "description": "Detalhes de uma implantação",
        "warm_on_startup": False,
    },
    "checklist_tree": {
        "ttl": 60,  # 1 minuto
        "description": "Árvore de checklist",
        "warm_on_startup": False,
    },
    "user_profile": {
        "ttl": 600,  # 10 minutos
        "description": "Perfil do usuário",
        "warm_on_startup": False,
    },
    "configuracoes": {
        "ttl": 3600,  # 1 hora
        "description": "Configurações do sistema (tags, perfis, etc.)",
        "warm_on_startup": True,
    },
    "analytics": {
        "ttl": 900,  # 15 minutos
        "description": "Dados de analytics/relatórios",
        "warm_on_startup": False,
    },
    "gamification": {
        "ttl": 1800,  # 30 minutos
        "description": "Regras e pontuações de gamificação",
        "warm_on_startup": True,
    },
}


class CacheManager:
    """
    Gerenciador de cache com TTL configurável por recurso.

    Features:
    - TTL diferente por tipo de recurso
    - Invalidação granular (por recurso + ID)
    - Cache warming (pré-carregamento no startup)
    - Métricas de hit/miss
    """

    def __init__(self):
        self._cache = None
        self._app = None
        self._hits = 0
        self._misses = 0
        self._invalidations = 0

    def init_app(self, app, cache_instance=None) -> None:
        """Inicializa com instância Flask e cache existente."""
        self._app = app
        self._cache = cache_instance

        # Registrar no app para acesso global
        app.cache_manager = self

    @property
    def cache(self):
        """Retorna a instância de cache (lazy)."""
        if self._cache is None:
            try:
                from .cache_config import cache

                self._cache = cache
            except ImportError:
                logger.warning("Cache não disponível")
        return self._cache

    def _make_key(self, resource_type: str, **kwargs) -> str:
        """Gera chave de cache padronizada."""
        parts = [f"csapp:{resource_type}"]
        for k, v in sorted(kwargs.items()):
            if v is not None:
                parts.append(f"{k}={v}")
        return ":".join(parts)

    def get_ttl(self, resource_type: str) -> int:
        """Retorna o TTL configurado para um recurso."""
        config = CACHE_TTL_CONFIG.get(resource_type, {})
        return config.get("ttl", 60)  # Default: 60 segundos

    def get(self, resource_type: str, **kwargs) -> Any | None:
        """Busca valor do cache."""
        if not self.cache:
            return None

        key = self._make_key(resource_type, **kwargs)
        value = self.cache.get(key)

        if value is not None:
            self._hits += 1
        else:
            self._misses += 1

        return value

    def set(self, resource_type: str, value: Any, **kwargs) -> None:
        """Armazena valor no cache com TTL do recurso."""
        if not self.cache:
            return

        key = self._make_key(resource_type, **kwargs)
        ttl = self.get_ttl(resource_type)
        self.cache.set(key, value, timeout=ttl)

    def get_or_set(
        self,
        resource_type: str,
        fetch_fn: Callable[[], Any],
        **kwargs,
    ) -> Any:
        """
        Busca do cache ou executa fetch_fn e armazena.

        Args:
            resource_type: Tipo de recurso (ex: "dashboard")
            fetch_fn: Função que busca os dados se não estiver em cache
            **kwargs: Parâmetros para a chave de cache

        Returns:
            Dados do cache ou resultado de fetch_fn
        """
        cached = self.get(resource_type, **kwargs)
        if cached is not None:
            return cached

        value = fetch_fn()
        if value is not None:
            self.set(resource_type, value, **kwargs)
        return value

    def invalidate(self, resource_type: str, **kwargs) -> None:
        """Invalida uma chave específica do cache."""
        if not self.cache:
            return

        key = self._make_key(resource_type, **kwargs)
        self.cache.delete(key)
        self._invalidations += 1

    def invalidate_resource(self, resource_type: str, **kwargs) -> None:
        """
        Invalida todas as variações de um recurso.

        Como SimpleCache não suporta SCAN, invalidamos chaves conhecidas.
        Com Redis, poderíamos usar patterns.
        """
        if not self.cache:
            return

        # Invalidar chave específica
        self.invalidate(resource_type, **kwargs)

        # Invalidar chave sem parâmetros (cache geral do recurso)
        self.invalidate(resource_type)

        self._invalidations += 1
        logger.debug(f"Cache invalidado: {resource_type} {kwargs}")

    def invalidate_for_implantacao(self, implantacao_id: int) -> None:
        """Invalida todo cache relacionado a uma implantação."""
        self.invalidate("implantacao_details", implantacao_id=implantacao_id)
        self.invalidate("checklist_tree", implantacao_id=implantacao_id)
        self.invalidate("implantacao_list")
        self.invalidate("dashboard")

    def invalidate_for_user(self, user_email: str) -> None:
        """Invalida todo cache relacionado a um usuário."""
        self.invalidate("user_profile", user_email=user_email)
        self.invalidate("dashboard", user_email=user_email)
        self.invalidate("dashboard")

    def clear_all(self) -> bool:
        """Limpa todo o cache."""
        if not self.cache:
            return False
        self.cache.clear()
        self._invalidations += 1
        logger.info("Cache completo limpo")
        return True

    def get_stats(self) -> dict[str, Any]:
        """Retorna métricas de cache."""
        total = self._hits + self._misses
        hit_rate = (self._hits / total * 100) if total > 0 else 0

        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(hit_rate, 1),
            "invalidations": self._invalidations,
            "total_requests": total,
            "ttl_config": {
                k: {"ttl": v["ttl"], "description": v.get("description", "")} for k, v in CACHE_TTL_CONFIG.items()
            },
        }


def cached_resource(resource_type: str, **cache_kwargs) -> Callable:
    """
    Decorator para cachear o resultado de uma função.

    Exemplo:
        @cached_resource("dashboard", user_email="user@example.com")
        def get_dashboard_data():
            ...
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                from flask import current_app

                cache_mgr = getattr(current_app, "cache_manager", None)
                if cache_mgr:
                    return cache_mgr.get_or_set(
                        resource_type,
                        lambda: func(*args, **kwargs),
                        **cache_kwargs,
                    )
            except Exception:
                pass
            return func(*args, **kwargs)

        return wrapper

    return decorator


# Instância global (inicializada com init_app)
cache_manager = CacheManager()
