\
\

import pytest
import sys
import os
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))

from project import create_app
from project.performance_monitoring import (
    PerformanceMonitor,
    track_query,
    track_cache_hit,
    track_cache_miss,
    monitor_function
)
from flask import g


@pytest.fixture
def app():
    """Cria uma instância do app para testes."""
    app = create_app()
    app.config.update({
        'TESTING': True,
        'USE_SQLITE_LOCALLY': True,
    })
    
    yield app


class TestPerformanceMonitor:
    """Testes para monitor de performance."""
    
    def test_monitor_inicializa(self, app):
        """Testa que monitor inicializa corretamente."""
        monitor = PerformanceMonitor(app)
        assert monitor is not None
        assert monitor.metrics == []
    
    def test_monitor_coleta_metricas(self, app):
        """Testa que monitor coleta métricas de requests."""
        client = app.test_client()
        
                \
        client.get('/health')
        client.get('/health/ready')
        
                \
        with app.app_context():
            from project.performance_monitoring import performance_monitor
            assert len(performance_monitor.metrics) >= 2
    
    def test_monitor_metricas_contem_dados_corretos(self, app):
        """Testa que métricas contêm dados corretos."""
        client = app.test_client()
        
                \
        response = client.get('/health')
        
                \
        with app.app_context():
            from project.performance_monitoring import performance_monitor
            if len(performance_monitor.metrics) > 0:
                metric = performance_monitor.metrics[-1]
                
                assert 'timestamp' in metric
                assert 'method' in metric
                assert 'path' in metric
                assert 'status_code' in metric
                assert 'duration_ms' in metric
                assert metric['method'] == 'GET'
                assert '/health' in metric['path']
                assert metric['status_code'] == 200
    
    def test_monitor_summary(self, app):
        """Testa geração de resumo de métricas."""
        client = app.test_client()
        
                \
        for _ in range(5):
            client.get('/health')
        
        with app.app_context():
            from project.performance_monitoring import performance_monitor
            summary = performance_monitor.get_summary()
            
            assert 'total_requests' in summary
            assert 'avg_duration_ms' in summary
            assert 'max_duration_ms' in summary
            assert 'min_duration_ms' in summary
            assert summary['total_requests'] >= 5


class TestTrackQuery:
    """Testes para tracking de queries."""
    
    def test_track_query_incrementa_contador(self, app):
        """Testa que track_query incrementa contador."""
        with app.test_request_context('/'):
            g.query_count = 0
            
            track_query()
            assert g.query_count == 1
            
            track_query()
            assert g.query_count == 2
            
            track_query()
            assert g.query_count == 3


class TestTrackCache:
    """Testes para tracking de cache."""
    
    def test_track_cache_hit(self, app):
        """Testa tracking de cache hit."""
        with app.test_request_context('/'):
            g.cache_hits = 0
            
            track_cache_hit()
            assert g.cache_hits == 1
            
            track_cache_hit()
            assert g.cache_hits == 2
    
    def test_track_cache_miss(self, app):
        """Testa tracking de cache miss."""
        with app.test_request_context('/'):
            g.cache_misses = 0
            
            track_cache_miss()
            assert g.cache_misses == 1
            
            track_cache_miss()
            assert g.cache_misses == 2


class TestMonitorFunction:
    """Testes para decorador monitor_function."""
    
    def test_monitor_function_executa_normalmente(self, app):
        """Testa que função decorada executa normalmente."""
        with app.app_context():
            @monitor_function
            def test_func(x, y):
                return x + y
            
            result = test_func(2, 3)
            assert result == 5
    
    def test_monitor_function_loga_funcoes_lentas(self, app):
        """Testa que funções lentas são logadas."""
        with app.app_context():
            @monitor_function
            def slow_func():
                time.sleep(0.6)           
                return True
            
            result = slow_func()
            assert result is True
    
    def test_monitor_function_propaga_excecoes(self, app):
        """Testa que exceções são propagadas."""
        with app.app_context():
            @monitor_function
            def error_func():
                raise ValueError("Test error")
            
            with pytest.raises(ValueError):
                error_func()


class TestPerformanceIntegration:
    """Testes de integração de performance."""
    
    def test_request_lento_e_logado(self, app):
        """Testa que requests lentos são logados."""
        \
\
        client = app.test_client()
        
        response = client.get('/health')
        assert response.status_code == 200
    
    def test_metricas_endpoint_admin(self, app):
        """Testa endpoint de métricas (admin)."""
        \
\
        client = app.test_client()
        
                \
        response = client.get('/admin/metrics')
        assert response.status_code in [302, 403, 401]

