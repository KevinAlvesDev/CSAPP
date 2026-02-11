"""
Health Check Endpoints
Provides system status for monitoring and load balancers.

Endpoints:
- /health - Full health check (database, cache)
- /health/ready - Readiness check (is the app ready to serve traffic?)
- /health/live - Liveness check (is the app alive?)
- /health/db - Database-specific check
- /health/metrics - Performance metrics (query profiler, cache)
- /health/cache/refresh - Refresh config cache on-demand
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from flask import Blueprint, jsonify

health_bp = Blueprint("health", __name__)


@health_bp.route("/health", methods=["GET"])
def health_check() -> tuple[Any, int]:
    """
    Full health check that verifies:
    - Application is running
    - Database connection pool status
    - Database connection is working (optional)
    - Redis connection is working (if configured)

    Returns:
        200: All systems operational or degraded (app still usable)
        503: Critical failure (app cannot serve requests)
    """
    health_status: dict[str, Any] = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "checks": {},
    }

    all_healthy = True
    critical_failure = False

    # Check database connection pool
    try:
        from ..database import get_pool_stats, is_pool_initialized

        pool_initialized = is_pool_initialized()
        pool_stats = get_pool_stats()

        if pool_initialized:
            health_status["checks"]["database_pool"] = {
                "status": "healthy",
                **pool_stats,
            }
        else:
            # Pool not initialized - check if we're using SQLite
            from flask import current_app

            if current_app.config.get("USE_SQLITE_LOCALLY", False):
                health_status["checks"]["database_pool"] = {
                    "status": "not_applicable",
                    "note": "Using SQLite - no pool needed",
                }
            else:
                all_healthy = False
                health_status["checks"]["database_pool"] = {
                    "status": "unhealthy",
                    "error": "Pool not initialized",
                }
    except Exception as e:
        all_healthy = False
        health_status["checks"]["database_pool"] = {
            "status": "error",
            "error": str(e),
        }

    # Check actual database connection (try to execute a query)
    try:
        from ..database.db_pool import get_db_connection

        conn, db_type = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        cursor.close()

        health_status["checks"]["database_connection"] = {
            "status": "healthy",
            "type": db_type,
        }
    except RuntimeError as e:
        # Pool not initialized - degraded but not critical
        all_healthy = False
        health_status["checks"]["database_connection"] = {
            "status": "degraded",
            "error": str(e),
            "note": "Database unavailable - some features may not work",
        }
    except Exception as e:
        all_healthy = False
        health_status["checks"]["database_connection"] = {
            "status": "unhealthy",
            "error": str(e),
        }

    # Check Redis connection (if configured)
    try:
        from ..config.cache_config import cache

        if cache and hasattr(cache, "cache"):
            cache.set("health_check", "ok", timeout=5)
            value = cache.get("health_check")

            if value == "ok":
                health_status["checks"]["redis"] = {"status": "healthy"}
            else:
                all_healthy = False
                health_status["checks"]["redis"] = {
                    "status": "unhealthy",
                    "error": "Cache test failed",
                }
        else:
            health_status["checks"]["redis"] = {
                "status": "not_configured",
                "note": "Using SimpleCache (in-memory)",
            }
    except Exception:
        # Redis is optional
        health_status["checks"]["redis"] = {
            "status": "not_configured",
            "note": "Redis not available",
        }

    # Set overall status
    if critical_failure:
        health_status["status"] = "critical"
        return jsonify(health_status), 503
    elif not all_healthy:
        health_status["status"] = "degraded"
        # Return 200 even if degraded - app can still serve some requests
        return jsonify(health_status), 200

    return jsonify(health_status), 200


@health_bp.route("/health/ready", methods=["GET"])
def readiness_check() -> tuple[Any, int]:
    """
    Readiness check for Kubernetes/container orchestration.
    Returns 200 if the application is ready to serve traffic.

    For readiness, we require:
    - Application is running
    - Database pool is initialized (for PostgreSQL)
    """
    try:
        from flask import current_app

        from ..database import is_pool_initialized

        if current_app.config.get("USE_SQLITE_LOCALLY", False):
            return jsonify({"status": "ready", "mode": "sqlite"}), 200

        if is_pool_initialized():
            return jsonify({"status": "ready", "mode": "postgres"}), 200
        else:
            return jsonify(
                {
                    "status": "not_ready",
                    "reason": "Database pool not initialized",
                }
            ), 503

    except Exception as e:
        return jsonify(
            {
                "status": "not_ready",
                "error": str(e),
            }
        ), 503


@health_bp.route("/health/live", methods=["GET"])
def liveness_check() -> tuple[Any, int]:
    """
    Liveness check for Kubernetes/container orchestration.
    Returns 200 if the application is alive (even if not ready).

    This should always return 200 as long as the Python process is running.
    """
    return jsonify(
        {
            "status": "alive",
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
    ), 200


@health_bp.route("/health/db", methods=["GET"])
def database_check() -> tuple[Any, int]:
    """
    Database-specific health check.
    Tests actual database connectivity with a simple query.
    """
    try:
        from ..database.db_pool import get_db_connection, get_pool_stats

        conn, db_type = get_db_connection()
        cursor = conn.cursor()

        # Execute a simple query
        cursor.execute("SELECT 1 as test")
        cursor.fetchone()
        cursor.close()

        return jsonify(
            {
                "status": "healthy",
                "db_type": db_type,
                "test_query": "passed",
                "pool_stats": get_pool_stats(),
            }
        ), 200

    except RuntimeError as e:
        return jsonify(
            {
                "status": "unavailable",
                "error": str(e),
                "note": "Database pool not initialized",
            }
        ), 503
    except Exception as e:
        return jsonify(
            {
                "status": "unhealthy",
                "error": str(e),
            }
        ), 503


@health_bp.route("/health/metrics", methods=["GET"])
def metrics_endpoint() -> tuple[Any, int]:
    """
    Performance metrics endpoint.

    Returns aggregated metrics from:
    - Query Profiler (slow queries, avg time, p95)
    - Cache Manager (hit rate, misses)
    - Service Container (registered services)
    - Event Bus (emitted events, handler count)
    """
    metrics: dict[str, Any] = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }

    # Query Profiler stats
    try:
        from ..common.query_profiler import QueryProfiler

        metrics["queries"] = QueryProfiler.get_stats_summary()
    except Exception:
        metrics["queries"] = {"status": "unavailable"}

    # Cache Manager stats
    try:
        from flask import current_app

        cache_mgr = getattr(current_app, "cache_manager", None)
        if cache_mgr:
            metrics["cache"] = cache_mgr.get_stats()
        else:
            metrics["cache"] = {"status": "not_configured"}
    except Exception:
        metrics["cache"] = {"status": "unavailable"}

    # Service Container info
    try:
        from ..core.container import get_container

        container = get_container()
        services = container.registered_services()
        metrics["container"] = {
            "total_services": len(services),
            "services": services,
        }
    except Exception:
        metrics["container"] = {"status": "not_initialized"}

    # Event Bus stats
    try:
        from ..core.container import get_container

        container = get_container()
        if container.has("event_bus"):
            event_bus = container.resolve("event_bus")
            metrics["events"] = event_bus.get_stats()
        else:
            metrics["events"] = {"status": "not_registered"}
    except Exception:
        metrics["events"] = {"status": "unavailable"}

    return jsonify(metrics), 200


@health_bp.route("/health/cache/refresh", methods=["POST"])
def cache_refresh_endpoint() -> tuple[Any, int]:
    """
    Refresh config cache on-demand.

    Reloads all cached configuration data (tags, status, motivos, etc.).
    Useful after manual DB changes or deployments.
    """
    try:
        from ..config.cache_warming import refresh_config_cache

        results = refresh_config_cache()
        return jsonify(
            {
                "status": "completed",
                "refreshed": results,
            }
        ), 200
    except Exception as e:
        return jsonify(
            {
                "status": "error",
                "error": str(e),
            }
        ), 500

