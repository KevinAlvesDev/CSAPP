"""
Event Bus — Sistema de eventos de domínio.

Implementa um Event Bus leve e in-process para desacoplamento de módulos.
Permite que ações em um módulo (ex: "implantação iniciada") disparem
reações em outros módulos (ex: gamificação, notificações) sem acoplamento direto.

Fase futura: Substituir por Redis Streams ou RabbitMQ para escalabilidade.

Uso:
    from backend.project.core.events import event_bus, DomainEvent

    # Definir evento
    class ImplantacaoIniciada(DomainEvent):
        def __init__(self, implantacao_id: int, usuario_cs: str):
            super().__init__()
            self.implantacao_id = implantacao_id
            self.usuario_cs = usuario_cs

    # Registrar handler
    @event_bus.on(ImplantacaoIniciada)
    def handle_implantacao_iniciada(event: ImplantacaoIniciada):
        print(f"Implantação {event.implantacao_id} iniciada por {event.usuario_cs}")

    # Emitir evento
    event_bus.emit(ImplantacaoIniciada(
        implantacao_id=42,
        usuario_cs="admin@admin.com"
    ))
"""

from __future__ import annotations

import logging
import time
import traceback
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, TypeVar

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger("app")

T = TypeVar("T", bound="DomainEvent")


@dataclass
class DomainEvent:
    """
    Classe base para eventos de domínio.

    Todos os eventos devem herdar desta classe.
    """

    timestamp: float = field(default_factory=time.time, init=False)
    event_id: str = field(default_factory=lambda: f"{time.time_ns()}", init=False)

    @property
    def event_name(self) -> str:
        return self.__class__.__name__


# ──────────────────────────────────────────────
# Eventos de Domínio — Implantação
# ──────────────────────────────────────────────


@dataclass
class ImplantacaoIniciada(DomainEvent):
    """Emitido quando uma implantação é iniciada."""

    implantacao_id: int = 0
    usuario_cs: str = ""
    nome_empresa: str = ""


@dataclass
class ImplantacaoFinalizada(DomainEvent):
    """Emitido quando uma implantação é finalizada."""

    implantacao_id: int = 0
    usuario_cs: str = ""
    nome_empresa: str = ""
    progresso_final: float = 0.0


@dataclass
class ImplantacaoCriada(DomainEvent):
    """Emitido quando uma nova implantação é criada."""

    implantacao_id: int = 0
    usuario_cs: str = ""
    nome_empresa: str = ""


@dataclass
class ImplantacaoTransferida(DomainEvent):
    """Emitido quando uma implantação é transferida para outro CS."""

    implantacao_id: int = 0
    de_usuario: str = ""
    para_usuario: str = ""


# ──────────────────────────────────────────────
# Eventos de Domínio — Checklist
# ──────────────────────────────────────────────


@dataclass
class ChecklistItemConcluido(DomainEvent):
    """Emitido quando um item do checklist é marcado como concluído."""

    item_id: int = 0
    implantacao_id: int = 0
    usuario: str = ""
    progresso_atual: float = 0.0


@dataclass
class ChecklistComentarioAdicionado(DomainEvent):
    """Emitido quando um comentário é adicionado a um item."""

    item_id: int = 0
    implantacao_id: int = 0
    autor: str = ""
    tag: str = ""


# ──────────────────────────────────────────────
# Eventos de Domínio — Planos de Sucesso
# ──────────────────────────────────────────────


@dataclass
class PlanoAtribuido(DomainEvent):
    """Emitido quando um plano de sucesso é atribuído a uma implantação."""

    implantacao_id: int = 0
    plano_id: int = 0
    usuario: str = ""


@dataclass
class PlanoRemovido(DomainEvent):
    """Emitido quando um plano de sucesso é removido."""

    implantacao_id: int = 0
    plano_id: int = 0
    usuario: str = ""


# ──────────────────────────────────────────────
# Eventos de Domínio — Usuários
# ──────────────────────────────────────────────


@dataclass
class UsuarioLogado(DomainEvent):
    """Emitido quando um usuário faz login."""

    email: str = ""
    provider: str = ""  # auth0, google, dev


@dataclass
class PerfilAtualizado(DomainEvent):
    """Emitido quando o perfil de um usuário é atualizado."""

    email: str = ""
    campo_alterado: str = ""


# ──────────────────────────────────────────────
# Event Bus
# ──────────────────────────────────────────────


class EventBus:
    """
    Event Bus in-process para comunicação entre módulos.

    Features:
    - Registro de handlers por tipo de evento
    - Execução síncrona (in-process)
    - Logging automático de eventos
    - Error handling (handlers falhando não afetam o fluxo principal)
    - Histórico de eventos recentes (para debugging)
    """

    def __init__(self):
        self._handlers: dict[type, list[Callable]] = {}
        self._history: list[DomainEvent] = []
        self._max_history: int = 500
        self._enabled: bool = True

    def on(self, event_type: type[T]) -> Callable:
        """
        Decorator para registrar um handler de evento.

        Exemplo:
            @event_bus.on(ImplantacaoIniciada)
            def handle_implantacao_iniciada(event):
                ...
        """

        def decorator(func: Callable[[T], Any]) -> Callable[[T], Any]:
            self.register(event_type, func)
            return func

        return decorator

    def register(self, event_type: type[DomainEvent], handler: Callable) -> None:
        """Registra um handler para um tipo de evento."""
        self._handlers.setdefault(event_type, []).append(handler)
        logger.debug(f"Event handler registrado: {event_type.__name__} → {handler.__name__}")

    def emit(self, event: DomainEvent) -> None:
        """
        Emite um evento, executando todos os handlers registrados.

        Handlers são executados sincronamente. Erros em handlers
        são logados mas NÃO propagados (não afetam o fluxo principal).
        """
        if not self._enabled:
            return

        event_name = event.event_name
        handlers = self._handlers.get(type(event), [])

        # Armazenar no histórico
        self._history.append(event)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history :]

        if not handlers:
            logger.debug(f"📢 Evento emitido sem handlers: {event_name}")
            return

        logger.info(f"📢 Evento emitido: {event_name} → {len(handlers)} handler(s)")

        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"❌ Erro no handler {handler.__name__} para {event_name}: {e}\n{traceback.format_exc()}")

    def emit_after_commit(self, event: DomainEvent) -> None:
        """
        Agenda um evento para ser emitido após o commit do DB.

        Em Flask, isso pode ser implementado com after_request ou signals.
        Por enquanto, emite imediatamente (placeholder para implementação futura).
        """
        # TODO: Implementar deferred emit com Flask signals
        self.emit(event)

    def get_handlers(self, event_type: type) -> list[Callable]:
        """Retorna handlers registrados para um tipo de evento."""
        return self._handlers.get(event_type, [])

    def get_history(self, event_type: type | None = None, limit: int = 50) -> list[dict]:
        """
        Retorna histórico de eventos recentes.

        Args:
            event_type: Filtrar por tipo (None = todos)
            limit: Número máximo de eventos

        Returns:
            Lista de dicionários com informações dos eventos
        """
        events = self._history
        if event_type:
            events = [e for e in events if isinstance(e, event_type)]

        events = events[-limit:]

        return [
            {
                "event_id": e.event_id,
                "event_name": e.event_name,
                "timestamp": e.timestamp,
                "data": {k: v for k, v in e.__dict__.items() if k not in ("timestamp", "event_id")},
            }
            for e in events
        ]

    def clear_handlers(self) -> None:
        """Remove todos os handlers (útil para testes)."""
        self._handlers.clear()

    def clear_history(self) -> None:
        """Limpa o histórico de eventos."""
        self._history.clear()

    @property
    def stats(self) -> dict[str, Any]:
        """Estatísticas do Event Bus."""
        return {
            "total_events_emitted": len(self._history),
            "registered_event_types": len(self._handlers),
            "handlers_count": sum(len(h) for h in self._handlers.values()),
            "enabled": self._enabled,
            "event_types": [
                {
                    "type": et.__name__,
                    "handlers": len(handlers),
                }
                for et, handlers in self._handlers.items()
            ],
        }

    def enable(self) -> None:
        """Habilita o Event Bus."""
        self._enabled = True

    def disable(self) -> None:
        """Desabilita o Event Bus (útil para testes ou manutenção)."""
        self._enabled = False


# ──────────────────────────────────────────────
# Instância global
# ──────────────────────────────────────────────
event_bus = EventBus()
