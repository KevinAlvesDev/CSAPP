"""
Health Check Endpoint
Provides system status for monitoring and load balancers
"""

from flask import Blueprint, jsonify

health_bp = Blueprint("health", __name__)


@health_bp.route("/health", methods=["GET"])
def health_check():
    """
    Health check endpoint that verifies:
    - Application is running
    - Database connection is working
    - Redis connection is working (if configured)

    Returns:
        200: All systems operational
        503: Service unavailable (one or more checks failed)
    """
    from ..database.db_pool import get_db_connection

    health_status = {"status": "healthy", "checks": {}}

    all_healthy = True

    # Check database connection
    try:
        conn, db_type = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        cursor.close()

        health_status["checks"]["database"] = {"status": "healthy", "type": db_type}
    except Exception as e:
        all_healthy = False
        health_status["checks"]["database"] = {"status": "unhealthy", "error": str(e)}

    # Check Redis connection (if configured)
    try:
        from ..config.cache_config import cache

        if cache and hasattr(cache, "cache"):
            # Try to set and get a test value
            cache.set("health_check", "ok", timeout=5)
            value = cache.get("health_check")

            if value == "ok":
                health_status["checks"]["redis"] = {"status": "healthy"}
            else:
                all_healthy = False
                health_status["checks"]["redis"] = {"status": "unhealthy", "error": "Cache test failed"}
    except Exception:
        # Redis is optional, so don't fail health check if not configured
        health_status["checks"]["redis"] = {"status": "not_configured", "note": "Redis not available or not configured"}

    # Set overall status
    if not all_healthy:
        health_status["status"] = "unhealthy"
        return jsonify(health_status), 503

    return jsonify(health_status), 200


@health_bp.route("/health/ready", methods=["GET"])
def readiness_check():
    """
    Readiness check for Kubernetes/container orchestration.
    Returns 200 if the application is ready to serve traffic.
    """
    # For now, same as health check
    # Can be extended with more specific readiness criteria
    return health_check()


@health_bp.route("/health/live", methods=["GET"])
def liveness_check():
    """
    Liveness check for Kubernetes/container orchestration.
    Returns 200 if the application is alive (even if not ready).
    """
    return jsonify({"status": "alive"}), 200
