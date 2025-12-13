"""
Decoradores e utilitários para tratamento de erros robusto
"""

import functools
from flask import jsonify, current_app
from ..config.logging_config import api_logger


def handle_api_errors(f):
    """
    Decorator para tratamento consistente de erros em endpoints de API.
    Captura exceções e retorna respostas JSON padronizadas.
    """
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except ValueError as e:
            # Erros de validação de negócio
            api_logger.warning(f"Validation error in {f.__name__}: {str(e)}")
            return jsonify({
                'ok': False,
                'error': str(e),
                'error_type': 'validation_error'
            }), 400
        except PermissionError as e:
            # Erros de permissão
            api_logger.warning(f"Permission denied in {f.__name__}: {str(e)}")
            return jsonify({
                'ok': False,
                'error': str(e) or 'Permissão negada',
                'error_type': 'permission_error'
            }), 403
        except FileNotFoundError as e:
            # Recurso não encontrado
            api_logger.warning(f"Resource not found in {f.__name__}: {str(e)}")
            return jsonify({
                'ok': False,
                'error': str(e) or 'Recurso não encontrado',
                'error_type': 'not_found'
            }), 404
        except ConnectionError as e:
            # Erros de conexão (banco, APIs externas)
            api_logger.error(f"Connection error in {f.__name__}: {str(e)}")
            return jsonify({
                'ok': False,
                'error': 'Erro de conexão. Tente novamente.',
                'error_type': 'connection_error'
            }), 503
        except TimeoutError as e:
            # Timeout
            api_logger.error(f"Timeout in {f.__name__}: {str(e)}")
            return jsonify({
                'ok': False,
                'error': 'Operação demorou muito. Tente novamente.',
                'error_type': 'timeout_error'
            }), 504
        except Exception as e:
            # Erro inesperado
            api_logger.error(f"Unexpected error in {f.__name__}: {str(e)}", exc_info=True)
            
            # Em desenvolvimento, mostrar erro completo
            if current_app.config.get('DEBUG'):
                return jsonify({
                    'ok': False,
                    'error': str(e),
                    'error_type': 'internal_error',
                    'debug_info': {
                        'function': f.__name__,
                        'exception_type': type(e).__name__
                    }
                }), 500
            
            # Em produção, mensagem genérica
            return jsonify({
                'ok': False,
                'error': 'Erro interno do servidor',
                'error_type': 'internal_error'
            }), 500
    
    return decorated_function


def handle_view_errors(f):
    """
    Decorator para tratamento de erros em views (HTML).
    Redireciona para páginas de erro apropriadas.
    """
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        from flask import flash, redirect, url_for, render_template
        
        try:
            return f(*args, **kwargs)
        except ValueError as e:
            flash(str(e), 'error')
            return redirect(url_for('main.dashboard'))
        except PermissionError as e:
            flash(str(e) or 'Você não tem permissão para acessar este recurso', 'error')
            return redirect(url_for('main.dashboard'))
        except FileNotFoundError as e:
            flash(str(e) or 'Recurso não encontrado', 'error')
            return redirect(url_for('main.dashboard'))
        except Exception as e:
            api_logger.error(f"Error in view {f.__name__}: {str(e)}", exc_info=True)
            
            if current_app.config.get('DEBUG'):
                # Em desenvolvimento, mostrar erro
                return render_template('error.html', error=str(e)), 500
            
            flash('Ocorreu um erro inesperado. Tente novamente.', 'error')
            return redirect(url_for('main.dashboard'))
    
    return decorated_function


def require_fields(*required_fields):
    """
    Decorator para validar campos obrigatórios em requisições JSON.
    
    Uso:
        @require_fields('nome', 'email')
        def minha_rota():
            ...
    """
    def decorator(f):
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            from flask import request, jsonify
            
            if not request.is_json:
                return jsonify({
                    'ok': False,
                    'error': 'Content-Type deve ser application/json'
                }), 400
            
            data = request.get_json()
            missing_fields = [field for field in required_fields if not data.get(field)]
            
            if missing_fields:
                return jsonify({
                    'ok': False,
                    'error': f'Campos obrigatórios ausentes: {", ".join(missing_fields)}',
                    'missing_fields': missing_fields
                }), 400
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator


def validate_pagination(max_per_page=100):
    """
    Decorator para validar e normalizar parâmetros de paginação.
    Adiciona 'page' e 'per_page' validados ao request.
    """
    def decorator(f):
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            from flask import request
            
            try:
                page = int(request.args.get('page', 1))
                per_page = int(request.args.get('per_page', 20))
                
                # Validações
                if page < 1:
                    page = 1
                if per_page < 1:
                    per_page = 20
                if per_page > max_per_page:
                    per_page = max_per_page
                
                # Adicionar ao request para uso na função
                request.validated_page = page
                request.validated_per_page = per_page
                
            except (ValueError, TypeError):
                request.validated_page = 1
                request.validated_per_page = 20
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator


class ValidationError(Exception):
    """Exceção customizada para erros de validação"""
    pass


class PermissionDeniedError(PermissionError):
    """Exceção customizada para erros de permissão"""
    pass


class ResourceNotFoundError(FileNotFoundError):
    """Exceção customizada para recursos não encontrados"""
    pass
