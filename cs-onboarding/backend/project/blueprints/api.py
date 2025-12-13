
import json

from flask import Blueprint, g, jsonify, make_response, render_template, request
from decimal import Decimal

from ..blueprints.auth import login_required

# Importar cache para invalidação
try:
    from ..config.cache_config import cache
except ImportError:
    cache = None


from flask_limiter.util import get_remote_address
from sqlalchemy.exc import OperationalError

from ..common.utils import format_date_iso_for_json
from ..common.validation import ValidationError, validate_integer
from ..config.logging_config import api_logger
from ..constants import PERFIS_COM_GESTAO
from ..core.extensions import limiter
from ..db import execute_db, logar_timeline, query_db
from ..domain.implantacao_service import _get_progress
from ..domain.task_definitions import TASK_TIPS
from ..security.api_security import validate_api_origin

api_bp = Blueprint('api', __name__, url_prefix='/api')


@api_bp.before_request
def _api_origin_guard():
    return validate_api_origin(lambda: None)()


@api_bp.route('/progresso_implantacao/<int:impl_id>', methods=['GET'])
@validate_api_origin
def progresso_implantacao(impl_id):
    try:
        impl_id = validate_integer(impl_id, min_value=1)
    except ValidationError as e:
        return jsonify({'ok': False, 'error': f'ID inválido: {str(e)}'}), 400
    try:
        pct, total, done = _get_progress(impl_id)
        return jsonify({'ok': True, 'progresso': pct, 'total': total, 'concluidas': done})
    except Exception as e:
        api_logger.error(f"Erro ao obter progresso da implantação {impl_id}: {e}", exc_info=True)
        return jsonify({'ok': False, 'error': 'Erro interno'}), 500




@api_bp.route('/implantacao/<int:impl_id>/timeline', methods=['GET'])
@login_required
@validate_api_origin
@limiter.limit("200 per minute", key_func=lambda: g.user_email or get_remote_address())
def get_timeline(impl_id):
    try:
        impl_id = validate_integer(impl_id, min_value=1)
    except ValidationError as e:
        return jsonify({'ok': False, 'error': f'ID inválido: {str(e)}'}), 400

    page = request.args.get('page', type=int) or 1
    per_page = request.args.get('per_page', type=int) or 50
    if per_page > 200:
        per_page = 200
    types_param = request.args.get('types', '')
    q = request.args.get('q', '')
    dt_from = request.args.get('from', '')
    dt_to = request.args.get('to', '')

    where = ["tl.implantacao_id = %s"]
    params = [impl_id]
    if types_param:
        types = [t.strip() for t in types_param.split(',') if t.strip()]
        if types:
            where.append("tl.tipo_evento = ANY(%s)")
            params.append(types)
    if q:
        where.append("tl.detalhes ILIKE %s")
        params.append(f"%{q}%")
    if dt_from:
        where.append("tl.data_criacao >= %s")
        params.append(dt_from)
    if dt_to:
        where.append("tl.data_criacao <= %s")
        params.append(dt_to)

    offset = (page - 1) * per_page

    sql = f"""
        SELECT tl.id, tl.implantacao_id, tl.usuario_cs, tl.tipo_evento, tl.detalhes, tl.data_criacao,
               COALESCE(p.nome, tl.usuario_cs) as usuario_nome
        FROM timeline_log tl
        LEFT JOIN perfil_usuario p ON tl.usuario_cs = p.usuario
        WHERE {' AND '.join(where)}
        ORDER BY tl.data_criacao DESC
        LIMIT %s OFFSET %s
    """
    params_with_pagination = params + [per_page, offset]
    try:
        rows = query_db(sql, tuple(params_with_pagination)) or []
        items = []
        for r in rows:
            d = dict(r)
            dt = d.get('data_criacao')
            d['data_criacao'] = dt.isoformat() if hasattr(dt, 'isoformat') else str(dt)
            items.append(d)
        return jsonify({'ok': True, 'logs': items, 'pagination': {'page': page, 'per_page': per_page}})
    except Exception as e:
        api_logger.error(f"Erro ao buscar timeline da implantação {impl_id}: {e}", exc_info=True)
        return jsonify({'ok': False, 'error': 'Erro interno ao buscar timeline'}), 500


@api_bp.route('/implantacao/<int:impl_id>/timeline/export', methods=['GET'])
@login_required
@validate_api_origin
@limiter.limit("30 per minute", key_func=lambda: g.user_email or get_remote_address())
def export_timeline(impl_id):
    try:
        impl_id = validate_integer(impl_id, min_value=1)
    except ValidationError as e:
        return jsonify({'ok': False, 'error': f'ID inválido: {str(e)}'}), 400

    types_param = request.args.get('types', '')
    q = request.args.get('q', '')
    dt_from = request.args.get('from', '')
    dt_to = request.args.get('to', '')

    where = ["tl.implantacao_id = %s"]
    params = [impl_id]
    if types_param:
        types = [t.strip() for t in types_param.split(',') if t.strip()]
        if types:
            where.append("tl.tipo_evento = ANY(%s)")
            params.append(types)
    if q:
        where.append("tl.detalhes ILIKE %s")
        params.append(f"%{q}%")
    if dt_from:
        where.append("tl.data_criacao >= %s")
        params.append(dt_from)
    if dt_to:
        where.append("tl.data_criacao <= %s")
        params.append(dt_to)

    sql = f"""
        SELECT tl.data_criacao, tl.tipo_evento, COALESCE(p.nome, tl.usuario_cs) as usuario_nome, tl.detalhes
        FROM timeline_log tl
        LEFT JOIN perfil_usuario p ON tl.usuario_cs = p.usuario
        WHERE {' AND '.join(where)}
        ORDER BY tl.data_criacao DESC
    """
    try:
        rows = query_db(sql, tuple(params)) or []
        import io, csv
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['data_criacao', 'tipo_evento', 'usuario', 'detalhes'])
        for r in rows:
            dc = r['data_criacao']
            dc_str = dc.isoformat() if hasattr(dc, 'isoformat') else str(dc)
            writer.writerow([dc_str, r.get('tipo_evento', ''), r.get('usuario_nome', ''), r.get('detalhes', '')])
        resp = make_response(output.getvalue())
        resp.headers['Content-Type'] = 'text/csv; charset=utf-8'
        resp.headers['Content-Disposition'] = f'attachment; filename="timeline_implantacao_{impl_id}.csv"'
        return resp
    except Exception as e:
        api_logger.error(f"Erro ao exportar timeline da implantação {impl_id}: {e}", exc_info=True)
        return jsonify({'ok': False, 'error': 'Erro interno ao exportar timeline'}), 500


@api_bp.route('/consultar_empresa', methods=['GET'])
@login_required
@validate_api_origin
@limiter.limit("20 per minute", key_func=lambda: g.user_email or get_remote_address())
def consultar_empresa():

    """
    Endpoint para consultar dados da empresa no banco externo (OAMD) via ID Favorecido (codigofinanceiro).
    """
    raw_id = request.args.get('id_favorecido')
    infra_req = request.args.get('infra') or request.args.get('zw') or request.args.get('infra_code')

    id_favorecido = None
    if raw_id:
        try:
            import re as _re
            digits_only = ''.join(_re.findall(r"\d+", str(raw_id)))
            if digits_only:
                id_favorecido = validate_integer(digits_only, min_value=1)
        except Exception:
            id_favorecido = None

    from ..domain.external_service import consultar_empresa_oamd
    result = consultar_empresa_oamd(id_favorecido, infra_req)
    
    status_code = result.pop('status_code', 200)
    return jsonify(result), status_code



