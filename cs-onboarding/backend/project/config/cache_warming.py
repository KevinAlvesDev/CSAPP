"""
Cache Warming — Pré-carrega dados frequentes no startup.

Ao invés de esperar o primeiro request para popular o cache,
carregamos dados estáticos/semi-estáticos durante o boot da app.

Isso elimina cold-start lento para o primeiro usuário.

Recursos pré-carregados:
- Tags do sistema (mudam raramente)
- Status de implantação (mudam raramente)
- Níveis de atendimento
- Tipos de evento
- Motivos de parada/cancelamento
- Regras de gamificação
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from flask import Flask

    from .cache_manager import CacheManager

logger = logging.getLogger("app")


# ──────────────────────────────────────────────
# Definições de recursos que devem ser aquecidos
# ──────────────────────────────────────────────

WARM_RESOURCES: list[dict[str, Any]] = [
    {
        "name": "tags_sistema",
        "resource_type": "configuracoes",
        "cache_key": {"tipo": "ambos"},
        "fetch_fn": "_fetch_tags",
    },
    {
        "name": "status_implantacao",
        "resource_type": "configuracoes",
        "cache_key": {"subtipo": "status"},
        "fetch_fn": "_fetch_status_implantacao",
    },
    {
        "name": "niveis_atendimento",
        "resource_type": "configuracoes",
        "cache_key": {"subtipo": "niveis"},
        "fetch_fn": "_fetch_niveis_atendimento",
    },
    {
        "name": "tipos_evento",
        "resource_type": "configuracoes",
        "cache_key": {"subtipo": "tipos_evento"},
        "fetch_fn": "_fetch_tipos_evento",
    },
    {
        "name": "motivos_parada",
        "resource_type": "configuracoes",
        "cache_key": {"subtipo": "motivos_parada"},
        "fetch_fn": "_fetch_motivos_parada",
    },
    {
        "name": "motivos_cancelamento",
        "resource_type": "configuracoes",
        "cache_key": {"subtipo": "motivos_cancelamento"},
        "fetch_fn": "_fetch_motivos_cancelamento",
    },
]


# ──────────────────────────────────────────────
# Funções de fetch
# ──────────────────────────────────────────────


def _fetch_tags() -> list[dict]:
    from ..modules.config.application.config_service import listar_tags

    return listar_tags(tipo="ambos")


def _fetch_status_implantacao() -> list[dict]:
    from ..modules.config.application.config_service import listar_status_implantacao

    return listar_status_implantacao()


def _fetch_niveis_atendimento() -> list[dict]:
    from ..modules.config.application.config_service import listar_niveis_atendimento

    return listar_niveis_atendimento()


def _fetch_tipos_evento() -> list[dict]:
    from ..modules.config.application.config_service import listar_tipos_evento

    return listar_tipos_evento()


def _fetch_motivos_parada() -> list[dict]:
    from ..modules.config.application.config_service import listar_motivos_parada

    return listar_motivos_parada()


def _fetch_motivos_cancelamento() -> list[dict]:
    from ..modules.config.application.config_service import listar_motivos_cancelamento

    return listar_motivos_cancelamento()


# Mapa de nomes de funções para funções reais
_FETCH_MAP = {
    "_fetch_tags": _fetch_tags,
    "_fetch_status_implantacao": _fetch_status_implantacao,
    "_fetch_niveis_atendimento": _fetch_niveis_atendimento,
    "_fetch_tipos_evento": _fetch_tipos_evento,
    "_fetch_motivos_parada": _fetch_motivos_parada,
    "_fetch_motivos_cancelamento": _fetch_motivos_cancelamento,
}


# ──────────────────────────────────────────────
# Warming
# ──────────────────────────────────────────────


def warm_cache(app: Flask, cache_manager: CacheManager | None = None) -> dict[str, Any]:
    """
    Pré-carrega dados frequentes no cache durante o startup.

    Args:
        app: Instância do Flask
        cache_manager: Instância do CacheManager (ou pega do app)

    Returns:
        Resumo do warming com estatísticas
    """
    if cache_manager is None:
        cache_manager = getattr(app, "cache_manager", None)

    if cache_manager is None:
        logger.warning("Cache Manager não disponível — warming ignorado")
        return {"status": "skipped", "reason": "no_cache_manager"}

    start_time = time.perf_counter()
    results: dict[str, str] = {}
    errors: list[str] = []

    for resource in WARM_RESOURCES:
        name = resource["name"]
        resource_type = resource["resource_type"]
        cache_key = resource["cache_key"]
        fetch_fn_name = resource["fetch_fn"]

        try:
            fetch_fn = _FETCH_MAP.get(fetch_fn_name)
            if not fetch_fn:
                errors.append(f"{name}: fetch function '{fetch_fn_name}' not found")
                continue

            data = fetch_fn()
            if data:
                cache_manager.set(resource_type, data, **cache_key)
                results[name] = f"OK ({len(data)} items)"
            else:
                results[name] = "EMPTY"

        except Exception as e:
            results[name] = f"ERROR: {e}"
            errors.append(f"{name}: {e}")
            logger.warning(f"Cache warming falhou para {name}: {e}")

    duration_ms = (time.perf_counter() - start_time) * 1000
    succeeded = sum(1 for v in results.values() if v.startswith("OK"))

    summary = {
        "status": "completed",
        "duration_ms": round(duration_ms, 1),
        "total": len(WARM_RESOURCES),
        "succeeded": succeeded,
        "failed": len(errors),
        "details": results,
    }

    if errors:
        summary["errors"] = errors
        logger.warning(f"♨️  Cache Warming: {succeeded}/{len(WARM_RESOURCES)} OK em {duration_ms:.0f}ms ({len(errors)} erros)")
    else:
        logger.info(f"♨️  Cache Warming: {succeeded}/{len(WARM_RESOURCES)} recursos pré-carregados em {duration_ms:.0f}ms")

    return summary


def refresh_config_cache(cache_manager: CacheManager | None = None) -> dict[str, str]:
    """
    Recarrega configurações no cache (chamável via API ou scheduled task).

    Returns:
        Mapa de recurso → status
    """
    if cache_manager is None:
        try:
            from flask import current_app

            cache_manager = getattr(current_app, "cache_manager", None)
        except RuntimeError:
            return {"error": "No app context"}

    if not cache_manager:
        return {"error": "No cache manager"}

    results: dict[str, str] = {}

    for resource in WARM_RESOURCES:
        name = resource["name"]
        resource_type = resource["resource_type"]
        cache_key = resource["cache_key"]
        fetch_fn_name = resource["fetch_fn"]

        try:
            fetch_fn = _FETCH_MAP.get(fetch_fn_name)
            if fetch_fn:
                data = fetch_fn()
                if data:
                    cache_manager.set(resource_type, data, **cache_key)
                    results[name] = "refreshed"
                else:
                    results[name] = "empty"
        except Exception as e:
            results[name] = f"error: {e}"

    return results
