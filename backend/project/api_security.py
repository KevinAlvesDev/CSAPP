# backend/project/api_security.py
"""
Middleware de segurança para APIs REST.
Implementa validação de Origin/Referer para prevenir CSRF em APIs.
"""

from functools import wraps
from flask import request, jsonify, current_app
from urllib.parse import urlparse


def validate_api_origin(f):
    """
    Decorator para validar Origin/Referer em requisições de API.
    
    SEGURANÇA: Previne CSRF em APIs REST verificando se a requisição
    vem de uma origem confiável.
    
    Uso:
        @api_bp.route('/endpoint', methods=['POST'])
        @validate_api_origin
        def my_endpoint():
            ...
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Ignora validação para métodos seguros (GET, HEAD, OPTIONS)
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return f(*args, **kwargs)
        
        # Obtém Origin ou Referer
        origin = request.headers.get('Origin')
        referer = request.headers.get('Referer')
        
        # Se não tem nem Origin nem Referer, bloqueia
        if not origin and not referer:
            current_app.logger.warning(
                f'API request without Origin/Referer: {request.method} {request.path} '
                f'from {request.remote_addr}'
            )
            return jsonify({
                'ok': False,
                'error': 'Origin ou Referer header obrigatório'
            }), 403
        
        # Valida Origin/Referer contra lista de origens permitidas
        allowed_origins = _get_allowed_origins()
        
        # Verifica Origin
        if origin:
            if not _is_origin_allowed(origin, allowed_origins):
                current_app.logger.warning(
                    f'API request from unauthorized origin: {origin} '
                    f'for {request.method} {request.path}'
                )
                return jsonify({
                    'ok': False,
                    'error': 'Origin não autorizado'
                }), 403
        
        # Verifica Referer (se Origin não estiver presente)
        elif referer:
            referer_origin = _extract_origin_from_referer(referer)
            if not _is_origin_allowed(referer_origin, allowed_origins):
                current_app.logger.warning(
                    f'API request from unauthorized referer: {referer} '
                    f'for {request.method} {request.path}'
                )
                return jsonify({
                    'ok': False,
                    'error': 'Referer não autorizado'
                }), 403
        
        return f(*args, **kwargs)
    
    return decorated_function


def _get_allowed_origins():
    """
    Retorna lista de origens permitidas.
    
    Returns:
        Lista de origens permitidas (ex: ['http://localhost:5000', 'https://app.com'])
    """
    # Origens padrão (localhost para desenvolvimento)
    allowed = [
        'http://localhost:5000',
        'http://127.0.0.1:5000',
        'http://localhost:8000',
        'http://127.0.0.1:8000',
    ]
    
    # Adiciona origem de produção se configurada
    # Obtém do request.host_url ou de variável de ambiente
    if request.host_url:
        allowed.append(request.host_url.rstrip('/'))
    
    # Adiciona origens customizadas do .env (se configurado)
    custom_origins = current_app.config.get('CORS_ALLOWED_ORIGINS', '')
    if custom_origins:
        for origin in custom_origins.split(','):
            origin = origin.strip()
            if origin:
                allowed.append(origin)
    
    return allowed


def _is_origin_allowed(origin, allowed_origins):
    """
    Verifica se uma origem está na lista de permitidas.
    
    Args:
        origin: Origem a verificar (ex: 'http://localhost:5000')
        allowed_origins: Lista de origens permitidas
    
    Returns:
        True se permitida, False caso contrário
    """
    if not origin:
        return False
    
    # Normaliza origem (remove trailing slash)
    origin = origin.rstrip('/')
    
    # Verifica se está na lista
    for allowed in allowed_origins:
        if origin == allowed.rstrip('/'):
            return True
    
    return False


def _extract_origin_from_referer(referer):
    """
    Extrai a origem (scheme + host) de uma URL Referer.
    
    Args:
        referer: URL completa do Referer
    
    Returns:
        Origem extraída (ex: 'http://localhost:5000')
    """
    if not referer:
        return None
    
    try:
        parsed = urlparse(referer)
        return f"{parsed.scheme}://{parsed.netloc}"
    except Exception:
        return None

