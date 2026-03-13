from functools import wraps
from flask import flash, redirect, request, url_for, g
from .exceptions import CSAPPException
from ..config.logging_config import app_logger

def handle_view_errors(dashboard_endpoint=None):
    """
    Decorator para tratar exceções em funções de 'actions' ou instâncias de views.
    Se for uma requisição JSON/API, as exceções serão capturadas pelo errorhandler global.
    Se for uma requisição HTML, este decorator garante o flash e o redirect correto.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except CSAPPException as e:
                # O errorhandler global já cuida disso se for JSON.
                # Para views normais, facilitamos o redirect aqui se necessário,
                # ou apenas re-lançamos para o global handler.
                raise
            except Exception as e:
                # Captura erros inesperados para evitar 500 genérico sem log detalhado
                app_logger.error(f"Erro inesperado em {f.__name__}: {e}", exc_info=True)
                
                if request.path.startswith("/api") or request.is_json:
                    raise
                
                flash(f"Ocorreu um erro inesperado: {str(e)}", "error")
                endpoint = dashboard_endpoint or "main.dashboard"
                return redirect(url_for(endpoint, context=getattr(g, "modulo_atual", None)))
        return decorated_function
    return decorator
