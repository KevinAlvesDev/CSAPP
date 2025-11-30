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

from flask import Blueprint, request, jsonify, g
from ..blueprints.auth import login_required
from ..constants import PERFIS_COM_GESTAO
from ..db import query_db, execute_db
from ..core.extensions import limiter
from ..config.logging_config import api_logger
from flask_limiter.util import get_remote_address
from ..security.api_security import validate_api_origin
from ..domain.hierarquia_service import get_hierarquia_implantacao
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

        # Normalizar datas para strings ISO (YYYY-MM-DD) no payload
        def iso_date(val):
            try:
                from ..common.utils import format_date_iso_for_json
                return format_date_iso_for_json(val, only_date=True)
            except Exception:
                return None

        impl['data_criacao'] = iso_date(impl.get('data_criacao'))
        impl['data_inicio_efetivo'] = iso_date(impl.get('data_inicio_efetivo'))
        impl['data_inicio_producao'] = iso_date(impl.get('data_inicio_producao'))
        impl['data_final_implantacao'] = iso_date(impl.get('data_final_implantacao'))

        # Migrado para estrutura hierárquica (fases -> grupos -> tarefas_h -> subtarefas_h)
        # DEPRECATED: A tabela 'tarefas' (estrutura antiga) não é mais usada
        hierarquia = get_hierarquia_implantacao(impl_id)

        return jsonify({
            'ok': True,
            'data': {
                'implantacao': impl,
                'hierarquia': hierarquia
            }
        })

    except Exception as e:
        api_logger.error(f"Error getting implantacao {impl_id}: {e}")
        return jsonify({'ok': False, 'error': str(e)}), 500


