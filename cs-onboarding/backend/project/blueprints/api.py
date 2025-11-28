
from flask import Blueprint, request, jsonify, g, current_app, render_template, make_response
from datetime import datetime
import os
import time
import json
from werkzeug.utils import secure_filename
from botocore.exceptions import ClientError, NoCredentialsError

from ..blueprints.auth import login_required

# Importar cache para invalidação
try:
    from ..config.cache_config import cache
except ImportError:
    cache = None


from ..db import query_db, execute_db, logar_timeline, execute_and_fetch_one, db_transaction_with_lock

from ..core.extensions import r2_client, limiter                                                


from ..domain.implantacao_service import _get_progress
from ..domain.task_definitions import TASK_TIPS
from ..domain.hierarquia_service import (
    toggle_subtarefa,
    calcular_progresso_implantacao,
    adicionar_comentario_tarefa,
    get_comentarios_tarefa
)

from ..common.utils import allowed_file, format_date_iso_for_json, format_date_br
from ..common.file_validation import validate_uploaded_file
from ..constants import PERFIS_COM_GESTAO
from ..common.validation import validate_integer, sanitize_string, ValidationError
from ..config.logging_config import api_logger, security_logger
from flask_limiter.util import get_remote_address

from ..security.api_security import validate_api_origin

api_bp = Blueprint('api', __name__, url_prefix='/api')


@api_bp.before_request
def _api_origin_guard():
    return validate_api_origin(lambda: None)()

# ============================================================================
# CÓDIGO LEGADO REMOVIDO - Endpoints do modelo antigo (tabela 'tarefas')
# Todos os endpoints legados foram removidos. Use os endpoints hierárquicos:
# - /api/toggle_tarefa_h/<int:tarefa_h_id>
# - /api/toggle_subtarefa_h/<int:sub_id>
# - /api/adicionar_comentario_h/<string:tipo>/<int:item_id>
# - /api/excluir_tarefa_h/<int:tarefa_h_id>
# - /api/excluir_subtarefa_h/<int:sub_id>
# ============================================================================

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

# ============================================================================
# Endpoints Hierárquicos (Modelo Novo) - A partir daqui
# ============================================================================

@api_bp.route('/toggle_subtarefa_h/<int:sub_id>', methods=['POST'])
@login_required
@validate_api_origin
@limiter.limit("100 per minute", key_func=lambda: g.user_email or get_remote_address())
def toggle_subtarefa_h(sub_id):
    api_logger.info(f"[TOGGLE_SUBTAREFA_H] INÍCIO - sub_id={sub_id}")
    usuario_cs_email = g.user_email
    api_logger.info(f"[TOGGLE_SUBTAREFA_H] Usuario: {usuario_cs_email}")
    
    try:
        sub_id = validate_integer(sub_id, min_value=1)
        api_logger.info(f"[TOGGLE_SUBTAREFA_H] ID validado: {sub_id}")
    except ValidationError as e:
        api_logger.error(f"[TOGGLE_SUBTAREFA_H] ERRO validação ID: {str(e)}")
        return jsonify({'ok': False, 'error': f'ID inválido: {str(e)}'}), 400
    
    try:
        api_logger.info(f"[TOGGLE_SUBTAREFA_H] Buscando subtarefa no banco...")
        row = query_db(
            """
            SELECT s.id as sub_id, s.concluido, i.id as implantacao_id, i.usuario_cs, i.status
            FROM subtarefas_h s
            JOIN tarefas_h th ON s.tarefa_id = th.id
            JOIN grupos g ON th.grupo_id = g.id
            JOIN fases f ON g.fase_id = f.id
            JOIN implantacoes i ON f.implantacao_id = i.id
            WHERE s.id = %s
            """,
            (sub_id,), one=True
        )
        api_logger.info(f"[TOGGLE_SUBTAREFA_H] Resultado query: {row}")
        
        if not row:
            api_logger.error(f"[TOGGLE_SUBTAREFA_H] Subtarefa não encontrada no banco")
            return jsonify({'ok': False, 'error': 'Subtarefa não encontrada'}), 404
        
        is_owner = row.get('usuario_cs') == usuario_cs_email
        is_manager = g.perfil and g.perfil.get('perfil_acesso') in PERFIS_COM_GESTAO
        api_logger.info(f"[TOGGLE_SUBTAREFA_H] Permissões - is_owner={is_owner}, is_manager={is_manager}")
        
        if not (is_owner or is_manager):
            api_logger.error(f"[TOGGLE_SUBTAREFA_H] PERMISSÃO NEGADA")
            return jsonify({'ok': False, 'error': 'Permissão negada.'}), 403
        
        if row.get('status') in ['finalizada', 'parada', 'cancelada']:
            api_logger.error(f"[TOGGLE_SUBTAREFA_H] Implantação bloqueada - status={row.get('status')}")
            return jsonify({'ok': False, 'error': 'Implantação bloqueada para alterações.'}), 400
        
        # Obter o estado desejado do body da requisição
        request_data = request.get_json(silent=True) or {}
        concluido_desejado = request_data.get('concluido', None)
        api_logger.info(f"[TOGGLE_SUBTAREFA_H] Request data: {request_data}")
        api_logger.info(f"[TOGGLE_SUBTAREFA_H] concluido_desejado={concluido_desejado}")
        api_logger.info(f"[TOGGLE_SUBTAREFA_H] Status atual no banco: concluido={row.get('concluido')}")
        
        # Se não foi enviado no body, alternar o estado atual
        if concluido_desejado is None:
            novo = 0 if row.get('concluido') else 1
            api_logger.info(f"[TOGGLE_SUBTAREFA_H] Toggle automático: {row.get('concluido')} -> {novo}")
        else:
            # Usar o valor enviado pelo frontend
            novo = 1 if bool(concluido_desejado) else 0
            api_logger.info(f"[TOGGLE_SUBTAREFA_H] Valor vindo do frontend: concluido_desejado={concluido_desejado} -> novo={novo}")
        
        api_logger.info(f"[TOGGLE_SUBTAREFA_H] Atualizando banco: UPDATE subtarefas_h SET concluido = {novo} WHERE id = {sub_id}")
        execute_db("UPDATE subtarefas_h SET concluido = %s WHERE id = %s", (novo, sub_id))
        api_logger.info(f"[TOGGLE_SUBTAREFA_H] UPDATE executado com sucesso")
        
        detalhe = f"Subtarefa {sub_id}: {'Concluída' if novo else 'Não Concluída'}."
        api_logger.info(f"[TOGGLE_SUBTAREFA_H] Logando timeline: {detalhe}")
        logar_timeline(row['implantacao_id'], usuario_cs_email, 'tarefa_alterada', detalhe)
        
        api_logger.info(f"[TOGGLE_SUBTAREFA_H] Buscando subtarefa atualizada do banco...")
        tarefa_atualizada = query_db("SELECT id, nome, concluido FROM subtarefas_h WHERE id = %s", (sub_id,), one=True)
        api_logger.info(f"[TOGGLE_SUBTAREFA_H] Subtarefa retornada do banco: {tarefa_atualizada}")
        
        api_logger.info(f"[TOGGLE_SUBTAREFA_H] Buscando informações de implantação...")
        implantacao_info = query_db("SELECT nome_empresa, email_responsavel FROM implantacoes WHERE id = %s", (row['implantacao_id'],), one=True) or {}
        api_logger.info(f"[TOGGLE_SUBTAREFA_H] Calculando progresso...")
        # Invalidar cache antes de calcular novo progresso
        impl_id = row['implantacao_id']
        if cache:
            cache_key = f'progresso_impl_{impl_id}'
            cache.delete(cache_key)
            api_logger.info(f"[TOGGLE_SUBTAREFA_H] Cache invalidado para impl_id={impl_id}")
        
        novo_prog, _, _ = _get_progress(impl_id)
        api_logger.info(f"[TOGGLE_SUBTAREFA_H] Novo progresso: {novo_prog}%")
        
        tarefa_concluida = bool(tarefa_atualizada.get('concluido'))
        
        if request.headers.get('HX-Request') == 'true':
            api_logger.info(f"[TOGGLE_SUBTAREFA_H] Requisição HTMX detectada, retornando HTML")
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
            api_logger.info(f"[TOGGLE_SUBTAREFA_H] Resposta HTMX enviada com sucesso")
            return resp
        
        api_logger.info(f"[TOGGLE_SUBTAREFA_H] Retornando resposta JSON")
        resp = jsonify({
            'ok': True,
            'novo_progresso': novo_prog,
            'concluida': tarefa_concluida
        })
        resp.headers['Content-Type'] = 'application/json'
        api_logger.info(f"[TOGGLE_SUBTAREFA_H] Resposta JSON enviada: ok=True, concluida={tarefa_concluida}, novo_progresso={novo_prog}")
        return resp
    except Exception as e:
        api_logger.error(f"[TOGGLE_SUBTAREFA_H] EXCEÇÃO CAPTURADA: {e}", exc_info=True)
        return jsonify({'ok': False, 'error': f"Erro interno: {e}"}), 500

@api_bp.route('/toggle_tarefa_h/<int:tarefa_h_id>', methods=['POST'])
@login_required
@validate_api_origin
@limiter.limit("100 per minute", key_func=lambda: g.user_email or get_remote_address())
def toggle_tarefa_h(tarefa_h_id):
    api_logger.info(f"[TOGGLE_TAREFA_H] INÍCIO - tarefa_h_id={tarefa_h_id}")
    usuario_cs_email = g.user_email
    api_logger.info(f"[TOGGLE_TAREFA_H] Usuario: {usuario_cs_email}")
    
    try:
        tarefa_h_id = validate_integer(tarefa_h_id, min_value=1)
        api_logger.info(f"[TOGGLE_TAREFA_H] ID validado: {tarefa_h_id}")
    except ValidationError as e:
        api_logger.error(f"[TOGGLE_TAREFA_H] ERRO validação ID: {str(e)}")
        return jsonify({'ok': False, 'error': f'ID inválido: {str(e)}'}), 400
    
    try:
        api_logger.info(f"[TOGGLE_TAREFA_H] Buscando tarefa no banco...")
        row = query_db(
            """
            SELECT th.id as tarefa_id, th.status, i.id as implantacao_id, i.usuario_cs, i.status as impl_status
            FROM tarefas_h th
            JOIN grupos g ON th.grupo_id = g.id
            JOIN fases f ON g.fase_id = f.id
            JOIN implantacoes i ON f.implantacao_id = i.id
            WHERE th.id = %s
            """,
            (tarefa_h_id,), one=True
        )
        api_logger.info(f"[TOGGLE_TAREFA_H] Resultado query: {row}")
        
        if not row:
            api_logger.error(f"[TOGGLE_TAREFA_H] Tarefa não encontrada no banco")
            return jsonify({'ok': False, 'error': 'Tarefa não encontrada'}), 404
        is_owner = row.get('usuario_cs') == usuario_cs_email
        is_manager = g.perfil and g.perfil.get('perfil_acesso') in PERFIS_COM_GESTAO
        api_logger.info(f"[TOGGLE_TAREFA_H] Permissões - is_owner={is_owner}, is_manager={is_manager}")
        
        if not (is_owner or is_manager):
            api_logger.error(f"[TOGGLE_TAREFA_H] PERMISSÃO NEGADA")
            return jsonify({'ok': False, 'error': 'Permissão negada.'}), 403
        
        if row.get('impl_status') in ['finalizada', 'parada', 'cancelada']:
            api_logger.error(f"[TOGGLE_TAREFA_H] Implantação bloqueada - status={row.get('impl_status')}")
            return jsonify({'ok': False, 'error': 'Implantação bloqueada para alterações.'}), 400
        
        # Obter o estado desejado do body da requisição
        request_data = request.get_json(silent=True) or {}
        concluido_desejado = request_data.get('concluido', None)
        api_logger.info(f"[TOGGLE_TAREFA_H] Request data: {request_data}")
        api_logger.info(f"[TOGGLE_TAREFA_H] concluido_desejado={concluido_desejado}")
        
        # Se não foi enviado no body, alternar o estado atual
        if concluido_desejado is None:
            curr = (row.get('status') or '').lower().strip()
            api_logger.info(f"[TOGGLE_TAREFA_H] Status atual no banco: '{curr}'")
            
            # Normalizar valores antigos
            if curr in ['concluido', 'concluida']:
                curr = 'concluida'
            else:
                curr = 'pendente'
            
            novo_status = 'concluida' if curr != 'concluida' else 'pendente'
            api_logger.info(f"[TOGGLE_TAREFA_H] Toggle automático: curr='{curr}' -> novo_status='{novo_status}'")
        else:
            # Usar o valor enviado pelo frontend
            novo_status = 'concluida' if bool(concluido_desejado) else 'pendente'
            api_logger.info(f"[TOGGLE_TAREFA_H] Status vindo do frontend: concluido_desejado={concluido_desejado} -> novo_status='{novo_status}'")
        
        # Garantir que o status seja sempre 'pendente' ou 'concluida'
        if novo_status not in ['pendente', 'concluida']:
            api_logger.warning(f"[TOGGLE_TAREFA_H] Status inválido '{novo_status}', normalizando para 'pendente'")
            novo_status = 'pendente'
        
        api_logger.info(f"[TOGGLE_TAREFA_H] Atualizando banco: UPDATE tarefas_h SET status = '{novo_status}' WHERE id = {tarefa_h_id}")
        # Garantir que o status seja sempre 'pendente' ou 'concluida' (nunca NULL)
        execute_db("UPDATE tarefas_h SET status = %s WHERE id = %s", (novo_status, tarefa_h_id))
        api_logger.info(f"[TOGGLE_TAREFA_H] UPDATE executado com sucesso")
        
        # Log para debug
        api_logger.info(f"[TOGGLE_TAREFA_H] Tarefa {tarefa_h_id} atualizada: status anterior={row.get('status')}, novo_status={novo_status}, concluido_desejado={concluido_desejado}")
        
        detalhe = f"TarefaH {tarefa_h_id}: {novo_status}."
        api_logger.info(f"[TOGGLE_TAREFA_H] Logando timeline: {detalhe}")
        logar_timeline(row['implantacao_id'], usuario_cs_email, 'tarefa_alterada', detalhe)
        
        # Buscar tarefa atualizada do banco
        api_logger.info(f"[TOGGLE_TAREFA_H] Buscando tarefa atualizada do banco...")
        th = query_db("SELECT id, nome, COALESCE(status, 'pendente') as status FROM tarefas_h WHERE id = %s", (tarefa_h_id,), one=True)
        api_logger.info(f"[TOGGLE_TAREFA_H] Tarefa retornada do banco: {th}")
        
        if not th:
            api_logger.error(f"[TOGGLE_TAREFA_H] Tarefa não encontrada após UPDATE!")
            return jsonify({'ok': False, 'error': 'Tarefa não encontrada após atualização'}), 404
        
        # Normalizar status retornado - garantir que seja 'concluida' ou 'pendente'
        status_retornado = (th.get('status') or 'pendente').lower().strip()
        api_logger.info(f"[TOGGLE_TAREFA_H] Status retornado do banco (antes normalização): '{status_retornado}'")
        
        if status_retornado not in ['pendente', 'concluida']:
            # Se for 'concluido' ou qualquer variação, normalizar para 'concluida'
            if 'conclui' in status_retornado:
                status_retornado = 'concluida'
            else:
                status_retornado = 'pendente'
            api_logger.info(f"[TOGGLE_TAREFA_H] Status normalizado para: '{status_retornado}'")
        
        # Se o status no banco não estiver normalizado, corrigir
        if th.get('status') != status_retornado:
            api_logger.info(f"[TOGGLE_TAREFA_H] Corrigindo status no banco: '{th.get('status')}' -> '{status_retornado}'")
            execute_db("UPDATE tarefas_h SET status = %s WHERE id = %s", (status_retornado, tarefa_h_id))
            th['status'] = status_retornado
        
        api_logger.info(f"[TOGGLE_TAREFA_H] Buscando informações de implantação...")
        implantacao_info = query_db("SELECT nome_empresa, email_responsavel FROM implantacoes WHERE id = %s", (row['implantacao_id'],), one=True) or {}
        api_logger.info(f"[TOGGLE_TAREFA_H] Calculando progresso...")
        # Invalidar cache antes de calcular novo progresso
        impl_id = row['implantacao_id']
        if cache:
            cache_key = f'progresso_impl_{impl_id}'
            cache.delete(cache_key)
            api_logger.info(f"[TOGGLE_TAREFA_H] Cache invalidado para impl_id={impl_id}")
        
        novo_prog, _, _ = _get_progress(impl_id)
        api_logger.info(f"[TOGGLE_TAREFA_H] Novo progresso: {novo_prog}%")
        
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
        
        api_logger.info(f"[TOGGLE_TAREFA_H] tarefa_payload criado: {tarefa_payload}")
        
        if request.headers.get('HX-Request') == 'true':
            api_logger.info(f"[TOGGLE_TAREFA_H] Requisição HTMX detectada, retornando HTML")
            item_html = render_template('partials/_task_item_wrapper.html', tarefa=tarefa_payload, implantacao=implantacao, tt=TASK_TIPS)
            progress_html = render_template('partials/_progress_total_bar.html', progresso_percent=novo_prog)
            hx_payload = { 'progress_update': { 'novo_progresso': novo_prog } }
            resp = make_response(item_html + progress_html)
            resp.headers['Content-Type'] = 'text/html; charset=utf-8'
            resp.headers['HX-Trigger-After-Swap'] = json.dumps(hx_payload)
            api_logger.info(f"[TOGGLE_TAREFA_H] Resposta HTMX enviada com sucesso")
            return resp
        
        api_logger.info(f"[TOGGLE_TAREFA_H] Retornando resposta JSON")
        resp = jsonify({
            'ok': True,
            'novo_progresso': novo_prog,
            'concluida': status_retornado == 'concluida'
        })
        resp.headers['Content-Type'] = 'application/json'
        api_logger.info(f"[TOGGLE_TAREFA_H] Resposta JSON enviada: ok=True, concluida={status_retornado == 'concluida'}, novo_progresso={novo_prog}")
        return resp
    except Exception as e:
        api_logger.error(f"[TOGGLE_TAREFA_H] EXCEÇÃO CAPTURADA: {e}", exc_info=True)
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
            SELECT s.id as sub_id, s.nome, i.id as implantacao_id, i.usuario_cs, i.status
            FROM subtarefas_h s
            JOIN tarefas_h th ON s.tarefa_id = th.id
            JOIN grupos g ON th.grupo_id = g.id
            JOIN fases f ON g.fase_id = f.id
            JOIN implantacoes i ON f.implantacao_id = i.id
            WHERE s.id = %s
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
        execute_db("DELETE FROM subtarefas_h WHERE id = %s", (sub_id,))
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
            SELECT th.id as tarefa_id, th.nome, i.id as implantacao_id, i.usuario_cs, i.status
            FROM tarefas_h th
            JOIN grupos g ON th.grupo_id = g.id
            JOIN fases f ON g.fase_id = f.id
            JOIN implantacoes i ON f.implantacao_id = i.id
            WHERE th.id = %s
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
        execute_db("DELETE FROM subtarefas_h WHERE tarefa_id = %s", (tarefa_h_id,))
        execute_db("DELETE FROM tarefas_h WHERE id = %s", (tarefa_h_id,))
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
            SELECT g.id FROM grupos g
            JOIN fases f ON g.fase_id = f.id
            WHERE f.implantacao_id = %s AND g.nome = %s
            """,
            (impl_id, grupo_nome), one=True
        )
        if not grupo:
            return jsonify({'ok': False, 'error': 'Grupo não encontrado.'}), 404
        gid = grupo['id']
        tarefas_ids = query_db("SELECT id FROM tarefas_h WHERE grupo_id = %s", (gid,)) or []
        for t in tarefas_ids:
            execute_db("DELETE FROM subtarefas_h WHERE tarefa_id = %s", (t['id'],))
        execute_db("DELETE FROM tarefas_h WHERE grupo_id = %s", (gid,))
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
            SELECT g.id FROM grupos g
            JOIN fases f ON g.fase_id = f.id
            WHERE f.implantacao_id = %s AND g.nome = %s
            """,
            (impl_id, grupo_nome), one=True
        )
        if not grupo:
            return jsonify({'ok': False, 'error': 'Grupo não encontrado.'}), 404
        for idx, item_id in enumerate(ordem, 1):
            try:
                execute_db("UPDATE subtarefas_h SET ordem = %s WHERE id = %s", (idx, item_id))
            except Exception:
                try:
                    execute_db("UPDATE tarefas_h SET ordem = %s WHERE id = %s", (idx, item_id))
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
