"""
Event Handlers — Reações a eventos de domínio.

Cada handler é uma função pura que reage a um DomainEvent.
São registrados no EventBus durante o startup via `register_event_handlers`.

Princípios:
- Handlers NUNCA podem falhar o fluxo principal (fire-and-forget)
- Cada handler faz UMA coisa (SRP)
- Cross-cutting concerns (audit, cache, notifications) ficam aqui,
  NÃO dentro dos services de domínio

Categorias de handlers:
- Audit: Loga ações relevantes na timeline
- Cache: Invalida caches após mudanças de estado
- Notification: Dispara notificações internas
- Gamification: Atualiza métricas de gamificação
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .events import (
        ChecklistComentarioAdicionado,
        ChecklistItemConcluido,
        ImplantacaoCriada,
        ImplantacaoFinalizada,
        ImplantacaoIniciada,
        ImplantacaoTransferida,
        PlanoAtribuido,
        PlanoRemovido,
        UsuarioLogado,
    )

logger = logging.getLogger("app")


# ──────────────────────────────────────────────
# Audit Handlers — Loga ações na timeline
# ──────────────────────────────────────────────


def handle_audit_implantacao_criada(event: ImplantacaoCriada) -> None:
    """Registra criação de implantação no log de auditoria."""
    try:
        from ..domain.audit_service import log_action

        log_action(
            action="CREATE",
            target_type="implantacao",
            target_id=str(event.implantacao_id),
            metadata={
                "nome_empresa": event.nome_empresa,
                "evento": "ImplantacaoCriada",
            },
            user_email=event.usuario_cs,
        )
        logger.debug(f"📝 Audit: implantação {event.implantacao_id} criada")
    except Exception as e:
        logger.warning(f"Audit handler falhou (ImplantacaoCriada): {e}")


def handle_audit_implantacao_finalizada(event: ImplantacaoFinalizada) -> None:
    """Registra finalização no log de auditoria."""
    try:
        from ..domain.audit_service import log_action

        log_action(
            action="FINALIZE",
            target_type="implantacao",
            target_id=str(event.implantacao_id),
            metadata={
                "nome_empresa": event.nome_empresa,
                "progresso_final": event.progresso_final,
                "evento": "ImplantacaoFinalizada",
            },
            user_email=event.usuario_cs,
        )
        logger.debug(f"📝 Audit: implantação {event.implantacao_id} finalizada")
    except Exception as e:
        logger.warning(f"Audit handler falhou (ImplantacaoFinalizada): {e}")


def handle_audit_implantacao_transferida(event: ImplantacaoTransferida) -> None:
    """Registra transferência no log de auditoria."""
    try:
        from ..domain.audit_service import log_action

        log_action(
            action="TRANSFER",
            target_type="implantacao",
            target_id=str(event.implantacao_id),
            changes={
                "before": {"usuario_cs": event.de_usuario},
                "after": {"usuario_cs": event.para_usuario},
            },
            user_email=event.de_usuario,
        )
        logger.debug(f"📝 Audit: implantação {event.implantacao_id} transferida")
    except Exception as e:
        logger.warning(f"Audit handler falhou (ImplantacaoTransferida): {e}")



# ──────────────────────────────────────────────
# Cache Handlers — Invalida caches após mudanças
# ──────────────────────────────────────────────


def handle_cache_implantacao_iniciada(event: ImplantacaoIniciada) -> None:
    """Invalida caches quando uma implantação é iniciada."""
    try:
        from ..config.cache_config import clear_dashboard_cache, clear_implantacao_cache, clear_user_cache

        clear_implantacao_cache(event.implantacao_id)
        clear_user_cache(event.usuario_cs)
        clear_dashboard_cache()
        logger.debug(f"🗑️ Cache invalidado: implantação {event.implantacao_id} iniciada")
    except Exception as e:
        logger.warning(f"Cache handler falhou (ImplantacaoIniciada): {e}")


def handle_cache_implantacao_finalizada(event: ImplantacaoFinalizada) -> None:
    """Invalida caches quando uma implantação é finalizada."""
    try:
        from ..config.cache_config import clear_dashboard_cache, clear_implantacao_cache, clear_user_cache

        clear_implantacao_cache(event.implantacao_id)
        clear_user_cache(event.usuario_cs)
        clear_dashboard_cache()
        logger.debug(f"🗑️ Cache invalidado: implantação {event.implantacao_id} finalizada")
    except Exception as e:
        logger.warning(f"Cache handler falhou (ImplantacaoFinalizada): {e}")


def handle_cache_item_concluido(event: ChecklistItemConcluido) -> None:
    """Invalida caches quando um item do checklist é concluído."""
    try:
        from ..config.cache_config import clear_implantacao_cache

        clear_implantacao_cache(event.implantacao_id)
        logger.debug(f"🗑️ Cache invalidado: item {event.item_id} concluído")
    except Exception as e:
        logger.warning(f"Cache handler falhou (ChecklistItemConcluido): {e}")


def handle_cache_comentario_adicionado(event: ChecklistComentarioAdicionado) -> None:
    """Invalida caches quando um comentário é adicionado."""
    try:
        from ..config.cache_config import clear_dashboard_cache, clear_implantacao_cache

        clear_implantacao_cache(event.implantacao_id)
        clear_dashboard_cache()
        logger.debug(f"🗑️ Cache invalidado: comentário no item {event.item_id}")
    except Exception as e:
        logger.warning(f"Cache handler falhou (ChecklistComentarioAdicionado): {e}")


def handle_cache_plano_atribuido(event: PlanoAtribuido) -> None:
    """Invalida caches quando um plano é atribuído."""
    try:
        from ..config.cache_config import clear_implantacao_cache

        clear_implantacao_cache(event.implantacao_id)
        logger.debug(f"🗑️ Cache invalidado: plano {event.plano_id} atribuído")
    except Exception as e:
        logger.warning(f"Cache handler falhou (PlanoAtribuido): {e}")


def handle_cache_implantacao_transferida(event: ImplantacaoTransferida) -> None:
    """Invalida caches de ambos os usuários na transferência."""
    try:
        from ..config.cache_config import clear_dashboard_cache, clear_implantacao_cache, clear_user_cache

        clear_implantacao_cache(event.implantacao_id)
        clear_user_cache(event.de_usuario)
        clear_user_cache(event.para_usuario)
        clear_dashboard_cache()
        logger.debug(f"🗑️ Cache invalidado: implantação {event.implantacao_id} transferida")
    except Exception as e:
        logger.warning(f"Cache handler falhou (ImplantacaoTransferida): {e}")


# ──────────────────────────────────────────────
# Gamification Handlers — Atualiza métricas
# ──────────────────────────────────────────────


def handle_gamification_finalizada(event: ImplantacaoFinalizada) -> None:
    """Limpa cache de gamificação ao finalizar implantação."""
    try:
        from ..domain.gamification.utils import clear_gamification_cache

        clear_gamification_cache()
        logger.debug(f"🎮 Gamificação: cache limpo após finalização {event.implantacao_id}")
    except Exception as e:
        logger.warning(f"Gamification handler falhou (ImplantacaoFinalizada): {e}")


def handle_gamification_item_concluido(event: ChecklistItemConcluido) -> None:
    """Limpa cache de gamificação ao concluir item."""
    try:
        from ..domain.gamification.utils import clear_gamification_cache

        # Limpa cache apenas quando progresso atinge marcos relevantes
        if event.progresso_atual in (25.0, 50.0, 75.0, 100.0):
            clear_gamification_cache()
            logger.debug(
                f"🎮 Gamificação: cache limpo (marco {event.progresso_atual}% atingido)"
            )
    except Exception as e:
        logger.warning(f"Gamification handler falhou (ChecklistItemConcluido): {e}")


# ──────────────────────────────────────────────
# Logging Handlers — logs de atividade do usuário
# ──────────────────────────────────────────────


def handle_log_usuario_logado(event: UsuarioLogado) -> None:
    """Registra login do usuário para analytics."""
    logger.info(f"🔐 Login: {event.email} via {event.provider}")


# ──────────────────────────────────────────────
# Registro de Handlers
# ──────────────────────────────────────────────


def register_event_handlers(event_bus) -> None:
    """
    Registra todos os handlers no EventBus.

    Chamado durante o startup da aplicação (create_app).
    Cada handler é registrado para um tipo específico de evento.
    """
    from .events import (
        ChecklistComentarioAdicionado,
        ChecklistItemConcluido,
        ImplantacaoCriada,
        ImplantacaoFinalizada,
        ImplantacaoIniciada,
        ImplantacaoTransferida,
        PlanoAtribuido,
        UsuarioLogado,
    )

    # Audit handlers
    event_bus.register(ImplantacaoCriada, handle_audit_implantacao_criada)
    event_bus.register(ImplantacaoFinalizada, handle_audit_implantacao_finalizada)
    event_bus.register(ImplantacaoTransferida, handle_audit_implantacao_transferida)

    # Cache handlers
    event_bus.register(ImplantacaoIniciada, handle_cache_implantacao_iniciada)
    event_bus.register(ImplantacaoFinalizada, handle_cache_implantacao_finalizada)
    event_bus.register(ChecklistItemConcluido, handle_cache_item_concluido)
    event_bus.register(ChecklistComentarioAdicionado, handle_cache_comentario_adicionado)
    event_bus.register(PlanoAtribuido, handle_cache_plano_atribuido)
    event_bus.register(ImplantacaoTransferida, handle_cache_implantacao_transferida)

    # Gamification handlers
    event_bus.register(ImplantacaoFinalizada, handle_gamification_finalizada)
    event_bus.register(ChecklistItemConcluido, handle_gamification_item_concluido)

    # Log handlers
    event_bus.register(UsuarioLogado, handle_log_usuario_logado)

    total = sum(len(h) for h in event_bus._handlers.values())
    logger.info(f"📢 EventBus: {total} handlers registrados para {len(event_bus._handlers)} tipos de evento")
