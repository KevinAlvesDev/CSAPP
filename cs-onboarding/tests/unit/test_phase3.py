"""
Testes para a Fase 3: Container, Cache Warming e Métricas.

Cobre:
- ServiceContainer: registro de services e resolução
- Cache Warming: pré-carregamento de configs
- Métricas: endpoint de health/metrics
"""

from unittest.mock import MagicMock, patch

# ──────────────────────────────────────────────
# Service Container
# ──────────────────────────────────────────────


class TestServiceRegistry:
    """Testa o registro de services no container."""

    def test_register_all_services(self):
        """Verifica que todos os services são registrados."""
        from backend.project.core.container import ServiceContainer
        from backend.project.core.service_registry import register_all_services

        mock_app = MagicMock()
        mock_app.config = {"DEBUG": True}

        container = ServiceContainer()
        register_all_services(mock_app, container)

        # Deve ter registrado services core
        assert container.has("config")
        assert container.has("db")
        assert container.has("event_bus")
        assert container.has("query_profiler")

        # Deve ter registrado services de domínio
        assert container.has("dashboard_service")
        assert container.has("implantacao_service")
        assert container.has("config_service")
        assert container.has("checklist_service")

        # Deve ter registrado infra
        assert container.has("dataloader_factory")

    def test_container_resolves_event_bus(self):
        """Verifica que o EventBus é resolvido corretamente."""
        from backend.project.core.container import ServiceContainer
        from backend.project.core.events import EventBus
        from backend.project.core.service_registry import register_all_services

        mock_app = MagicMock()
        mock_app.config = {"DEBUG": True}

        container = ServiceContainer()
        register_all_services(mock_app, container)

        event_bus = container.resolve("event_bus")
        assert isinstance(event_bus, EventBus)

    def test_container_resolves_dataloader_factory(self):
        """Verifica que o DataLoader factory retorna construtores."""
        from backend.project.core.container import ServiceContainer
        from backend.project.core.service_registry import register_all_services

        mock_app = MagicMock()
        mock_app.config = {"DEBUG": True}

        container = ServiceContainer()
        register_all_services(mock_app, container)

        factory = container.resolve("dataloader_factory")
        assert "checklist" in factory
        assert "comentarios" in factory
        assert "implantacao" in factory

    def test_container_lists_all_services(self):
        """Verifica lista de services registrados."""
        from backend.project.core.container import ServiceContainer
        from backend.project.core.service_registry import register_all_services

        mock_app = MagicMock()
        mock_app.config = {"DEBUG": True}

        container = ServiceContainer()
        register_all_services(mock_app, container)

        services = container.registered_services()
        assert len(services) > 10  # Pelo menos 10 services


# ──────────────────────────────────────────────
# Cache Warming
# ──────────────────────────────────────────────


class TestCacheWarming:
    """Testa o pré-carregamento de cache no startup."""

    def test_warm_cache_loads_all_resources(self):
        """Verifica que warm_cache carrega todos os recursos."""
        from backend.project.config.cache_warming import warm_cache

        # Patch the _FETCH_MAP directly so warm_cache uses our mocks
        mock_fetch_map = {
            "_fetch_tags": lambda: [{"id": 1, "nome": "teste"}],
            "_fetch_status_implantacao": lambda: [{"id": 1, "codigo": "EM_ANDAMENTO"}],
            "_fetch_niveis_atendimento": lambda: [{"id": 1, "codigo": "BASICO"}],
            "_fetch_tipos_evento": lambda: [{"id": 1, "codigo": "COMENTARIO"}],
            "_fetch_motivos_parada": lambda: [{"id": 1, "descricao": "Problema técnico"}],
            "_fetch_motivos_cancelamento": lambda: [{"id": 1, "descricao": "Desistência"}],
        }

        mock_cache_mgr = MagicMock()
        mock_app = MagicMock()
        mock_app.cache_manager = mock_cache_mgr

        with patch("backend.project.config.cache_warming._FETCH_MAP", mock_fetch_map):
            result = warm_cache(mock_app, cache_manager=mock_cache_mgr)

        assert result["status"] == "completed"
        assert result["succeeded"] == 6
        assert result["failed"] == 0
        assert mock_cache_mgr.set.call_count == 6

    def test_warm_cache_handles_errors_gracefully(self):
        """Verifica que erros não impedem o warming dos outros recursos."""
        from backend.project.config.cache_warming import warm_cache

        mock_cache_mgr = MagicMock()
        mock_app = MagicMock()
        mock_app.cache_manager = mock_cache_mgr

        # Simular erro: patch _FETCH_MAP with a function that raises
        broken_map = {
            "_fetch_tags": MagicMock(side_effect=Exception("DB down")),
            "_fetch_status_implantacao": MagicMock(side_effect=Exception("DB down")),
            "_fetch_niveis_atendimento": MagicMock(side_effect=Exception("DB down")),
            "_fetch_tipos_evento": MagicMock(side_effect=Exception("DB down")),
            "_fetch_motivos_parada": MagicMock(side_effect=Exception("DB down")),
            "_fetch_motivos_cancelamento": MagicMock(side_effect=Exception("DB down")),
        }

        with patch("backend.project.config.cache_warming._FETCH_MAP", broken_map):
            result = warm_cache(mock_app, cache_manager=mock_cache_mgr)

        # Deve completar mesmo com erros
        assert result["status"] == "completed"
        assert result["failed"] >= 1

    def test_warm_cache_skips_without_cache_manager(self):
        """Verifica que sem cache manager, o warming é ignorado."""
        from backend.project.config.cache_warming import warm_cache

        mock_app = MagicMock(spec=[])  # Sem cache_manager

        result = warm_cache(mock_app, cache_manager=None)

        assert result["status"] == "skipped"

    def test_refresh_config_cache(self):
        """Testa refresh de cache on-demand."""
        from backend.project.config.cache_warming import refresh_config_cache

        mock_fetch_map = {
            "_fetch_tags": lambda: [{"id": 1}],
            "_fetch_status_implantacao": lambda: [{"id": 1}],
            "_fetch_niveis_atendimento": lambda: [{"id": 1}],
            "_fetch_tipos_evento": lambda: [{"id": 1}],
            "_fetch_motivos_parada": lambda: [{"id": 1}],
            "_fetch_motivos_cancelamento": lambda: [{"id": 1}],
        }

        mock_cache_mgr = MagicMock()

        with patch("backend.project.config.cache_warming._FETCH_MAP", mock_fetch_map):
            results = refresh_config_cache(cache_manager=mock_cache_mgr)

        assert all(v == "refreshed" for v in results.values())
