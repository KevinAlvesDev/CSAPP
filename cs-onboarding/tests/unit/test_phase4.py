"""
Testes para a Fase 4: Event-Driven Architecture.

Cobre:
- Event Handlers: audit, cache, gamification, log
- Emissão de eventos nos services
- Registro de handlers no startup
"""

from unittest.mock import MagicMock, patch

import pytest

from backend.project.core.events import (
    ChecklistComentarioAdicionado,
    ChecklistItemConcluido,
    EventBus,
    ImplantacaoCriada,
    ImplantacaoFinalizada,
    ImplantacaoIniciada,
    ImplantacaoTransferida,
    PlanoAtribuido,
    UsuarioLogado,
)


# ──────────────────────────────────────────────
# Handler Registration
# ──────────────────────────────────────────────


class TestEventHandlerRegistration:
    """Testa o registro de handlers no EventBus."""

    def test_register_event_handlers_wires_all_handlers(self):
        """Verifica que todos os handlers são registrados."""
        from backend.project.core.event_handlers import register_event_handlers

        bus = EventBus()
        register_event_handlers(bus)

        # Deve ter handlers para esses tipos
        assert len(bus.get_handlers(ImplantacaoCriada)) >= 1
        assert len(bus.get_handlers(ImplantacaoFinalizada)) >= 2  # audit + cache + gamification
        assert len(bus.get_handlers(ImplantacaoIniciada)) >= 1
        assert len(bus.get_handlers(ImplantacaoTransferida)) >= 2  # audit + cache
        assert len(bus.get_handlers(ChecklistItemConcluido)) >= 2  # cache + gamification
        assert len(bus.get_handlers(ChecklistComentarioAdicionado)) >= 1
        assert len(bus.get_handlers(PlanoAtribuido)) >= 1
        assert len(bus.get_handlers(UsuarioLogado)) >= 1

    def test_total_handler_count(self):
        """Verifica contagem total de handlers."""
        from backend.project.core.event_handlers import register_event_handlers

        bus = EventBus()
        register_event_handlers(bus)

        total = sum(len(h) for h in bus._handlers.values())
        assert total >= 12  # Pelo menos 12 handlers

    def test_stats_after_registration(self):
        """Verifica stats do EventBus após registro."""
        from backend.project.core.event_handlers import register_event_handlers

        bus = EventBus()
        register_event_handlers(bus)

        stats = bus.stats
        assert stats["registered_event_types"] >= 7
        assert stats["handlers_count"] >= 12
        assert stats["enabled"] is True


# ──────────────────────────────────────────────
# Audit Handlers
# ──────────────────────────────────────────────


class TestAuditHandlers:
    """Testa handlers de auditoria."""

    @patch("backend.project.core.event_handlers.logger")
    def test_audit_implantacao_criada(self, mock_logger):
        """Testa que audit handler de criação funciona."""
        from backend.project.core.event_handlers import handle_audit_implantacao_criada

        event = ImplantacaoCriada(
            implantacao_id=42,
            usuario_cs="user@test.com",
            nome_empresa="ACME Corp",
        )

        with patch("backend.project.core.event_handlers.handle_audit_implantacao_criada.__module__"):
            # Handler deve rodar sem erros (log_action pode falhar sem DB)
            handle_audit_implantacao_criada(event)

    @patch("backend.project.domain.audit_service.log_action", return_value=True)
    def test_audit_implantacao_finalizada_calls_log_action(self, mock_log):
        """Testa que finalização chama log_action com params corretos."""
        from backend.project.core.event_handlers import handle_audit_implantacao_finalizada

        event = ImplantacaoFinalizada(
            implantacao_id=42,
            usuario_cs="user@test.com",
            nome_empresa="ACME Corp",
            progresso_final=100.0,
        )

        handle_audit_implantacao_finalizada(event)

        mock_log.assert_called_once()
        call_kwargs = mock_log.call_args
        assert call_kwargs[1]["action"] == "FINALIZE"
        assert call_kwargs[1]["target_type"] == "implantacao"
        assert call_kwargs[1]["target_id"] == "42"
        assert call_kwargs[1]["user_email"] == "user@test.com"

    @patch("backend.project.domain.audit_service.log_action", return_value=True)
    def test_audit_implantacao_transferida_includes_changes(self, mock_log):
        """Testa que transferência inclui before/after no log."""
        from backend.project.core.event_handlers import handle_audit_implantacao_transferida

        event = ImplantacaoTransferida(
            implantacao_id=42,
            de_usuario="old@test.com",
            para_usuario="new@test.com",
        )

        handle_audit_implantacao_transferida(event)

        mock_log.assert_called_once()
        call_kwargs = mock_log.call_args[1]
        assert call_kwargs["changes"]["before"]["usuario_cs"] == "old@test.com"
        assert call_kwargs["changes"]["after"]["usuario_cs"] == "new@test.com"


# ──────────────────────────────────────────────
# Cache Handlers
# ──────────────────────────────────────────────


class TestCacheHandlers:
    """Testa handlers de invalidação de cache."""

    @patch("backend.project.core.event_handlers.logger")
    def test_cache_implantacao_iniciada(self, mock_logger):
        """Testa invalidação de cache ao iniciar."""
        from backend.project.core.event_handlers import handle_cache_implantacao_iniciada

        event = ImplantacaoIniciada(
            implantacao_id=42,
            usuario_cs="user@test.com",
            nome_empresa="ACME",
        )

        with patch("backend.project.config.cache_config.clear_implantacao_cache") as mock_clear_impl, \
             patch("backend.project.config.cache_config.clear_user_cache") as mock_clear_user, \
             patch("backend.project.config.cache_config.clear_dashboard_cache") as mock_clear_dash:
            handle_cache_implantacao_iniciada(event)

            mock_clear_impl.assert_called_once_with(42)
            mock_clear_user.assert_called_once_with("user@test.com")
            mock_clear_dash.assert_called_once()

    @patch("backend.project.core.event_handlers.logger")
    def test_cache_item_concluido(self, mock_logger):
        """Testa invalidação de cache ao concluir item."""
        from backend.project.core.event_handlers import handle_cache_item_concluido

        event = ChecklistItemConcluido(
            item_id=10,
            implantacao_id=42,
            usuario="user@test.com",
            progresso_atual=50.0,
        )

        with patch("backend.project.config.cache_config.clear_implantacao_cache") as mock_clear:
            handle_cache_item_concluido(event)
            mock_clear.assert_called_once_with(42)

    @patch("backend.project.core.event_handlers.logger")
    def test_cache_transferencia_invalida_ambos_usuarios(self, mock_logger):
        """Testa que transferência invalida cache de ambos usuários."""
        from backend.project.core.event_handlers import handle_cache_implantacao_transferida

        event = ImplantacaoTransferida(
            implantacao_id=42,
            de_usuario="old@test.com",
            para_usuario="new@test.com",
        )

        with patch("backend.project.config.cache_config.clear_implantacao_cache") as mock_impl, \
             patch("backend.project.config.cache_config.clear_user_cache") as mock_user, \
             patch("backend.project.config.cache_config.clear_dashboard_cache"):
            handle_cache_implantacao_transferida(event)

            mock_impl.assert_called_once_with(42)
            assert mock_user.call_count == 2  # old + new user


# ──────────────────────────────────────────────
# Gamification Handlers
# ──────────────────────────────────────────────


class TestGamificationHandlers:
    """Testa handlers de gamificação."""

    def test_gamification_finalizada_clears_cache(self):
        """Testa que finalização limpa cache de gamificação."""
        from backend.project.core.event_handlers import handle_gamification_finalizada

        event = ImplantacaoFinalizada(
            implantacao_id=42,
            usuario_cs="user@test.com",
            nome_empresa="ACME",
            progresso_final=100.0,
        )

        with patch("backend.project.domain.gamification.utils.clear_gamification_cache") as mock_clear:
            handle_gamification_finalizada(event)
            mock_clear.assert_called_once()

    def test_gamification_item_only_at_milestones(self):
        """Testa que gamificação só limpa cache em marcos (25/50/75/100%)."""
        from backend.project.core.event_handlers import handle_gamification_item_concluido

        # 50% → deve limpar
        event_50 = ChecklistItemConcluido(
            item_id=10,
            implantacao_id=42,
            usuario="user@test.com",
            progresso_atual=50.0,
        )

        # 33% → não deve limpar
        event_33 = ChecklistItemConcluido(
            item_id=11,
            implantacao_id=42,
            usuario="user@test.com",
            progresso_atual=33.0,
        )

        with patch("backend.project.domain.gamification.utils.clear_gamification_cache") as mock_clear:
            handle_gamification_item_concluido(event_50)
            assert mock_clear.call_count == 1

            mock_clear.reset_mock()

            handle_gamification_item_concluido(event_33)
            assert mock_clear.call_count == 0


# ──────────────────────────────────────────────
# Integration: EventBus + Handlers
# ──────────────────────────────────────────────


class TestEventBusIntegration:
    """Testa o fluxo completo: emissão → handler."""

    def test_emit_triggers_handler(self):
        """Verifica que emitir evento executa o handler."""
        from backend.project.core.event_handlers import register_event_handlers

        bus = EventBus()
        register_event_handlers(bus)

        event = UsuarioLogado(email="test@test.com", provider="auth0")

        # Deve emitir sem erros
        bus.emit(event)

        # Verificar que foi registrado no histórico
        history = bus.get_history(UsuarioLogado, limit=1)
        assert len(history) == 1
        assert history[0]["data"]["email"] == "test@test.com"

    def test_multiple_handlers_per_event(self):
        """Verifica que múltiplos handlers executam para o mesmo evento."""
        from backend.project.core.event_handlers import register_event_handlers

        bus = EventBus()
        register_event_handlers(bus)

        # ImplantacaoFinalizada tem 3 handlers: audit + cache + gamification
        handlers = bus.get_handlers(ImplantacaoFinalizada)
        assert len(handlers) >= 3

    def test_handler_error_doesnt_break_flow(self):
        """Verifica que erro em um handler não afeta os outros."""
        bus = EventBus()

        results = []

        def handler_ok(event):
            results.append("ok")

        def handler_error(event):
            raise RuntimeError("Handler falhou!")

        def handler_ok2(event):
            results.append("ok2")

        bus.register(UsuarioLogado, handler_ok)
        bus.register(UsuarioLogado, handler_error)
        bus.register(UsuarioLogado, handler_ok2)

        event = UsuarioLogado(email="test@test.com", provider="dev")
        bus.emit(event)

        # handler_ok e handler_ok2 devem ter executado
        assert "ok" in results
        assert "ok2" in results

    def test_disabled_bus_skips_handlers(self):
        """Verifica que EventBus desabilitado não executa handlers."""
        bus = EventBus()

        called = []
        bus.register(UsuarioLogado, lambda e: called.append(True))
        bus.disable()

        bus.emit(UsuarioLogado(email="test@test.com", provider="dev"))

        assert len(called) == 0

        bus.enable()
        bus.emit(UsuarioLogado(email="test@test.com", provider="dev"))

        assert len(called) == 1
