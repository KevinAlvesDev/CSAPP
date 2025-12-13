"""
API v1 - Endpoints versionados

Esta é a primeira versão estável da API.
Mudanças breaking devem ser feitas em uma nova versão (v2, v3, etc).


Endpoints disponíveis:
- GET  /api/v1/implantacoes - Lista implantações
- GET  /api/v1/implantacoes/<id> - Detalhes de uma implantação
- GET  /api/v1/oamd/implantacoes/<id>/consulta - Consulta dados externos (OAMD)
- POST /api/v1/oamd/implantacoes/<id>/aplicar - Aplica dados externos
"""


from flask import Blueprint, g, jsonify, request
from flask_limiter.util import get_remote_address

from ..blueprints.auth import login_required
from ..config.logging_config import api_logger
from ..constants import PERFIS_COM_GESTAO
from ..core.extensions import limiter
from ..domain.implantacao_service import (
    listar_implantacoes,
    obter_implantacao_basica,
    consultar_dados_oamd,
    aplicar_dados_oamd
)
from ..security.api_security import validate_api_origin

api_v1_bp = Blueprint('api_v1', __name__, url_prefix='/api/v1')


@api_v1_bp.before_request
def _api_v1_origin_guard():
    return validate_api_origin(lambda: None)()


@api_v1_bp.route('/health', methods=['GET'])
def health():
    """Health check endpoint para API v1."""
    return jsonify({
        'status': 'ok',
        'version': 'v1',
        'api': 'CSAPP API v1'
    })


@api_v1_bp.route('/implantacoes', methods=['GET'])
@login_required
@limiter.limit("100 per minute", key_func=lambda: g.user_email or get_remote_address())
def list_implantacoes():
    """
    Lista implantações do usuário.

    Query params:
        - status: Filtrar por status (opcional)
        - page: Número da página (opcional, padrão 1)
        - per_page: Itens por página (opcional, padrão 50)

    Returns:
        JSON com lista de implantações
    """
    try:
        user_email = g.user_email
        status_filter = request.args.get('status')
        page = request.args.get('page', 1)
        per_page = request.args.get('per_page', 50)
        
        result = listar_implantacoes(
            user_email=user_email,
            status_filter=status_filter,
            page=page,
            per_page=per_page,
            is_admin=False 
        )

        return jsonify({
            'ok': True,
            **result
        })

    except Exception as e:
        api_logger.error(f"Error listing implantacoes: {e}", exc_info=True)
        return jsonify({'ok': False, 'error': str(e)}), 500


@api_v1_bp.route('/implantacoes/<int:impl_id>', methods=['GET'])
@login_required
@limiter.limit("100 per minute", key_func=lambda: g.user_email or get_remote_address())
def get_implantacao(impl_id):
    """
    Retorna detalhes de uma implantação.

    Args:
        impl_id: ID da implantação

    Returns:
        JSON com detalhes da implantação
    """
    try:
        user_email = g.user_email
        is_manager = g.perfil and g.perfil.get('perfil_acesso') in PERFIS_COM_GESTAO
        
        data = obter_implantacao_basica(impl_id, user_email, is_manager)

        if not data:
            return jsonify({'ok': False, 'error': 'Implantação não encontrada'}), 404

        return jsonify({
            'ok': True,
            'data': data
        })

    except Exception as e:
        api_logger.error(f"Error getting implantacao {impl_id}: {e}", exc_info=True)
        return jsonify({'ok': False, 'error': str(e)}), 500


@api_v1_bp.route('/oamd/implantacoes/<int:impl_id>/consulta', methods=['GET'])
@login_required
@limiter.limit("60 per minute", key_func=lambda: g.user_email or get_remote_address())
def consultar_oamd_implantacao(impl_id):
    try:
        user_email = g.user_email 
        result = consultar_dados_oamd(impl_id, user_email)
        
        return jsonify({'ok': True, 'data': result})

    except ValueError as ve:
        return jsonify({'ok': False, 'error': str(ve)}), 404
    except Exception as e:
        api_logger.error(f"Erro ao consultar OAMD para implantação {impl_id}: {e}", exc_info=True)
        return jsonify({'ok': False, 'error': 'Erro interno na consulta ao OAMD'}), 500


@api_v1_bp.route('/oamd/implantacoes/<int:impl_id>/aplicar', methods=['POST'])
@login_required
@limiter.limit("60 per minute", key_func=lambda: g.user_email or get_remote_address())
def aplicar_oamd_implantacao(impl_id):
    try:
        user_email = g.user_email 
        
        # Reaproveitar a consulta externa para obter os dados frescos
        info = consultar_dados_oamd(impl_id, user_email)
        
        persist = info.get('persistibles') or {}
        derived = info.get('derived') or {}
        
        updates = {}
        if persist.get('id_favorecido'): updates['id_favorecido'] = str(persist['id_favorecido'])
        if persist.get('chave_oamd'): updates['chave_oamd'] = str(persist['chave_oamd'])
        if derived.get('informacao_infra'): updates['informacao_infra'] = str(derived['informacao_infra'])
        if derived.get('tela_apoio_link'): updates['tela_apoio_link'] = str(derived['tela_apoio_link'])
        
        result = aplicar_dados_oamd(impl_id, user_email, updates)
        
        return jsonify({
            'ok': True, 
            'updated': result.get('updated'), 
            'fields': result.get('fields')
        })
        
    except ValueError as ve:
        return jsonify({'ok': False, 'error': str(ve)}), 404
    except Exception as e:
        api_logger.error(f"Erro ao aplicar dados OAMD na implantação {impl_id}: {e}", exc_info=True)
        return jsonify({'ok': False, 'error': 'Erro interno ao aplicar dados'}), 500
