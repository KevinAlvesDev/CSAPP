"""
Service Container — Dependency Injection simplificada para Flask.

Implementa um container de serviços que desacopla a lógica de negócio
do contexto Flask (g, session, current_app), facilitando testes unitários.

Diferente de frameworks como Dependency Injector, este é uma solução leve
e pragmática que se integra naturalmente com Flask.

Uso:
    # No startup (create_app):
    from backend.project.core.container import ServiceContainer
    container = ServiceContainer(app)

    # Em routes/blueprints:
    from backend.project.core.container import get_container
    container = get_container()
    implantacao_service = container.implantacao_service

    # Em testes:
    container = ServiceContainer(test_app)
    container.register("db", mock_db)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, TypeVar

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger("app")

T = TypeVar("T")


class ServiceContainer:
    """
    Container de serviços para Dependency Injection.

    Armazena factories e instâncias de serviços, permitindo que
    a lógica de negócio seja testada sem depender do Flask context.

    Suporta:
    - Registro de singletons (uma instância)
    - Registro de factories (nova instância a cada resolução)
    - Override para testes
    """

    def __init__(self, app=None):
        self._singletons: dict[str, Any] = {}
        self._factories: dict[str, Callable] = {}
        self._app = app

        if app:
            self._register_defaults(app)
            # Armazenar no app para acesso global
            app.service_container = self

    def _register_defaults(self, app) -> None:
        """Registra serviços padrão baseados na configuração."""
        # Configuração
        self.register("config", app.config)

        # Database helper
        self.register_factory("db", lambda: self._get_db_functions())

    def _get_db_functions(self) -> dict:
        """Retorna funções de banco de dados."""
        from ..db import execute_db, query_db

        return {"query_db": query_db, "execute_db": execute_db}

    def register(self, name: str, instance: Any) -> None:
        """
        Registra uma instância singleton.

        Args:
            name: Nome do serviço
            instance: Instância do serviço
        """
        self._singletons[name] = instance
        logger.debug(f"Serviço registrado (singleton): {name}")

    def register_factory(self, name: str, factory: Callable[[], Any]) -> None:
        """
        Registra uma factory que cria novas instâncias.

        Args:
            name: Nome do serviço
            factory: Callable que retorna uma nova instância
        """
        self._factories[name] = factory
        logger.debug(f"Serviço registrado (factory): {name}")

    def resolve(self, name: str) -> Any:
        """
        Resolve (obtém) um serviço pelo nome.

        Prioridade: singletons > factories

        Args:
            name: Nome do serviço

        Returns:
            Instância do serviço

        Raises:
            KeyError: Se o serviço não estiver registrado
        """
        if name in self._singletons:
            return self._singletons[name]

        if name in self._factories:
            return self._factories[name]()

        raise KeyError(f"Serviço '{name}' não registrado no container")

    def has(self, name: str) -> bool:
        """Verifica se um serviço está registrado."""
        return name in self._singletons or name in self._factories

    def override(self, name: str, instance: Any) -> None:
        """
        Override para testes — substitui um serviço existente.

        Args:
            name: Nome do serviço
            instance: Mock/stub para substituir
        """
        self._singletons[name] = instance
        # Remover factory se existir (singleton tem prioridade)
        self._factories.pop(name, None)

    def __getattr__(self, name: str) -> Any:
        """Permite acesso por atributo: container.db_service."""
        try:
            return self.resolve(name)
        except KeyError as exc:
            raise AttributeError(f"Serviço '{name}' não encontrado no container") from exc

    def registered_services(self) -> list[str]:
        """Lista todos os serviços registrados."""
        return sorted(set(list(self._singletons.keys()) + list(self._factories.keys())))


def get_container() -> ServiceContainer:
    """
    Obtém o ServiceContainer da aplicação Flask atual.

    Uso em routes:
        container = get_container()
        service = container.implantacao_service
    """
    from flask import current_app

    container = getattr(current_app, "service_container", None)
    if container is None:
        raise RuntimeError(
            "ServiceContainer não inicializado. Certifique-se de chamar ServiceContainer(app) no create_app()."
        )
    return container


def inject_service(service_name: str) -> Callable:
    """
    Decorator que injeta um serviço como argumento da função.

    Exemplo:
        @inject_service("db")
        def minha_funcao(db, ...):
            db.query_db(...)
    """
    import functools

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                container = get_container()
                service = container.resolve(service_name)
                return func(service, *args, **kwargs)
            except (RuntimeError, KeyError):
                # Fallback: executar sem injeção (compatibilidade)
                return func(*args, **kwargs)

        return wrapper

    return decorator
