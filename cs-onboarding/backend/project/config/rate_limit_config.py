"""
Rate Limiting Configuration
Protects the application from abuse and DDoS attacks
"""

import os

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = None


def init_rate_limiter(app):
    """
    Initialize rate limiting for the application.

    Uses Redis if available, otherwise falls back to memory storage.
    """
    global limiter

    # Check if Redis is available
    redis_url = os.environ.get("REDIS_URL")

    if redis_url:
        # Use Redis for distributed rate limiting
        storage_uri = redis_url
        app.logger.info("Rate limiter initialized with Redis backend")
    else:
        # Fallback to memory storage (not recommended for production)
        storage_uri = "memory://"
        app.logger.warning("Rate limiter using memory storage - not suitable for multiple workers")

    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        storage_uri=storage_uri,
        default_limits=["200 per day", "50 per hour"],
        storage_options={"socket_connect_timeout": 30},
        strategy="fixed-window",
        headers_enabled=True,
    )

    # Custom error handler for rate limit exceeded
    @app.errorhandler(429)
    def ratelimit_handler(e):
        from flask import jsonify, request

        if request.path.startswith("/api/"):
            return jsonify(
                {
                    "ok": False,
                    "error": "Limite de requisições excedido. Tente novamente mais tarde.",
                    "error_type": "rate_limit_exceeded",
                }
            ), 429
        else:
            from flask import render_template

            return render_template("error.html", error="Muitas requisições. Por favor, aguarde um momento."), 429

    return limiter
