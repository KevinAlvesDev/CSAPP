"""
Middleware de monitoramento de performance.
Registra requisições lentas para identificar gargalos.
"""

import time
from flask import g, request
from ..config.logging_config import get_logger

logger = get_logger('performance')


def init_performance_monitoring(app):
    """
    Inicializa o monitoramento de performance.
    Registra requisições que demoram mais de 1 segundo.
    """
    
    @app.before_request
    def start_timer():
        """Inicia o timer antes de processar a requisição."""
        g.start_time = time.time()
    
    @app.after_request
    def log_slow_requests(response):
        """
        Registra requisições lentas após o processamento.
        Considera lenta qualquer requisição > 1 segundo.
        """
        if hasattr(g, 'start_time'):
            elapsed = time.time() - g.start_time
            
            # Ignorar rotas estáticas
            if request.path.startswith('/static/'):
                return response
            
            # Log de requisições lentas (> 1 segundo)
            if elapsed > 1.0:
                logger.warning(
                    f"Slow request: {request.method} {request.path} "
                    f"took {elapsed:.2f}s | "
                    f"User: {getattr(g, 'user_email', 'anonymous')}"
                )
            
            # Log de requisições muito lentas (> 3 segundos)
            elif elapsed > 3.0:
                logger.error(
                    f"VERY slow request: {request.method} {request.path} "
                    f"took {elapsed:.2f}s | "
                    f"User: {getattr(g, 'user_email', 'anonymous')}"
                )
            
            # Debug: log de todas as requisições em desenvolvimento
            elif app.config.get('DEBUG'):
                logger.debug(
                    f"{request.method} {request.path} took {elapsed:.3f}s"
                )
        
        return response
    
    app.logger.info("Performance monitoring initialized")
