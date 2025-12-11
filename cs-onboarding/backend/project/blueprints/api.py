
import json

from flask import Blueprint, g, jsonify, make_response, render_template, request

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

@api_bp.route('/toggle_subtarefa_h/<int:sub_id>', methods=['POST'])
@login_required
@validate_api_origin
@limiter.limit("100 per minute", key_func=lambda: g.user_email or get_remote_address())
def toggle_subtarefa_h(sub_id):
    usuario_cs_email = g.user_email

    try:
        sub_id = validate_integer(sub_id, min_value=1)
    except ValidationError as e:
        return jsonify({'ok': False, 'error': f'ID inválido: {str(e)}'}), 400

    try:
        row = query_db(
            """
            SELECT ci.id as sub_id, ci.completed as concluido, i.id as implantacao_id, i.usuario_cs, i.status
            FROM checklist_items ci
            JOIN implantacoes i ON ci.implantacao_id = i.id
            WHERE ci.id = %s AND ci.tipo_item = 'subtarefa'
            """,
            (sub_id,), one=True
        )

        if not row:
            return jsonify({'ok': False, 'error': 'Subtarefa não encontrada'}), 404

        is_owner = row.get('usuario_cs') == usuario_cs_email
        is_manager = g.perfil and g.perfil.get('perfil_acesso') in PERFIS_COM_GESTAO

        if not (is_owner or is_manager):
            return jsonify({'ok': False, 'error': 'Permissão negada.'}), 403

        if row.get('status') in ['finalizada', 'parada', 'cancelada']:
            return jsonify({'ok': False, 'error': 'Implantação bloqueada para alterações.'}), 400

        request_data = request.get_json(silent=True) or {}
        concluido_desejado = request_data.get('concluido', None)

        if concluido_desejado is None:
            novo = 0 if row.get('concluido') else 1
        else:
            novo = 1 if bool(concluido_desejado) else 0

        from datetime import datetime
        if novo:
            execute_db("UPDATE checklist_items SET completed = %s, data_conclusao = %s WHERE id = %s", (True, datetime.now(), sub_id))
        else:
            execute_db("UPDATE checklist_items SET completed = %s, data_conclusao = NULL WHERE id = %s", (False, sub_id))

        detalhe = f"Subtarefa {sub_id}: {'Concluída' if novo else 'Não Concluída'}."
        logar_timeline(row['implantacao_id'], usuario_cs_email, 'tarefa_alterada', detalhe)

        tarefa_atualizada = query_db("SELECT id, title as nome, completed as concluido FROM checklist_items WHERE id = %s AND tipo_item = 'subtarefa'", (sub_id,), one=True)
        implantacao_info = query_db("SELECT nome_empresa, email_responsavel FROM implantacoes WHERE id = %s", (row['implantacao_id'],), one=True) or {}

        impl_id = row['implantacao_id']
        if cache:
            cache_key = f'progresso_impl_{impl_id}'
            cache.delete(cache_key)

        novo_prog, _, _ = _get_progress(impl_id)
        tarefa_concluida = bool(tarefa_atualizada.get('concluido'))

        if request.headers.get('HX-Request') == 'true':
            tarefa_payload = {
                'id': tarefa_atualizada.get('id'),
                'tarefa_filho': tarefa_atualizada.get('nome'),
                'tag': '',
                'concluida': tarefa_concluida,
                'comentarios': [],
                'toggle_url': f"/api/toggle_subtarefa_h/{tarefa_atualizada.get('id')}"
            }
            implantacao = {
                'nome_empresa': implantacao_info.get('nome_empresa', ''),
                'email_responsavel': implantacao_info.get('email_responsavel', '')
            }
            item_html = render_template('partials/_task_item_wrapper.html', tarefa=tarefa_payload, implantacao=implantacao, tt=TASK_TIPS)
            progress_html = render_template('partials/_progress_total_bar.html', progresso_percent=novo_prog)
            hx_payload = { 'progress_update': { 'novo_progresso': novo_prog } }
            resp = make_response(item_html + progress_html)
            resp.headers['Content-Type'] = 'text/html; charset=utf-8'
            resp.headers['HX-Trigger-After-Swap'] = json.dumps(hx_payload)
            return resp

        resp = jsonify({
            'ok': True,
            'novo_progresso': novo_prog,
            'concluida': tarefa_concluida
        })
        resp.headers['Content-Type'] = 'application/json'
        return resp
    except Exception as e:
        api_logger.error(f"Erro ao fazer toggle de subtarefa {sub_id}: {e}", exc_info=True)
        return jsonify({'ok': False, 'error': f"Erro interno: {e}"}), 500


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
    id_favorecido = request.args.get('id_favorecido')
    infra_req = request.args.get('infra') or request.args.get('zw') or request.args.get('infra_code')

    if not id_favorecido and not infra_req:
        return jsonify({'ok': False, 'error': 'Informe ID Favorecido ou Infra (ZW_###).'}), 400

    if id_favorecido:
        try:
            id_favorecido = validate_integer(id_favorecido, min_value=1)
        except ValidationError:
            return jsonify({'ok': False, 'error': 'ID Favorecido inválido. Deve ser um número inteiro positivo.'}), 400

    from ..database.external_db import query_external_db

    try:
        # Consulta robusta com JOIN para trazer o máximo de informação possível
        # Prioriza o codigofinanceiro na tabela empresafinanceiro
        # Alterado para trazer TODAS as colunas de detalheempresa (de.*) para inspeção
        query = """
            SELECT 
                ef.codigofinanceiro,
                ef.nomefantasia,
                ef.razaosocial,
                ef.cnpj,
                ef.email,
                ef.telefone,
                ef.cidade,
                ef.estado,
                ef.bairro,
                ef.endereco,
                ef.nomedono,
                ef.responsavelemail,
                ef.responsaveltelefone,
                ef.datacadastro,
                ef.chavezw,
                ef.nomeempresazw,
                ef.empresazw,
                de.*
            FROM empresafinanceiro ef
            LEFT JOIN detalheempresa de ON ef.detalheempresa_codigo = de.codigo
            WHERE {where_clause}
            LIMIT 1
        """
        params = {}
        where_clause = "ef.codigofinanceiro = :id_favorecido"
        if infra_req and not id_favorecido:
            import re as _re
            digits = ''.join(_re.findall(r"\d+", str(infra_req)))
            try:
                emp_int = int(digits)
            except Exception:
                emp_int = None
            if emp_int:
                where_clause = "ef.empresazw = :empresazw"
                params['empresazw'] = emp_int
            else:
                where_clause = "LOWER(ef.nomeempresazw) LIKE :nomezw"
                params['nomezw'] = f"%{str(infra_req).lower()}%"
        else:
            params['id_favorecido'] = id_favorecido

        results = query_external_db(query.format(where_clause=where_clause), params) or []
        if not results and id_favorecido:
            try:
                # Tentar pelo codigo (Id Favorecido) caso seja diferente do codigofinanceiro
                alt_where = "ef.codigo = :codigo"
                alt_params = {'codigo': id_favorecido}
                results = query_external_db(query.format(where_clause=alt_where), alt_params) or []
            except Exception:
                pass

        if not results:
            return jsonify({'ok': False, 'error': 'Empresa não encontrada para este ID Favorecido.'}), 404

        empresa = results[0]



        # Sanitização básica para evitar problemas no JSON
        for k, v in empresa.items():
            if v is None:
                empresa[k] = ""
            elif hasattr(v, 'isoformat'): # Datas
                empresa[k] = v.isoformat()

        # Mapeamento de campos OAMD para campos do Frontend
        # Tentativa de normalizar chaves comuns
        mapped = {}

        # Função auxiliar para buscar chaves insensíveis a maiúsculas/minúsculas e variações
        def find_value(keys_to_try):
            for k in keys_to_try:
                for emp_k in empresa.keys():
                    if emp_k.lower().replace('_', '').replace(' ', '') == k.lower().replace('_', '').replace(' ', ''):
                        return empresa[emp_k]
            return None

        mapped['data_inicio_producao'] = find_value(['iniciodeproducao', 'inicioproducao', 'inicio_producao', 'dt_inicio_producao', 'dataproducao'])
        mapped['data_inicio_efetivo'] = find_value(['inicioimplantacao', 'inicio_implantacao', 'dt_inicio_implantacao', 'dataimplantacao'])
        mapped['data_final_implantacao'] = find_value(['finalimplantacao', 'final_implantacao', 'dt_final_implantacao', 'fimimplantacao', 'datafinalimplantacao'])
        mapped['status_implantacao'] = find_value(['status', 'statusimplantacao', 'situacao'])
        mapped['nivel_atendimento'] = find_value(['nivelatendimento', 'nivel_atendimento', 'classificacao'])
        mapped['nivel_receita'] = find_value(['nivelreceita', 'nivel_receita', 'faixareceita', 'mrr', 'nivelreceitamensal'])
        mapped['chave_oamd'] = empresa.get('chavezw')
        try:
            infra_code = None
            digits_pref = None
            import re as _re
            for _k, _v in empresa.items():
                if isinstance(_v, str) and _v:
                    m = _re.search(r"(?i)\bZW[_\-]?(\d{2,})\b", _v)
                    if m:
                        digits_pref = m.group(1)
                        break
            nomezw = str(empresa.get('nomeempresazw') or '').strip()
            if nomezw:
                mname = _re.search(r"zw[_\-]?(\d+)", nomezw, _re.IGNORECASE)
                if mname:
                    digits_pref = mname.group(1)
            if not digits_pref:
                # tentar extrair de qualquer URL presente nos campos retornados
                for k, v in empresa.items():
                    if k and 'url' in str(k).lower() and v:
                        murl = _re.search(r"zw(\d+)", str(v), _re.IGNORECASE)
                        if murl:
                            digits_pref = murl.group(1)
                            break
            if not digits_pref:
                empzw = empresa.get('empresazw')
                try:
                    ci = int(empzw) if empzw is not None else None
                    if ci is not None and ci > 0 and ci != 1:
                        digits_pref = str(ci)
                except Exception:
                    pass
            if digits_pref and len(digits_pref) >= 2:
                infra_code = f"ZW_{digits_pref}"
                mapped['informacao_infra'] = infra_code
            else:
                mapped['informacao_infra'] = mapped.get('informacao_infra') or ''
            # Forçar padrão de Tela de Apoio com ID Favorecido
            if id_favorecido:
                mapped['tela_apoio_link'] = f"https://app.pactosolucoes.com.br/apoio/apoio/{id_favorecido}"
        except Exception:
            mapped['informacao_infra'] = mapped.get('informacao_infra') or ''
            mapped['tela_apoio_link'] = mapped.get('tela_apoio_link') or ''
        mapped['cnpj'] = empresa.get('cnpj')
        mapped['data_cadastro'] = find_value(['datacadastro', 'data_cadastro', 'created_at', 'dt_cadastro'])

        return jsonify({
            'ok': True,
            'empresa': empresa,
            'mapped': mapped
        })

    except OperationalError as e:
        api_logger.error(f"Erro de conexão OAMD ao consultar ID {id_favorecido}: {e}")
        try:
            fallback_link = f"https://app.pactosolucoes.com.br/apoio/apoio/{id_favorecido}" if id_favorecido else ''
            return jsonify({'ok': True, 'empresa': {}, 'mapped': {
                'tela_apoio_link': fallback_link,
                'informacao_infra': '',
                'chave_oamd': '',
                'cnpj': '',
                'data_cadastro': None,
                'data_inicio_producao': None,
                'data_inicio_efetivo': None,
                'data_final_implantacao': None,
                'status_implantacao': ''
            }})
        except Exception:
            error_msg = str(e).lower()
            if "timeout" in error_msg or "timed out" in error_msg:
                 return jsonify({'ok': False, 'error': 'Tempo limite excedido. Verifique sua conexão com a VPN/Rede.'}), 504
            return jsonify({'ok': False, 'error': 'Falha na conexão com o banco externo.'}), 502

    except Exception as e:
        api_logger.error(f"Erro ao consultar empresa ID {id_favorecido}: {e}", exc_info=True)
        try:
            fallback_link = f"https://app.pactosolucoes.com.br/apoio/apoio/{id_favorecido}" if id_favorecido else ''
            return jsonify({'ok': True, 'empresa': {}, 'mapped': {
                'tela_apoio_link': fallback_link,
                'informacao_infra': '',
                'chave_oamd': '',
                'cnpj': '',
                'data_cadastro': None,
                'data_inicio_producao': None,
                'data_inicio_efetivo': None,
                'data_final_implantacao': None,
                'status_implantacao': ''
            }})
        except Exception:
            return jsonify({'ok': False, 'error': 'Erro ao consultar banco de dados externo.'}), 500

@api_bp.route('/toggle_tarefa_h/<int:tarefa_h_id>', methods=['POST'])
@login_required
@validate_api_origin
@limiter.limit("100 per minute", key_func=lambda: g.user_email or get_remote_address())
def toggle_tarefa_h(tarefa_h_id):
    usuario_cs_email = g.user_email

    try:
        tarefa_h_id = validate_integer(tarefa_h_id, min_value=1)
    except ValidationError as e:
        return jsonify({'ok': False, 'error': f'ID inválido: {str(e)}'}), 400

    try:
        row = query_db(
            """
            SELECT ci.id as tarefa_id, ci.status, i.id as implantacao_id, i.usuario_cs, i.status as impl_status
            FROM checklist_items ci
            JOIN implantacoes i ON ci.implantacao_id = i.id
            WHERE ci.id = %s AND ci.tipo_item = 'tarefa'
            """,
            (tarefa_h_id,), one=True
        )

        if not row:
            return jsonify({'ok': False, 'error': 'Tarefa não encontrada'}), 404
        is_owner = row.get('usuario_cs') == usuario_cs_email
        is_manager = g.perfil and g.perfil.get('perfil_acesso') in PERFIS_COM_GESTAO

        if not (is_owner or is_manager):
            return jsonify({'ok': False, 'error': 'Permissão negada.'}), 403

        if row.get('impl_status') in ['finalizada', 'parada', 'cancelada']:
            return jsonify({'ok': False, 'error': 'Implantação bloqueada para alterações.'}), 400

        request_data = request.get_json(silent=True) or {}
        concluido_desejado = request_data.get('concluido', None)

        if concluido_desejado is None:
            curr = (row.get('status') or '').lower().strip()

            if curr in ['concluido', 'concluida']:
                curr = 'concluida'
            else:
                curr = 'pendente'

            novo_status = 'concluida' if curr != 'concluida' else 'pendente'
        else:
            novo_status = 'concluida' if bool(concluido_desejado) else 'pendente'

        if novo_status not in ['pendente', 'concluida']:
            novo_status = 'pendente'

        execute_db("UPDATE checklist_items SET status = %s, completed = %s WHERE id = %s", (novo_status, novo_status == 'concluida', tarefa_h_id))

        detalhe = f"TarefaH {tarefa_h_id}: {novo_status}."
        logar_timeline(row['implantacao_id'], usuario_cs_email, 'tarefa_alterada', detalhe)

        th = query_db("SELECT id, title as nome, COALESCE(status, 'pendente') as status FROM checklist_items WHERE id = %s AND tipo_item = 'tarefa'", (tarefa_h_id,), one=True)

        if not th:
            return jsonify({'ok': False, 'error': 'Tarefa não encontrada após atualização'}), 404

        status_retornado = (th.get('status') or 'pendente').lower().strip()

        if status_retornado not in ['pendente', 'concluida']:
            if 'conclui' in status_retornado:
                status_retornado = 'concluida'
            else:
                status_retornado = 'pendente'

        if th.get('status') != status_retornado:
            execute_db("UPDATE checklist_items SET status = %s, completed = %s WHERE id = %s", (status_retornado, status_retornado == 'concluida', tarefa_h_id))
            th['status'] = status_retornado

        implantacao_info = query_db("SELECT nome_empresa, email_responsavel FROM implantacoes WHERE id = %s", (row['implantacao_id'],), one=True) or {}

        impl_id = row['implantacao_id']
        if cache:
            cache_key = f'progresso_impl_{impl_id}'
            cache.delete(cache_key)

        novo_prog, _, _ = _get_progress(impl_id)

        tarefa_payload = {
            'id': th.get('id'),
            'tarefa_filho': th.get('nome'),
            'tag': '',
            'concluida': status_retornado == 'concluida',
            'comentarios': [],
            'toggle_url': f"/api/toggle_tarefa_h/{th.get('id')}"
        }
        implantacao = {
            'nome_empresa': implantacao_info.get('nome_empresa', ''),
            'email_responsavel': implantacao_info.get('email_responsavel', '')
        }

        if request.headers.get('HX-Request') == 'true':
            item_html = render_template('partials/_task_item_wrapper.html', tarefa=tarefa_payload, implantacao=implantacao, tt=TASK_TIPS)
            progress_html = render_template('partials/_progress_total_bar.html', progresso_percent=novo_prog)
            hx_payload = { 'progress_update': { 'novo_progresso': novo_prog } }
            resp = make_response(item_html + progress_html)
            resp.headers['Content-Type'] = 'text/html; charset=utf-8'
            resp.headers['HX-Trigger-After-Swap'] = json.dumps(hx_payload)
            return resp

        resp = jsonify({
            'ok': True,
            'novo_progresso': novo_prog,
            'concluida': status_retornado == 'concluida'
        })
        resp.headers['Content-Type'] = 'application/json'
        return resp
    except Exception as e:
        api_logger.error(f"Erro ao fazer toggle de tarefa {tarefa_h_id}: {e}", exc_info=True)
        return jsonify({'ok': False, 'error': f"Erro interno: {e}"}), 500

@api_bp.route('/excluir_subtarefa_h/<int:sub_id>', methods=['POST'])
@login_required
@validate_api_origin
@limiter.limit("50 per minute", key_func=lambda: g.user_email or get_remote_address())
def excluir_subtarefa_h(sub_id):
    usuario_cs_email = g.user_email
    try:
        sub_id = validate_integer(sub_id, min_value=1)
    except ValidationError as e:
        return jsonify({'ok': False, 'error': f'ID inválido: {str(e)}'}), 400
    try:
        row = query_db(
            """
            SELECT ci.id as sub_id, ci.title as nome, i.id as implantacao_id, i.usuario_cs, i.status
            FROM checklist_items ci
            JOIN implantacoes i ON ci.implantacao_id = i.id
            WHERE ci.id = %s AND ci.tipo_item = 'subtarefa'
            """,
            (sub_id,), one=True
        )
        if not row:
            return jsonify({'ok': False, 'error': 'Subtarefa não encontrada'}), 404
        is_owner = row.get('usuario_cs') == usuario_cs_email
        is_manager = g.perfil and g.perfil.get('perfil_acesso') in PERFIS_COM_GESTAO
        if not (is_owner or is_manager):
            return jsonify({'ok': False, 'error': 'Permissão negada.'}), 403
        if row.get('status') in ['finalizada', 'parada', 'cancelada']:
            return jsonify({'ok': False, 'error': 'Implantação bloqueada para alterações.'}), 400
        execute_db("DELETE FROM checklist_items WHERE id = %s AND tipo_item = 'subtarefa'", (sub_id,))
        logar_timeline(row['implantacao_id'], usuario_cs_email, 'tarefa_excluida', f"Subtarefa '{row.get('nome','')}' foi excluída.")
        nome = g.perfil.get('nome', usuario_cs_email)
        log_exclusao = query_db(
            "SELECT *, %s as usuario_nome FROM timeline_log WHERE implantacao_id = %s AND tipo_evento = 'tarefa_excluida' ORDER BY id DESC LIMIT 1",
            (nome, row['implantacao_id']), one=True
        )
        if log_exclusao:
            log_exclusao['data_criacao'] = format_date_iso_for_json(log_exclusao.get('data_criacao'))
        return jsonify({'ok': True, 'log_exclusao': log_exclusao})
    except Exception as e:
        return jsonify({'ok': False, 'error': f"Erro interno: {e}"}), 500

@api_bp.route('/excluir_tarefa_h/<int:tarefa_h_id>', methods=['POST'])
@login_required
@validate_api_origin
@limiter.limit("50 per minute", key_func=lambda: g.user_email or get_remote_address())
def excluir_tarefa_h(tarefa_h_id):
    usuario_cs_email = g.user_email
    try:
        tarefa_h_id = validate_integer(tarefa_h_id, min_value=1)
    except ValidationError as e:
        return jsonify({'ok': False, 'error': f'ID inválido: {str(e)}'}), 400
    try:
        row = query_db(
            """
            SELECT ci.id as tarefa_id, ci.title as nome, i.id as implantacao_id, i.usuario_cs, i.status
            FROM checklist_items ci
            JOIN implantacoes i ON ci.implantacao_id = i.id
            WHERE ci.id = %s AND ci.tipo_item = 'tarefa'
            """,
            (tarefa_h_id,), one=True
        )
        if not row:
            return jsonify({'ok': False, 'error': 'Tarefa não encontrada'}), 404
        is_owner = row.get('usuario_cs') == usuario_cs_email
        is_manager = g.perfil and g.perfil.get('perfil_acesso') in PERFIS_COM_GESTAO
        if not (is_owner or is_manager):
            return jsonify({'ok': False, 'error': 'Permissão negada.'}), 403
        if row.get('status') in ['finalizada', 'parada', 'cancelada']:
            return jsonify({'ok': False, 'error': 'Implantação bloqueada para alterações.'}), 400
        # Deletar subtarefas primeiro (cascata via parent_id)
        execute_db("DELETE FROM checklist_items WHERE parent_id = %s AND tipo_item = 'subtarefa'", (tarefa_h_id,))
        execute_db("DELETE FROM checklist_items WHERE id = %s AND tipo_item = 'tarefa'", (tarefa_h_id,))
        logar_timeline(row['implantacao_id'], usuario_cs_email, 'tarefa_excluida', f"TarefaH '{row.get('nome','')}' foi excluída.")
        nome = g.perfil.get('nome', usuario_cs_email)
        log_exclusao = query_db(
            "SELECT *, %s as usuario_nome FROM timeline_log WHERE implantacao_id = %s AND tipo_evento = 'tarefa_excluida' ORDER BY id DESC LIMIT 1",
            (nome, row['implantacao_id']), one=True
        )
        if log_exclusao:
            log_exclusao['data_criacao'] = format_date_iso_for_json(log_exclusao.get('data_criacao'))
        return jsonify({'ok': True, 'log_exclusao': log_exclusao})
    except Exception as e:
        return jsonify({'ok': False, 'error': f"Erro interno: {e}"}), 500

@api_bp.route('/excluir_grupo_h', methods=['POST'])
@login_required
@validate_api_origin
def excluir_grupo_h():
    usuario_cs_email = g.user_email
    data = request.get_json(silent=True) or {}
    impl_id = data.get('implantacao_id')
    grupo_nome = (data.get('grupo_nome') or '').strip()
    if not impl_id or not grupo_nome:
        return jsonify({'ok': False, 'error': 'Dados inválidos.'}), 400
    try:
        impl = query_db("SELECT id, usuario_cs, status FROM implantacoes WHERE id = %s", (impl_id,), one=True)
        if not impl:
            return jsonify({'ok': False, 'error': 'Implantação não encontrada.'}), 404
        is_owner = impl.get('usuario_cs') == usuario_cs_email
        is_manager = g.perfil and g.perfil.get('perfil_acesso') in PERFIS_COM_GESTAO
        if not (is_owner or is_manager):
            return jsonify({'ok': False, 'error': 'Permissão negada.'}), 403
        if impl.get('status') in ['finalizada', 'parada', 'cancelada']:
            return jsonify({'ok': False, 'error': f"Não é possível excluir em status '{impl.get('status')}'."}), 400
        grupo = query_db(
            """
            SELECT ci.id FROM checklist_items ci
            WHERE ci.implantacao_id = %s AND ci.tipo_item = 'grupo' AND ci.title = %s
            """,
            (impl_id, grupo_nome), one=True
        )
        if not grupo:
            return jsonify({'ok': False, 'error': 'Grupo não encontrado.'}), 404
        gid = grupo['id']
        # Deletar recursivamente: subtarefas -> tarefas -> grupo
        tarefas_ids = query_db("SELECT id FROM checklist_items WHERE parent_id = %s AND tipo_item = 'tarefa'", (gid,)) or []
        for t in tarefas_ids:
            execute_db("DELETE FROM checklist_items WHERE parent_id = %s AND tipo_item = 'subtarefa'", (t['id'],))
        execute_db("DELETE FROM checklist_items WHERE parent_id = %s AND tipo_item = 'tarefa'", (gid,))
        execute_db("DELETE FROM checklist_items WHERE id = %s AND tipo_item = 'grupo'", (gid,))
        logar_timeline(impl_id, usuario_cs_email, 'modulo_excluido', f"Todas as tarefas do grupo '{grupo_nome}' foram excluídas.")
        nome = g.perfil.get('nome', usuario_cs_email)
        log_exclusao = query_db(
            "SELECT *, %s as usuario_nome FROM timeline_log WHERE implantacao_id = %s AND tipo_evento = 'modulo_excluido' ORDER BY id DESC LIMIT 1",
            (nome, impl_id), one=True
        )
        if log_exclusao:
            log_exclusao['data_criacao'] = format_date_iso_for_json(log_exclusao.get('data_criacao'))
        return jsonify({'ok': True, 'log_exclusao_modulo': log_exclusao})
    except Exception as e:
        return jsonify({'ok': False, 'error': f"Erro interno: {e}"}), 500

@api_bp.route('/reordenar_hierarquia', methods=['POST'])
@login_required
@validate_api_origin
def reordenar_hierarquia():
    usuario_cs_email = g.user_email
    data = request.get_json(silent=True) or {}
    impl_id = data.get('implantacao_id')
    grupo_nome = (data.get('grupo_nome') or '').strip()
    ordem = data.get('ordem') or []
    if not impl_id or not grupo_nome or not isinstance(ordem, list):
        return jsonify({'ok': False, 'error': 'Dados inválidos.'}), 400
    try:
        impl = query_db("SELECT id, usuario_cs, status FROM implantacoes WHERE id = %s", (impl_id,), one=True)
        if not impl:
            return jsonify({'ok': False, 'error': 'Implantação não encontrada.'}), 404
        is_owner = impl.get('usuario_cs') == usuario_cs_email
        is_manager = g.perfil and g.perfil.get('perfil_acesso') in PERFIS_COM_GESTAO
        if not (is_owner or is_manager):
            return jsonify({'ok': False, 'error': 'Permissão negada.'}), 403
        if impl.get('status') in ['finalizada', 'parada', 'cancelada']:
            return jsonify({'ok': False, 'error': f"Não é possível reordenar em status '{impl.get('status')}'."}), 400
        grupo = query_db(
            """
            SELECT ci.id FROM checklist_items ci
            WHERE ci.implantacao_id = %s AND ci.tipo_item = 'grupo' AND ci.title = %s
            """,
            (impl_id, grupo_nome), one=True
        )
        if not grupo:
            return jsonify({'ok': False, 'error': 'Grupo não encontrado.'}), 404
        for idx, item_id in enumerate(ordem, 1):
            try:
                execute_db("UPDATE checklist_items SET ordem = %s WHERE id = %s", (idx, item_id))
            except Exception:
                pass
        logar_timeline(impl_id, usuario_cs_email, 'tarefas_reordenadas', f"A ordem das tarefas no grupo '{grupo_nome}' foi alterada.")
        nome = g.perfil.get('nome', usuario_cs_email)
        log_reordenar = query_db(
            "SELECT *, %s as usuario_nome FROM timeline_log WHERE implantacao_id = %s AND tipo_evento = 'tarefas_reordenadas' ORDER BY id DESC LIMIT 1",
            (nome, impl_id), one=True
        )
        if log_reordenar:
            log_reordenar['data_criacao'] = format_date_iso_for_json(log_reordenar.get('data_criacao'))
        return jsonify({'ok': True, 'log_reordenar': log_reordenar})
    except Exception as e:
        return jsonify({'ok': False, 'error': f"Erro interno: {e}"}), 500
