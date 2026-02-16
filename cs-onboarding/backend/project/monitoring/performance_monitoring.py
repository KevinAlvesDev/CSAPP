import time
from datetime import datetime
from functools import wraps

from flask import current_app, g, request


class PerformanceMonitor:
    """
    Monitor de performance simples para rastrear métricas da aplicação.

    Coleta métricas como:
    - Tempo de resposta de endpoints
    - Número de queries executadas
    - Erros e exceções
    - Uso de cache
    """

    def __init__(self, app=None):
        self.metrics = []
        self.max_metrics = 1000

        if app:
            self.init_app(app)

    def init_app(self, app):
        """Inicializa o monitor com o app Flask."""
        app.before_request(self.before_request)
        app.after_request(self.after_request)
        app.teardown_request(self.teardown_request)

        if "view_metrics" not in app.view_functions:

            @app.route("/admin/metrics")
            def view_metrics():
                """Endpoint para visualizar métricas (apenas admin)."""
                from ..blueprints.auth import login_required
                from ..constants import PERFIL_ADMIN

                decorated = login_required(lambda: None)
                res = decorated()
                if res is not None:
                    return res

                if not hasattr(g, "perfil") or g.perfil.get("perfil_acesso") != PERFIL_ADMIN:
                    return "Acesso negado", 403

                return {
                    "total_requests": len(self.metrics),
                    "recent_metrics": self.metrics[-100:],
                    "summary": self.get_summary(),
                }

    def before_request(self):
        """Executado antes de cada request."""
        g.start_time = time.time()
        g.query_count = 0
        g.cache_hits = 0
        g.cache_misses = 0

    def after_request(self, response):
        """Executado após cada request."""
        if hasattr(g, "start_time"):
            elapsed = time.time() - g.start_time

            metric = {
                "timestamp": datetime.now().isoformat(),
                "method": request.method,
                "path": request.path,
                "status_code": response.status_code,
                "duration_ms": round(elapsed * 1000, 2),
                "query_count": getattr(g, "query_count", 0),
                "cache_hits": getattr(g, "cache_hits", 0),
                "cache_misses": getattr(g, "cache_misses", 0),
                "user": getattr(g, "user_email", "anonymous"),
            }

            self.metrics.append(metric)

            if len(self.metrics) > self.max_metrics:
                self.metrics = self.metrics[-self.max_metrics :]

            if elapsed > 1.0:
                current_app.logger.warning(
                    f"Slow request: {request.method} {request.path} "
                    f"took {elapsed:.2f}s ({metric['query_count']} queries)"
                )

        return response

    def teardown_request(self, exception=None):
        """Executado no teardown da request."""
        if exception:
            current_app.logger.error(f"Request exception: {exception}")

    def get_summary(self):
        """Retorna resumo das métricas."""
        if not self.metrics:
            return {}

        total = len(self.metrics)
        durations = [m["duration_ms"] for m in self.metrics]
        queries = [m["query_count"] for m in self.metrics]

        return {
            "total_requests": total,
            "avg_duration_ms": round(sum(durations) / total, 2),
            "max_duration_ms": max(durations),
            "min_duration_ms": min(durations),
            "avg_queries_per_request": round(sum(queries) / total, 2),
            "total_queries": sum(queries),
            "slow_requests": len([d for d in durations if d > 1000]),
            "error_requests": len([m for m in self.metrics if m["status_code"] >= 400]),
        }


def track_query():
    """Incrementa contador de queries na request atual."""
    if hasattr(g, "query_count"):
        g.query_count += 1


def track_cache_hit():
    """Incrementa contador de cache hits."""
    if hasattr(g, "cache_hits"):
        g.cache_hits += 1


def track_cache_miss():
    """Incrementa contador de cache misses."""
    if hasattr(g, "cache_misses"):
        g.cache_misses += 1


def monitor_function(func):
    """
    Decorador para monitorar performance de funções.

    Uso:
        @monitor_function
        def my_slow_function():
            ...
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        try:
            result = func(*args, **kwargs)
            elapsed = time.time() - start

            if elapsed > 0.5:
                current_app.logger.info(f"Function {func.__name__} took {elapsed:.2f}s")

            return result
        except Exception as e:
            elapsed = time.time() - start
            current_app.logger.error(f"Function {func.__name__} failed after {elapsed:.2f}s: {e}")
            raise

    return wrapper


performance_monitor = PerformanceMonitor()
