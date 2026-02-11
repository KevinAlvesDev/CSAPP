"""
Service Registry — Registra todos os services no Container.

Centraliza o registro de services no ServiceContainer durante o startup.
Evita imports espalhados pelo `create_app` e facilita testes unitários.

Uso:
    # Em create_app:
    from .core.service_registry import register_all_services
    register_all_services(app, container)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from flask import Flask

    from .container import ServiceContainer

logger = logging.getLogger("app")


def register_all_services(app: Flask, container: ServiceContainer) -> None:
    """
    Registra todos os services no ServiceContainer.

    Args:
        app: Instância do Flask
        container: ServiceContainer já inicializado
    """
    _register_core_services(app, container)
    _register_domain_services(app, container)
    _register_infrastructure_services(app, container)

    registered = container.registered_services()
    logger.info(f"🔧 ServiceContainer: {len(registered)} serviços registrados")
    logger.debug(f"🔧 Serviços: {', '.join(registered)}")


def _register_core_services(app: Flask, container: ServiceContainer) -> None:
    """Registra serviços de infraestrutura core."""

    # Config
    container.register("config", app.config)

    # Database
    container.register_factory("db", _get_db_factory)

    # Cache Manager
    cache_mgr = getattr(app, "cache_manager", None)
    if cache_mgr:
        container.register("cache_manager", cache_mgr)

    # Event Bus
    try:
        from .events import EventBus

        event_bus = EventBus()
        container.register("event_bus", event_bus)
        logger.debug("EventBus registrado no container")
    except Exception as e:
        logger.warning(f"EventBus não registrado: {e}")

    # Query Profiler
    try:
        from ..common.query_profiler import QueryProfiler

        container.register("query_profiler", QueryProfiler)
        logger.debug("QueryProfiler registrado no container")
    except Exception as e:
        logger.warning(f"QueryProfiler não registrado: {e}")


def _register_domain_services(app: Flask, container: ServiceContainer) -> None:
    """Registra services de domínio como factories (lazy-load)."""

    # Dashboard Service
    container.register_factory(
        "dashboard_service",
        lambda: _import("backend.project.domain.dashboard_service"),
    )

    # Config Service
    container.register_factory(
        "config_service",
        lambda: _import("backend.project.domain.config_service"),
    )

    # Implantacao Service
    container.register_factory(
        "implantacao_service",
        lambda: _import("backend.project.domain.implantacao_service"),
    )

    # Checklist Service
    container.register_factory(
        "checklist_service",
        lambda: _import("backend.project.domain.checklist_service"),
    )

    # Notification Service
    container.register_factory(
        "notification_service",
        lambda: _import("backend.project.domain.notification_service"),
    )

    # Perfis Service
    container.register_factory(
        "perfis_service",
        lambda: _import("backend.project.domain.perfis_service"),
    )

    # Timeline Service
    container.register_factory(
        "timeline_service",
        lambda: _import("backend.project.domain.timeline_service"),
    )

    # Audit Service
    container.register_factory(
        "audit_service",
        lambda: _import("backend.project.domain.audit_service"),
    )


def _register_infrastructure_services(app: Flask, container: ServiceContainer) -> None:
    """Registra services de infraestrutura."""

    # DataLoader factory (cada resolução cria um novo)
    container.register_factory(
        "dataloader_factory",
        lambda: _get_dataloader_factory(),
    )


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────


def _get_db_factory() -> dict:
    """Factory para funções de banco de dados."""
    from ..db import execute_db, query_db

    return {"query_db": query_db, "execute_db": execute_db}


def _get_dataloader_factory() -> dict:
    """Factory que retorna construtores de DataLoaders."""
    from ..common.dataloader import (
        ChecklistDataLoader,
        ComentariosDataLoader,
        ImplantacaoDataLoader,
    )

    return {
        "checklist": ChecklistDataLoader,
        "comentarios": ComentariosDataLoader,
        "implantacao": ImplantacaoDataLoader,
    }


def _import(module_path: str) -> Any:
    """Importa um módulo dinamicamente."""
    import importlib

    return importlib.import_module(module_path)

