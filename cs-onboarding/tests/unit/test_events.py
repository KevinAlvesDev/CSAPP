"""
Testes unitários para o Event Bus e DataLoader.

Testa:
- EventBus: registro, emissão, error handling
- DomainEvents: criação e dados
- DataLoader: lógica de batch loading
"""

from backend.project.core.events import (
    EventBus,
    ImplantacaoCriada,
    ImplantacaoFinalizada,
    ImplantacaoIniciada,
)


class TestDomainEvents:
    """Testes para eventos de domínio."""

    def test_event_has_timestamp(self):
        event = ImplantacaoIniciada(implantacao_id=1, usuario_cs="test@test.com")
        assert event.timestamp > 0

    def test_event_has_unique_id(self):
        e1 = ImplantacaoIniciada(implantacao_id=1, usuario_cs="test@test.com")
        e2 = ImplantacaoIniciada(implantacao_id=2, usuario_cs="test@test.com")
        assert e1.event_id != e2.event_id

    def test_event_name(self):
        event = ImplantacaoIniciada(implantacao_id=1, usuario_cs="test@test.com")
        assert event.event_name == "ImplantacaoIniciada"

    def test_event_stores_data(self):
        event = ImplantacaoCriada(
            implantacao_id=42,
            usuario_cs="user@company.com",
            nome_empresa="Acme Corp",
        )
        assert event.implantacao_id == 42
        assert event.usuario_cs == "user@company.com"
        assert event.nome_empresa == "Acme Corp"


class TestEventBus:
    """Testes para o Event Bus."""

    def setup_method(self):
        """Cria um EventBus limpo para cada teste."""
        self.bus = EventBus()

    def test_register_and_emit(self):
        """Testa registro e emissão de eventos."""
        received = []

        @self.bus.on(ImplantacaoIniciada)
        def handler(event):
            received.append(event)

        self.bus.emit(
            ImplantacaoIniciada(
                implantacao_id=1,
                usuario_cs="test@test.com",
            )
        )

        assert len(received) == 1
        assert received[0].implantacao_id == 1

    def test_multiple_handlers(self):
        """Testa múltiplos handlers para o mesmo evento."""
        results = []

        @self.bus.on(ImplantacaoIniciada)
        def handler1(event):
            results.append("handler1")

        @self.bus.on(ImplantacaoIniciada)
        def handler2(event):
            results.append("handler2")

        self.bus.emit(ImplantacaoIniciada(implantacao_id=1, usuario_cs="test"))

        assert len(results) == 2
        assert "handler1" in results
        assert "handler2" in results

    def test_handler_error_does_not_propagate(self):
        """Testa que erro em handler não afeta o fluxo."""
        results = []

        @self.bus.on(ImplantacaoIniciada)
        def failing_handler(event):
            raise ValueError("Erro intencional")

        @self.bus.on(ImplantacaoIniciada)
        def good_handler(event):
            results.append("ok")

        # Não deve lançar exceção
        self.bus.emit(ImplantacaoIniciada(implantacao_id=1, usuario_cs="test"))

        # O segundo handler deve ter executado mesmo com erro no primeiro
        assert "ok" in results

    def test_different_event_types(self):
        """Testa que handlers são isolados por tipo de evento."""
        received_iniciada = []
        received_finalizada = []

        @self.bus.on(ImplantacaoIniciada)
        def handler_iniciada(event):
            received_iniciada.append(event)

        @self.bus.on(ImplantacaoFinalizada)
        def handler_finalizada(event):
            received_finalizada.append(event)

        self.bus.emit(ImplantacaoIniciada(implantacao_id=1, usuario_cs="test"))

        assert len(received_iniciada) == 1
        assert len(received_finalizada) == 0

    def test_event_history(self):
        """Testa histórico de eventos."""
        self.bus.emit(ImplantacaoIniciada(implantacao_id=1, usuario_cs="test"))
        self.bus.emit(ImplantacaoCriada(implantacao_id=2, usuario_cs="test"))

        history = self.bus.get_history()
        assert len(history) == 2
        assert history[0]["event_name"] == "ImplantacaoIniciada"
        assert history[1]["event_name"] == "ImplantacaoCriada"

    def test_event_history_filtered(self):
        """Testa filtro de histórico por tipo."""
        self.bus.emit(ImplantacaoIniciada(implantacao_id=1, usuario_cs="test"))
        self.bus.emit(ImplantacaoCriada(implantacao_id=2, usuario_cs="test"))

        history = self.bus.get_history(event_type=ImplantacaoIniciada)
        assert len(history) == 1

    def test_disable_enable(self):
        """Testa habilitar/desabilitar Event Bus."""
        results = []

        @self.bus.on(ImplantacaoIniciada)
        def handler(event):
            results.append("received")

        self.bus.disable()
        self.bus.emit(ImplantacaoIniciada(implantacao_id=1, usuario_cs="test"))
        assert len(results) == 0

        self.bus.enable()
        self.bus.emit(ImplantacaoIniciada(implantacao_id=1, usuario_cs="test"))
        assert len(results) == 1

    def test_stats(self):
        """Testa estatísticas do Event Bus."""

        @self.bus.on(ImplantacaoIniciada)
        def handler(event):
            pass

        stats = self.bus.stats
        assert stats["registered_event_types"] == 1
        assert stats["handlers_count"] == 1
        assert stats["enabled"] is True

    def test_clear_handlers(self):
        """Testa limpeza de handlers."""

        @self.bus.on(ImplantacaoIniciada)
        def handler(event):
            pass

        self.bus.clear_handlers()
        assert len(self.bus.get_handlers(ImplantacaoIniciada)) == 0

    def test_clear_history(self):
        """Testa limpeza do histórico."""
        self.bus.emit(ImplantacaoIniciada(implantacao_id=1, usuario_cs="test"))
        self.bus.clear_history()
        assert len(self.bus.get_history()) == 0
