from flask import request


def init_security_headers(app):
    @app.after_request
    def set_security_headers(response):
        use_sqlite = app.config.get("USE_SQLITE_LOCALLY", False)
        is_production = not use_sqlite

        csp_directives = [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://unpkg.com",
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://fonts.googleapis.com",
            "font-src 'self' https://fonts.gstatic.com https://cdn.jsdelivr.net https://cdnjs.cloudflare.com",
            "img-src 'self' data: https: blob:",
            "connect-src 'self' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://unpkg.com",
            "frame-ancestors 'self'",  # Permite iframes do mesmo domínio
            "base-uri 'self'",
            "form-action 'self'",
        ]
        response.headers["Content-Security-Policy"] = "; ".join(csp_directives)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"  # Permite iframes do mesmo domínio
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        permissions = [
            "geolocation=()",
            "microphone=()",
            "camera=()",
            "payment=()",
            "usb=()",
            "magnetometer=()",
            "gyroscope=()",
            "accelerometer=()",
        ]
        response.headers["Permissions-Policy"] = ", ".join(permissions)

        if is_production:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"

        # Configurar Cache-Control baseado no tipo de conteúdo/rota
        if request.path.startswith("/static/"):
            # Arquivos estáticos: cache longo com revalidação (1 ano)
            # O cache-busting é feito via query string (?v=timestamp)
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        elif request.path.startswith("/api/") or request.path.startswith("/checklist/"):
            # Rotas de API: NUNCA cachear
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private, max-age=0"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
            # Adicionar timestamp para debugging de cache
            from datetime import datetime, timezone
            response.headers["X-Response-Time"] = datetime.now(timezone.utc).isoformat()
        elif response.content_type and "text/html" in response.content_type:
            # Páginas HTML dinâmicas: não cachear para garantir dados frescos
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        elif any(path in request.path for path in ["/login", "/perfil", "/management"]):
            # Rotas sensíveis específicas: garantir no-cache
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"

        return response

    app.logger.info("Security headers middleware initialized")


def init_rate_limiting_headers(app):
    @app.after_request
    def add_rate_limit_headers(response):
        from flask import g

        if hasattr(g, "rate_limit_info"):
            response.headers["X-RateLimit-Limit"] = str(g.rate_limit_info.get("limit", "N/A"))
            response.headers["X-RateLimit-Remaining"] = str(g.rate_limit_info.get("remaining", "N/A"))
            response.headers["X-RateLimit-Reset"] = str(g.rate_limit_info.get("reset", "N/A"))
        return response


def configure_cors(app):
    allowed_origins = app.config.get("CORS_ALLOWED_ORIGINS", [])
    if isinstance(allowed_origins, str):
        allowed_origins = [o.strip() for o in allowed_origins.split(",") if o.strip()]
    if allowed_origins:

        @app.after_request
        def add_cors_headers(response):
            origin = request.headers.get("Origin")
            if origin in allowed_origins:
                response.headers["Access-Control-Allow-Origin"] = origin
                response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
                response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-CSRFToken"
                response.headers["Access-Control-Allow-Credentials"] = "true"
            return response

        app.logger.info(f"CORS configured for origins: {allowed_origins}")
    else:
        app.logger.info("CORS not configured (default: same-origin only)")
