"""
Testes unitários para os Domain Services.

Testa:
- auth_service (sync de perfil, roles)
- Lógica de negócio isolada
"""

import os
from unittest.mock import patch

import pytest


class TestAuthService:
    """Testes para auth_service."""

    @pytest.fixture(autouse=True)
    def setup_env(self):
        """Configura variáveis de ambiente para teste."""
        with patch.dict(
            os.environ,
            {
                "SECRET_KEY": "test-key",
                "USE_SQLITE_LOCALLY": "True",
                "AUTH0_ENABLED": "false",
            },
        ):
            yield

    @patch("backend.project.domain.auth_service.query_db")
    @patch("backend.project.domain.auth_service.execute_db")
    def test_get_user_profile_service(self, mock_execute, mock_query):
        """Testa busca de perfil do usuário."""
        mock_query.return_value = {
            "usuario": "user@test.com",
            "nome": "Test User",
            "perfil_acesso": "Implantador",
        }

        from backend.project.domain.auth_service import get_user_profile_service

        result = get_user_profile_service("user@test.com")

        assert result is not None
        assert result["usuario"] == "user@test.com"
        assert result["perfil_acesso"] == "Implantador"
        mock_query.assert_called_once()

    @patch("backend.project.domain.auth_service.query_db")
    @patch("backend.project.domain.auth_service.execute_db")
    def test_update_user_role_service(self, mock_execute, mock_query):
        """Testa atualização de perfil de acesso."""
        from backend.project.domain.auth_service import update_user_role_service

        with patch("backend.project.domain.auth_service.clear_user_cache"):
            update_user_role_service("user@test.com", "Gerente")

        mock_execute.assert_called_once()
        call_args = mock_execute.call_args
        assert "UPDATE perfil_usuario" in call_args[0][0]
        assert "Gerente" in call_args[0][1]


class TestQueryProfiler:
    """Testes para o query profiler."""

    def test_profiler_measures_time(self):
        """Testa que o profiler mede o tempo corretamente."""
        import time

        from backend.project.common.query_profiler import QueryProfiler

        with QueryProfiler("test_operation"):
            time.sleep(0.01)  # 10ms

        # Verificar que o stats foi registrado
        stats = QueryProfiler.get_stats_summary()
        assert stats["total"] > 0

    def test_profiler_decorator(self):
        """Testa o decorator de profiling."""
        from backend.project.common.query_profiler import profile_query

        @profile_query("test_decorated")
        def dummy_function():
            return 42

        result = dummy_function()
        assert result == 42

    def test_profiler_stats_summary(self):
        """Testa o resumo de estatísticas."""
        from backend.project.common.query_profiler import QueryProfiler

        QueryProfiler.reset_stats()

        with QueryProfiler("op1"):
            pass
        with QueryProfiler("op2"):
            pass

        stats = QueryProfiler.get_stats_summary()
        assert stats["total"] == 2
        assert "avg_ms" in stats
        assert "max_ms" in stats


class TestCacheManager:
    """Testes para o cache manager aprimorado."""

    def test_cache_ttl_config(self):
        """Testa que a configuração de TTL está correta."""
        from backend.project.config.cache_manager import CACHE_TTL_CONFIG

        assert "dashboard" in CACHE_TTL_CONFIG
        assert CACHE_TTL_CONFIG["dashboard"]["ttl"] == 300
        assert CACHE_TTL_CONFIG["configuracoes"]["ttl"] == 3600

    def test_cache_manager_make_key(self):
        """Testa geração de chaves de cache."""
        from backend.project.config.cache_manager import CacheManager

        mgr = CacheManager()
        key = mgr._make_key("dashboard", user_email="test@test.com", page=1)
        assert "csapp:dashboard" in key
        assert "user_email=test@test.com" in key
        assert "page=1" in key

    def test_cache_manager_stats(self):
        """Testa métricas do cache manager."""
        from backend.project.config.cache_manager import CacheManager

        mgr = CacheManager()
        stats = mgr.get_stats()
        assert "hits" in stats
        assert "misses" in stats
        assert "hit_rate" in stats
        assert "ttl_config" in stats

    def test_cache_get_ttl(self):
        """Testa obtenção de TTL por recurso."""
        from backend.project.config.cache_manager import CacheManager

        mgr = CacheManager()
        assert mgr.get_ttl("dashboard") == 300
        assert mgr.get_ttl("configuracoes") == 3600
        assert mgr.get_ttl("unknown_resource") == 60  # default
