"""
Blueprint para RISC (Risk and Incident Sharing and Coordination)
Endpoint para receber eventos de segurança do Google
"""

from flask import Blueprint, request, jsonify
from ..config.logging_config import get_logger
from ..domain.risc_service import process_security_event

risc_bp = Blueprint('risc', __name__, url_prefix='/risc')
risc_logger = get_logger('risc')


@risc_bp.route('/events', methods=['POST'])
def receive_security_event():
    """
    Endpoint para receber eventos de segurança do Google.
    
    O Google envia eventos de segurança como tokens JWT no corpo da requisição.
    Este endpoint valida o token e processa o evento.
    
    Rota: POST /risc/events
    
    Body (application/x-www-form-urlencoded):
        SET: Token JWT do evento de segurança
        
    Returns:
        202 Accepted: Evento recebido e processado
        400 Bad Request: Token ausente ou inválido
        500 Internal Server Error: Erro ao processar evento
    """
    try:
        # O Google envia o token no campo 'SET' (Security Event Token)
        token = request.form.get('SET') or request.json.get('SET') if request.is_json else None
        
        if not token:
            risc_logger.warning("Evento de segurança recebido sem token")
            return jsonify({
                'error': 'Token ausente',
                'message': 'O campo SET é obrigatório'
            }), 400
        
        risc_logger.info("Evento de segurança recebido do Google")
        
        # Processar evento
        result = process_security_event(token)
        
        if result['status'] == 'error':
            risc_logger.error(f"Erro ao processar evento: {result['message']}")
            return jsonify(result), 400
        
        risc_logger.info(f"Evento processado com sucesso: {result.get('event_type')}")
        
        # Retornar 202 Accepted (padrão RISC)
        return jsonify(result), 202
        
    except Exception as e:
        risc_logger.error(f"Erro inesperado ao processar evento de segurança: {e}", exc_info=True)
        return jsonify({
            'error': 'Erro interno',
            'message': 'Erro ao processar evento de segurança'
        }), 500


@risc_bp.route('/status', methods=['GET'])
def risc_status():
    """
    Endpoint de status para verificar se o receptor RISC está funcionando.
    
    Rota: GET /risc/status
    
    Returns:
        200 OK: Receptor está funcionando
    """
    return jsonify({
        'status': 'ok',
        'message': 'RISC endpoint is operational',
        'endpoint': '/risc/events'
    }), 200
