# project/blueprints/api_v1.py
# API v1 - Versão estável da API

"""
API v1 - Endpoints versionados

Esta é a primeira versão estável da API.
Mudanças breaking devem ser feitas em uma nova versão (v2, v3, etc).

Endpoints disponíveis:
- GET  /api/v1/implantacoes - Lista implantações
- GET  /api/v1/implantacoes/<id> - Detalhes de uma implantação
- POST /api/v1/implantacoes/<id>/tarefas/<tarefa_id>/toggle - Toggle tarefa
- POST /api/v1/implantacoes/<id>/tarefas/<tarefa_id>/comentarios - Adicionar comentário
"""

from flask import Blueprint, request, jsonify, g, current_app
from ..blueprints.auth import login_required
from ..db import query_db, execute_db
from ..extensions import limiter
from ..validation import validate_integer, sanitize_string, ValidationError
from ..logging_config import api_logger
from flask_limiter.util import get_remote_address


api_v1_bp = Blueprint('api_v1', __name__, url_prefix='/api/v1')


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
        
        # Paginação
        try:
            page = int(request.args.get('page', 1))
            per_page = int(request.args.get('per_page', 50))
            per_page = min(per_page, 200)  # Máximo 200 por página
        except (TypeError, ValueError):
            page = 1
            per_page = 50
        
        offset = (page - 1) * per_page
        
        # Query base
        query = """
            SELECT i.*, p.nome as cs_nome
            FROM implantacoes i
            LEFT JOIN perfil_usuario p ON i.usuario_cs = p.usuario
            WHERE i.usuario_cs = %s
        """
        args = [user_email]
        
        # Filtro de status
        if status_filter:
            query += " AND i.status = %s"
            args.append(status_filter)
        
        # Ordenação e paginação
        query += " ORDER BY i.data_criacao DESC LIMIT %s OFFSET %s"
        args.extend([per_page, offset])
        
        implantacoes = query_db(query, tuple(args)) or []
        
        # Total para paginação
        count_query = "SELECT COUNT(*) as total FROM implantacoes WHERE usuario_cs = %s"
        count_args = [user_email]
        if status_filter:
            count_query += " AND status = %s"
            count_args.append(status_filter)
        
        total_result = query_db(count_query, tuple(count_args), one=True)
        total = total_result.get('total', 0) if total_result else 0
        
        return jsonify({
            'ok': True,
            'data': implantacoes,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': (total + per_page - 1) // per_page
            }
        })
        
    except Exception as e:
        api_logger.error(f"Error listing implantacoes: {e}")
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
        
        # Busca implantação
        impl = query_db(
            """SELECT i.*, p.nome as cs_nome
               FROM implantacoes i
               LEFT JOIN perfil_usuario p ON i.usuario_cs = p.usuario
               WHERE i.id = %s AND i.usuario_cs = %s""",
            (impl_id, user_email),
            one=True
        )
        
        if not impl:
            return jsonify({'ok': False, 'error': 'Implantação não encontrada'}), 404
        
        # Busca tarefas
        tarefas = query_db(
            "SELECT * FROM tarefas WHERE implantacao_id = %s ORDER BY tarefa_pai, ordem",
            (impl_id,)
        ) or []
        
        return jsonify({
            'ok': True,
            'data': {
                'implantacao': impl,
                'tarefas': tarefas
            }
        })
        
    except Exception as e:
        api_logger.error(f"Error getting implantacao {impl_id}: {e}")
        return jsonify({'ok': False, 'error': str(e)}), 500

