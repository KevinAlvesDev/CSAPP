

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
from ..constants import PERFIS_COM_GESTAO
from ..db import query_db, execute_db
from ..core.extensions import limiter
from ..common.validation import validate_integer, sanitize_string, ValidationError
from ..config.logging_config import api_logger
from flask_limiter.util import get_remote_address
from ..security.api_security import validate_api_origin
from datetime import datetime, date


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

        try:
            page = int(request.args.get('page', 1))
            per_page = int(request.args.get('per_page', 50))
            per_page = min(per_page, 200)                         
        except (TypeError, ValueError):
            page = 1
            per_page = 50
        
        offset = (page - 1) * per_page

        query = """
            SELECT i.*, p.nome as cs_nome
            FROM implantacoes i
            LEFT JOIN perfil_usuario p ON i.usuario_cs = p.usuario
            WHERE i.usuario_cs = %s
        """
        args = [user_email]

        if status_filter:
            query += " AND i.status = %s"
            args.append(status_filter)
        
        query += " ORDER BY i.data_criacao DESC LIMIT %s OFFSET %s"
        args.extend([per_page, offset])
        
        implantacoes = query_db(query, tuple(args)) or []

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
        
        is_manager = g.perfil and g.perfil.get('perfil_acesso') in PERFIS_COM_GESTAO
        if is_manager:
            impl = query_db(
                """SELECT i.*, p.nome as cs_nome
                   FROM implantacoes i
                   LEFT JOIN perfil_usuario p ON i.usuario_cs = p.usuario
                   WHERE i.id = %s""",
                (impl_id,),
                one=True
            )
        else:
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

@api_v1_bp.route('/implantacoes/<int:impl_id>/status/atrasada', methods=['POST'])
@login_required
@limiter.limit("50 per minute", key_func=lambda: g.user_email or get_remote_address())
def marcar_atrasada(impl_id):
    try:
        impl = query_db("SELECT status, data_inicio_efetivo, nome_empresa FROM implantacoes WHERE id = %s", (impl_id,), one=True)
        if not impl:
            return jsonify({'ok': False, 'error': 'Implantacao nao encontrada'}), 404
        status = impl.get('status')
        di = impl.get('data_inicio_efetivo')
        di_dt = None
        if isinstance(di, str):
            try:
                di_dt = datetime.fromisoformat(di.replace('Z', '+00:00'))
            except ValueError:
                try:
                    if '.' in di:
                        di_dt = datetime.strptime(di, '%Y-%m-%d %H:%M:%S.%f')
                    else:
                        di_dt = datetime.strptime(di, '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    try:
                        di_dt = datetime.strptime(di, '%Y-%m-%d')
                    except ValueError:
                        di_dt = None
        elif isinstance(di, date) and not isinstance(di, datetime):
            di_dt = datetime.combine(di, datetime.min.time())
        elif isinstance(di, datetime):
            di_dt = di
        if not di_dt:
            return jsonify({'ok': False, 'error': 'Data de inicio efetivo ausente'}), 400
        agora = datetime.now()
        agora_naive = agora.replace(tzinfo=None) if agora.tzinfo else agora
        inicio_naive = di_dt.replace(tzinfo=None) if di_dt.tzinfo else di_dt
        dias = (agora_naive - inicio_naive).days
        if dias > 25 and status == 'andamento':
            execute_db("UPDATE implantacoes SET status = 'atrasada' WHERE id = %s", (impl_id,))
            api_logger.info(f"Implantacao {impl_id} marcada como atrasada")
            return jsonify({'ok': True, 'status': 'atrasada', 'dias': dias})
        if dias <= 25 and status == 'atrasada':
            execute_db("UPDATE implantacoes SET status = 'andamento' WHERE id = %s", (impl_id,))
            api_logger.info(f"Implantacao {impl_id} revertida para andamento")
            return jsonify({'ok': True, 'status': 'andamento', 'dias': dias})
        return jsonify({'ok': True, 'status': status, 'dias': dias})
    except Exception as e:
        api_logger.error(f"Erro ao marcar atrasada: {e}", exc_info=True)
        return jsonify({'ok': False, 'error': 'Erro interno'}), 500

