# backend/project/security_middleware.py
"""
Middleware de segurança para adicionar headers de proteção.
Implementa CSP, HSTS, X-Frame-Options, etc.
"""

from flask import current_app


def init_security_headers(app):
    """
    Inicializa headers de segurança na aplicação.
    Adiciona proteções contra XSS, clickjacking, MIME sniffing, etc.
    """
    
    @app.after_request
    def set_security_headers(response):
        """
        Adiciona headers de segurança em todas as respostas.
        """
        # Só aplica em produção (quando não estiver usando SQLite)
        use_sqlite = app.config.get('USE_SQLITE_LOCALLY', False)
        is_production = not use_sqlite
        
        # Content Security Policy (CSP)
        # Permite scripts inline (necessário para alguns templates), mas restringe origens
        csp_directives = [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' cdn.jsdelivr.net cdnjs.cloudflare.com",
            "style-src 'self' 'unsafe-inline' cdn.jsdelivr.net cdnjs.cloudflare.com fonts.googleapis.com",
            "font-src 'self' fonts.gstatic.com cdnjs.cloudflare.com",
            "img-src 'self' data: https: blob:",
            "connect-src 'self'",
            "frame-ancestors 'none'",
            "base-uri 'self'",
            "form-action 'self'"
        ]
        response.headers['Content-Security-Policy'] = "; ".join(csp_directives)
        
        # X-Content-Type-Options: previne MIME sniffing
        response.headers['X-Content-Type-Options'] = 'nosniff'
        
        # X-Frame-Options: previne clickjacking
        response.headers['X-Frame-Options'] = 'DENY'
        
        # X-XSS-Protection: proteção adicional contra XSS (legacy, mas ainda útil)
        response.headers['X-XSS-Protection'] = '1; mode=block'
        
        # Referrer-Policy: controla informações de referrer
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # Permissions-Policy: controla features do browser
        permissions = [
            "geolocation=()",
            "microphone=()",
            "camera=()",
            "payment=()",
            "usb=()",
            "magnetometer=()",
            "gyroscope=()",
            "accelerometer=()"
        ]
        response.headers['Permissions-Policy'] = ", ".join(permissions)
        
        # HSTS (HTTP Strict Transport Security) - apenas em produção
        if is_production:
            # max-age=31536000 = 1 ano
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'
        
        # Cache-Control para páginas sensíveis (login, perfil, etc)
        if any(path in response.request.path for path in ['/login', '/perfil', '/management']):
            response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, private'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
        
        return response
    
    app.logger.info("Security headers middleware initialized")


def init_rate_limiting_headers(app):
    """
    Adiciona headers informativos sobre rate limiting.
    """
    
    @app.after_request
    def add_rate_limit_headers(response):
        """
        Adiciona headers de rate limiting quando aplicável.
        """
        # Verifica se há informações de rate limit no contexto
        from flask import g
        
        if hasattr(g, 'rate_limit_info'):
            response.headers['X-RateLimit-Limit'] = str(g.rate_limit_info.get('limit', 'N/A'))
            response.headers['X-RateLimit-Remaining'] = str(g.rate_limit_info.get('remaining', 'N/A'))
            response.headers['X-RateLimit-Reset'] = str(g.rate_limit_info.get('reset', 'N/A'))
        
        return response


def configure_cors(app):
    """
    Configura CORS de forma segura (se necessário).
    Por padrão, não permite CORS para segurança.
    """
    allowed_origins = app.config.get('CORS_ALLOWED_ORIGINS', [])
    
    if allowed_origins:
        @app.after_request
        def add_cors_headers(response):
            origin = request.headers.get('Origin')
            if origin in allowed_origins:
                response.headers['Access-Control-Allow-Origin'] = origin
                response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
                response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
                response.headers['Access-Control-Allow-Credentials'] = 'true'
            return response
        
        app.logger.info(f"CORS configured for origins: {allowed_origins}")
    else:
        app.logger.info("CORS not configured (default: same-origin only)")

