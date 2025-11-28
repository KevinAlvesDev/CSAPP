
from flask import Blueprint, request, jsonify, g, current_app, render_template, make_response
from datetime import datetime
import os
import time
import json
from werkzeug.utils import secure_filename
from botocore.exceptions import ClientError, NoCredentialsError

from ..blueprints.auth import login_required


from ..db import query_db, execute_db, logar_timeline, execute_and_fetch_one

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

@api_bp.route('/toggle_tarefa/<int:tarefa_id>', methods=['POST'])
@login_required
@validate_api_origin                                    
@limiter.limit("100 per minute", key_func=lambda: g.user_email or get_remote_address())
def toggle_tarefa(tarefa_id):
    usuario_cs_email = g.user_email

    try:
        tarefa_id = validate_integer(tarefa_id, min_value=1)
    except ValidationError as e:
        api_logger.warning(f'Invalid task ID in toggle_tarefa: {str(e)} - User: {g.user_email}')
        return jsonify({'ok': False, 'error': f'ID de tarefa inválido: {str(e)}'}), 400
    try:
        tarefa = query_db(
            """
            SELECT t.*, i.usuario_cs, i.id as implantacao_id, i.status 
            FROM tarefas t 
            JOIN implantacoes i ON t.implantacao_id = i.id 
            WHERE t.id = %s
            """, (tarefa_id,), one=True
        )
        
        if not tarefa:
            api_logger.warning(f'Task not found: {tarefa_id} - User: {g.user_email}')
            return jsonify({'ok': False, 'error': 'Tarefa não encontrada'}), 404
            
        is_owner = tarefa.get('usuario_cs') == usuario_cs_email
        is_manager = g.perfil and g.perfil.get('perfil_acesso') in PERFIS_COM_GESTAO
        
        if not (is_owner or is_manager):
             security_logger.warning(f'Permission denied for user {g.user_email} trying to toggle task {tarefa_id}')
             return jsonify({'ok': False, 'error': 'Permissão negada.'}), 403
            
        if tarefa.get('status') in ['finalizada', 'parada', 'cancelada']:
            return jsonify({'ok': False, 'error': f'Não é possível alterar tarefas de implantações com status "{tarefa.get("status")}".'}), 400
            
        novo_status_bool = not tarefa.get('concluida', False)
        
        data_conclusao_val = datetime.now() if novo_status_bool else None
        execute_db(
            "UPDATE tarefas SET concluida = %s, data_conclusao = %s WHERE id = %s", 
            (novo_status_bool, data_conclusao_val, tarefa_id)
        )
        
        detalhe = f"Tarefa '{tarefa['tarefa_filho']}': {'Marcada como Concluída' if novo_status_bool else 'Marcada como Não Concluída'}."
        logar_timeline(tarefa['implantacao_id'], usuario_cs_email, 'tarefa_alterada', detalhe)
        
        api_logger.info(f'Task {tarefa_id} status changed to {novo_status_bool} by user {g.user_email}')

        finalizada, log_finalizacao = False, None
        novo_prog, _, _ = _get_progress(tarefa['implantacao_id'])

        nome = g.perfil.get('nome', usuario_cs_email)
        log_tarefa = query_db(
            "SELECT *, %s as usuario_nome FROM timeline_log "
            "WHERE implantacao_id = %s AND tipo_evento = 'tarefa_alterada' "
            "ORDER BY id DESC LIMIT 1",
            (nome, tarefa['implantacao_id']), one=True
        )
        if log_tarefa:
            log_tarefa['data_criacao'] = format_date_iso_for_json(log_tarefa.get('data_criacao'))

        if request.headers.get('HX-Request') == 'true':
            tarefa_atualizada = query_db(
                "SELECT id, tarefa_filho, tag, concluida FROM tarefas WHERE id = %s",
                (tarefa_id,), one=True
            )
            comentarios = query_db(
                """
                SELECT c.*, p.nome as usuario_nome
                FROM comentarios c
                LEFT JOIN perfil_usuario p ON c.usuario_cs = p.usuario
                WHERE c.tarefa_id = %s
                ORDER BY c.id ASC
                """,
                (tarefa_id,)
            ) or []

            tarefa_atualizada['comentarios'] = comentarios

            implantacao_info = query_db(
                "SELECT nome_empresa, email_responsavel FROM implantacoes WHERE id = %s",
                (tarefa['implantacao_id'],), one=True
            ) or {}
            implantacao = {
                'nome_empresa': implantacao_info.get('nome_empresa', ''),
                'email_responsavel': implantacao_info.get('email_responsavel', '')
            }

            hx_payload = {
                'progress_update': {
                    'novo_progresso': novo_prog,
                    'log_tarefa': log_tarefa,
                    'implantacao_finalizada': finalizada,
                    'log_finalizacao': log_finalizacao
                }
            }

            item_html = render_template('partials/_task_item_wrapper.html', tarefa=tarefa_atualizada, implantacao=implantacao, tt=TASK_TIPS)
            progress_html = render_template('partials/_progress_total_bar.html', progresso_percent=novo_prog)
            resp = make_response(item_html + progress_html)

            resp.headers['HX-Trigger-After-Swap'] = json.dumps(hx_payload)
            return resp

        return jsonify({
            'ok': True,
            'novo_progresso': novo_prog,
            'log_tarefa': log_tarefa,
            'implantacao_finalizada': finalizada,
            'log_finalizacao': log_finalizacao
        })
        
    except Exception as e:
        api_logger.error(f"Erro ao alternar tarefa ID {tarefa_id}: {e}", exc_info=True)
        return jsonify({'ok': False, 'error': f"Erro interno: {e}"}), 500


@api_bp.route('/toggle_tarefas', methods=['POST'])
@login_required
@validate_api_origin                                    
def toggle_tarefas_bulk():
    """Alterna o status de múltiplas tarefas de uma mesma implantação em uma única operação.
    Espera JSON com {'ids': [<int>, ...]} ou form 'ids' separado por vírgula.
    Garante verificação de permissão e finaliza a implantação somente ao final.
    """
    usuario_cs_email = g.user_email

    ids = []
    try:
        if request.is_json:
            payload = request.get_json(silent=True) or {}
            ids = payload.get('ids') or []
        else:
            raw = (request.form.get('ids') or '').strip()
            if raw:
                ids = [s for s in raw.split(',') if s]

        ids_norm = []
        for tid in ids:
            try:
                tid_val = validate_integer(int(tid), min_value=1)
                ids_norm.append(tid_val)
            except Exception:
                raise ValidationError(f"ID inválido na lista: {tid}")

        if not ids_norm:
            return jsonify({'ok': False, 'error': 'Nenhuma tarefa informada.'}), 400
    except ValidationError as e:
        api_logger.warning(f'Invalid task IDs in toggle_tarefas_bulk: {str(e)} - User: {g.user_email}')
        return jsonify({'ok': False, 'error': f'Lista de IDs inválida: {str(e)}'}), 400

    implantacao_id = None
    status_impl = None
    tarefas_info = []
    for tarefa_id in ids_norm:
        tarefa = query_db(
            """
            SELECT t.id, t.concluida, t.tarefa_filho, i.usuario_cs, i.id as implantacao_id, i.status
            FROM tarefas t
            JOIN implantacoes i ON t.implantacao_id = i.id
            WHERE t.id = %s
            """,
            (tarefa_id,), one=True
        )
        if not tarefa:
            return jsonify({'ok': False, 'error': f'Tarefa {tarefa_id} não encontrada.'}), 404

        is_owner = tarefa.get('usuario_cs') == usuario_cs_email
        is_manager = g.perfil and g.perfil.get('perfil_acesso') in PERFIS_COM_GESTAO
        if not (is_owner or is_manager):
            security_logger.warning(f'Permission denied for user {g.user_email} trying to bulk toggle task {tarefa_id}')
            return jsonify({'ok': False, 'error': 'Permissão negada.'}), 403

        st = tarefa.get('status')
        if st in ['finalizada', 'parada', 'cancelada']:
            return jsonify({'ok': False, 'error': f'Implantação em status "{st}" não permite alteração de tarefas.'}), 400

        if implantacao_id is None:
            implantacao_id = tarefa.get('implantacao_id')
            status_impl = st
        elif implantacao_id != tarefa.get('implantacao_id'):
            return jsonify({'ok': False, 'error': 'Todas as tarefas devem pertencer à mesma implantação.'}), 400

        tarefas_info.append(tarefa)

    try:
        updated = 0
        for tarefa in tarefas_info:
            tid = tarefa['id']
            novo_status_bool = not tarefa.get('concluida', False)
            data_conclusao_val = datetime.now() if novo_status_bool else None
            execute_db(
                "UPDATE tarefas SET concluida = %s, data_conclusao = %s WHERE id = %s",
                (novo_status_bool, data_conclusao_val, tid)
            )
            detalhe = f"Tarefa '{tarefa['tarefa_filho']}': {'Marcada como Concluída' if novo_status_bool else 'Marcada como Não Concluída'}."
            logar_timeline(implantacao_id, usuario_cs_email, 'tarefa_alterada', detalhe)
            updated += 1

        finalizada, log_finalizacao = False, None
        novo_prog, _, _ = _get_progress(implantacao_id)

        if request.headers.get('HX-Request') == 'true':
            nome = g.perfil.get('nome', usuario_cs_email)
            log_tarefa = query_db(
                "SELECT *, %s as usuario_nome FROM timeline_log "
                "WHERE implantacao_id = %s AND tipo_evento = 'tarefa_alterada' "
                "ORDER BY id DESC LIMIT 1",
                (nome, implantacao_id), one=True
            )
            if log_tarefa:
                log_tarefa['data_criacao'] = format_date_iso_for_json(log_tarefa.get('data_criacao'))

            implantacao_info = query_db(
                "SELECT nome_empresa, email_responsavel FROM implantacoes WHERE id = %s",
                (implantacao_id,), one=True
            ) or {}
            implantacao = {
                'nome_empresa': implantacao_info.get('nome_empresa', ''),
                'email_responsavel': implantacao_info.get('email_responsavel', '')
            }

            fragments = []
            for tarefa in tarefas_info:
                tid = tarefa['id']
                tarefa_atualizada = query_db(
                    "SELECT id, tarefa_filho, tag, concluida FROM tarefas WHERE id = %s",
                    (tid,), one=True
                )
                comentarios = query_db(
                    """
                    SELECT c.*, p.nome as usuario_nome
                    FROM comentarios c
                    LEFT JOIN perfil_usuario p ON c.usuario_cs = p.usuario
                    WHERE c.tarefa_id = %s
                    ORDER BY c.id ASC
                    """,
                    (tid,)
                ) or []
                tarefa_atualizada['comentarios'] = comentarios
                fragments.append(render_template('partials/_task_item_wrapper.html', tarefa=tarefa_atualizada, implantacao=implantacao, tt=TASK_TIPS, oob=True))

            progress_html = render_template('partials/_progress_total_bar.html', progresso_percent=novo_prog)
            hx_payload = {
                'progress_update': {
                    'novo_progresso': novo_prog,
                    'log_tarefa': log_tarefa,
                    'implantacao_finalizada': finalizada,
                    'log_finalizacao': log_finalizacao
                }
            }
            resp = make_response("".join(fragments) + progress_html)
            resp.headers['HX-Trigger-After-Swap'] = json.dumps(hx_payload)
            return resp

        return jsonify({
            'ok': True,
            'updated_count': updated,
            'novo_progresso': novo_prog,
            'implantacao_finalizada': finalizada,
            'log_finalizacao': log_finalizacao
        })
    except Exception as e:
        api_logger.error(f"Erro ao alternar tarefas em lote para implantação {implantacao_id}: {e}", exc_info=True)
        return jsonify({'ok': False, 'error': f'Erro interno: {e}'}), 500

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

@api_bp.route('/adicionar_comentario/<int:tarefa_id>', methods=['POST'])
@login_required
@validate_api_origin                                    
@limiter.limit("20 per minute", key_func=lambda: g.user_email or get_remote_address())
def adicionar_comentario(tarefa_id):

    def render_hx_error(message, status_code=400):
        if request.headers.get('HX-Request') == 'true':

            html = render_template('partials/_comment_error.html', message=message)
            resp = make_response(html, 200)
            return resp
        return jsonify({'ok': False, 'error': message}), status_code

    usuario_cs_email = g.user_email

    try:
        tarefa_id = validate_integer(tarefa_id, min_value=1)
    except ValidationError as e:
        api_logger.warning(f'Invalid task ID in adicionar_comentario: {str(e)} - User: {g.user_email}')
        return render_hx_error(f'ID de tarefa inválido: {str(e)}', 400)
    
    try:
        texto = request.form.get('comentario', '')
        if texto:
            texto = sanitize_string(texto, max_length=8000, min_length=1)
        else:
            texto = ''
    except ValidationError as e:
        api_logger.warning(f'Invalid comment in adicionar_comentario: {str(e)} - User: {g.user_email}')
        return render_hx_error(f'Texto do comentário inválido: {str(e)}', 400)
    
    img_url = None

    visibilidade = (request.form.get('visibilidade', 'interno') or 'interno').strip().lower()
    if visibilidade not in ('interno', 'externo'):
        visibilidade = 'interno'

    tarefa_info = query_db(
        "SELECT i.usuario_cs, i.id as implantacao_id, t.tarefa_filho, i.status "
        "FROM tarefas t JOIN implantacoes i ON t.implantacao_id = i.id "
        "WHERE t.id = %s",
        (tarefa_id,), one=True
    )

    is_owner = tarefa_info.get('usuario_cs') == usuario_cs_email
    is_manager = g.perfil and g.perfil.get('perfil_acesso') in PERFIS_COM_GESTAO
    
    if not tarefa_info or not (is_owner or is_manager):
        return render_hx_error('Permissão negada.', 403)
        
    if tarefa_info.get('status') in ['finalizada', 'parada']:
        status_atual = tarefa_info.get('status')
        return render_hx_error(f'Não é possível adicionar comentários a implantações com status "{status_atual}".', 400)

    if 'imagem' in request.files:
        file = request.files.get('imagem')
        if file and file.filename:
            is_valid, error_msg, metadata = validate_uploaded_file(file)

            if not is_valid:
                current_app.logger.warning(f"File upload rejected: {error_msg}")
                return render_hx_error(f'Arquivo inválido: {error_msg}', 400)

            try:

                if not r2_client or not current_app.config.get('CLOUDFLARE_PUBLIC_URL'):
                    return render_hx_error('Serviço de armazenamento (R2) não está configurado para upload de imagem.', 500)
                impl_id = tarefa_info['implantacao_id']

                safe_filename = metadata['safe_filename']
                nome_base, extensao = os.path.splitext(safe_filename)
                nome_unico = f"{nome_base}_task{tarefa_id}_{int(time.time())}{extensao}"
                object_name = f"comment_images/impl_{impl_id}/task_{tarefa_id}/{nome_unico}"

                file.seek(0)
                r2_client.upload_fileobj(
                    file,
                    current_app.config['CLOUDFLARE_BUCKET_NAME'],
                    object_name,
                    ExtraArgs={'ContentType': metadata['mime_type']}
                )
                img_url = f"{current_app.config['CLOUDFLARE_PUBLIC_URL']}/{object_name}"
                current_app.logger.info(f"File uploaded to R2: {object_name} ({metadata['size_mb']} MB)")

            except (ClientError, NoCredentialsError) as upload_err:
                current_app.logger.error(f"R2 upload error: {upload_err}")
                return render_hx_error('Erro ao fazer upload da imagem para o R2.', 500)
            except Exception as e:
                current_app.logger.error(f"File processing error: {e}")
                return render_hx_error(f'Falha ao processar imagem: {e}', 500)

    if not texto and not img_url:
        return render_hx_error('O comentário não pode estar vazio se não houver imagem.', 400)

    try:
        agora = datetime.now()
        result = execute_and_fetch_one(
            "INSERT INTO comentarios (tarefa_id, usuario_cs, texto, data_criacao, imagem_url, visibilidade) "
            "VALUES (%s, %s, %s, %s, %s, %s) RETURNING id",
            (tarefa_id, usuario_cs_email, texto, agora, img_url, visibilidade)
        )
        
        novo_id = result.get('id') if result else None
        
        if not novo_id:
            raise Exception("Falha ao salvar comentário e obter ID.")

        detalhe = f"Comentário em '{tarefa_info['tarefa_filho']}':\n{texto}" if texto else f"Imagem adicionada em '{tarefa_info['tarefa_filho']}'."
        if texto and img_url:
            detalhe = f"Comentário em '{tarefa_info['tarefa_filho']}':\n{texto}\n[Imagem Adicionada]"
        logar_timeline(tarefa_info['implantacao_id'], usuario_cs_email, 'novo_comentario', detalhe)
        
        api_logger.info(f'Comment added to task {tarefa_id} by user {g.user_email}')

        novo_comentario_dados = query_db(
            """
            SELECT c.*, p.nome as usuario_nome
            FROM comentarios c
            JOIN perfil_usuario p ON c.usuario_cs = p.usuario
            WHERE c.id = %s
            """, (novo_id,), one=True
        )

        if not novo_comentario_dados:
            return render_hx_error('Falha ao recuperar o comentário após a criação.', 500)

        try:
            if visibilidade == 'externo':
                impl = query_db(
                    "SELECT i.id, i.nome_empresa, i.email_responsavel FROM implantacoes i "
                    "JOIN tarefas t ON t.implantacao_id = i.id WHERE t.id = %s",
                    (tarefa_id,), one=True
                )
                to_email = impl.get('email_responsavel') if impl else None
                if to_email:
                    from ..mail.email_utils import send_email_global
                    import threading
                    subject = f"Resumo de reunião - {impl.get('nome_empresa', 'Academia')}"
                    corpo_txt = f"Olá,\n\nCompartilhamos o resumo da reunião referente à implantação.\n\nResumo:\n{texto or ''}\n\n"
                    if img_url:
                        corpo_txt += f"Imagem: {img_url}\n\n"
                    corpo_html = f"<p>Olá,</p><p>Compartilhamos o resumo da reunião referente à implantação.</p><p><strong>Resumo:</strong></p><div>{(texto or '').replace('\n','<br>')}</div>" + (f"<p><a href='{img_url}' target='_blank'>Ver imagem</a></p>" if img_url else "")

                    from ..tasks.async_tasks import send_email_async

                    send_email_async(
                        subject=subject,
                        body_html=corpo_html,
                        recipients=[to_email],
                        reply_to=usuario_cs_email,
                        from_name=novo_comentario_dados.get('usuario_nome') or usuario_cs_email,
                        body_text=corpo_txt
                    )

                    api_logger.info(f"E-mail de comentário externo agendado para {to_email} (tarefa {tarefa_id}).")
                else:
                    api_logger.info(f"Comentário externo sem e-mail do responsável configurado para tarefa {tarefa_id}.")
        except Exception as e_mail:
            api_logger.warning(f"Falha ao agendar envio de e-mail de comentário externo: {e_mail}")

        try:
            if visibilidade == 'externo':
                if not isinstance(novo_comentario_dados, dict):
                    novo_comentario_dados = dict(novo_comentario_dados)
                novo_comentario_dados['responsavel_email'] = (impl or {}).get('email_responsavel')
                novo_comentario_dados['responsavel_nome'] = (impl or {}).get('responsavel_cliente')
        except Exception:
            pass

        item_html = render_template('partials/_comment_item.html', comentario=novo_comentario_dados)
        oob_stub = f"<div id='no-comment-{tarefa_id}' hx-swap-oob='delete'></div>"

        notice_html = ''
        try:
            if visibilidade == 'externo':
                notice_html = render_template('partials/_comment_email_notice.html', comentario=novo_comentario_dados)
        except Exception:
            notice_html = ''
        resp = make_response(item_html + oob_stub + (notice_html or ''), 200)
        try:
            payload = {
                'comment_saved': {
                    'tarefa_id': tarefa_id,
                    'comentario_id': novo_id,
                    'visibilidade': visibilidade
                }
            }
            resp.headers['HX-Trigger-After-Swap'] = json.dumps(payload)
        except Exception:
            pass
        return resp
        
    except Exception as e:
        api_logger.error(f"Erro ao salvar comentário para tarefa {tarefa_id}: {e}", exc_info=True)
        if request.headers.get('HX-Request') == 'true':
            return render_hx_error(f"Erro interno do servidor: {e}", 500)
        return jsonify({'ok': False, 'error': f"Erro interno do servidor: {e}"}), 500

@api_bp.route('/enviar_email_comentario/<int:comentario_id>', methods=['POST'])
@login_required
@validate_api_origin
@limiter.limit("20 per minute", key_func=lambda: g.user_email or get_remote_address())
def enviar_email_comentario(comentario_id):
    def render_inline_notice(comentario_ctx):
        try:
            html = render_template('partials/_comment_email_notice.html', comentario=comentario_ctx, oob=False)
            return make_response(html, 200)
        except Exception as e:
            return make_response(f"<div class='list-group-item py-2'><small class='text-danger'>Falha ao renderizar aviso: {e}</small></div>", 200)

    usuario_cs_email = g.user_email
    try:
        comentario_id = validate_integer(comentario_id, min_value=1)
    except ValidationError as e:
        api_logger.warning(f"ID inválido em enviar_email_comentario: {e} - User: {g.user_email}")
        return render_inline_notice({'email_send_status': 'error', 'email_send_error': f'ID inválido: {e}', 'tarefa_id': 0})

    try:
        dados = query_db(
            """
            SELECT c.id, c.texto, c.imagem_url, c.visibilidade, c.tarefa_id,
                   t.tarefa_filho,
                   i.id as impl_id, i.nome_empresa, i.email_responsavel, i.usuario_cs as implantacao_owner
            FROM comentarios c
            JOIN tarefas t ON c.tarefa_id = t.id
            JOIN implantacoes i ON t.implantacao_id = i.id
            WHERE c.id = %s
            """,
            (comentario_id,), one=True
        )
        if not dados:
            return render_inline_notice({'email_send_status': 'error', 'email_send_error': 'Comentário não encontrado.', 'tarefa_id': 0})

        is_owner = dados.get('usuario_cs') == usuario_cs_email if 'usuario_cs' in dados else True
        is_impl_owner = dados.get('implantacao_owner') == usuario_cs_email
        is_manager = g.perfil and g.perfil.get('perfil_acesso') in PERFIS_COM_GESTAO
        if not (is_owner or is_impl_owner or is_manager):
            security_logger.warning(f"Permissão negada ao enviar email do comentário {comentario_id} por {g.user_email}")
            return render_inline_notice({'email_send_status': 'error', 'email_send_error': 'Permissão negada.', 'tarefa_id': dados.get('tarefa_id')})

        if str(dados.get('visibilidade', 'interno')).lower() != 'externo':
            return render_inline_notice({'email_send_status': 'error', 'email_send_error': 'Comentário não é externo.', 'tarefa_id': dados.get('tarefa_id')})

        to_email = dados.get('email_responsavel')
        if not to_email:
            return render_inline_notice({'email_send_status': 'error', 'email_send_error': 'E-mail do responsável não configurado.', 'tarefa_id': dados.get('tarefa_id')})

        if not current_app.config.get('EMAIL_CONFIGURADO'):
            api_logger.warning("Tentativa de envio mas EMAIL_CONFIGURADO está falso.")
            return render_inline_notice({'email_send_status': 'error', 'email_send_error': 'Serviço de e-mail não configurado.', 'tarefa_id': dados.get('tarefa_id'), 'responsavel_email': to_email})

        subject = f"Resumo de reunião - {dados.get('nome_empresa') or 'Academia'}"
        texto = dados.get('texto') or ''
        img_url = dados.get('imagem_url')
        corpo_txt = f"Olá,\n\nCompartilhamos o resumo da reunião referente à implantação.\n\nResumo:\n{texto}\n\n"
        if img_url:
            corpo_txt += f"Imagem: {img_url}\n\n"
        corpo_html = f"<p>Olá,</p><p>Compartilhamos o resumo da reunião referente à implantação.</p><p><strong>Resumo:</strong></p><div>{texto.replace('\n','<br>')}</div>" + (f"<p><a href='{img_url}' target='_blank'>Ver imagem</a></p>" if img_url else "")

        api_logger.info(f"Tentando enviar e-mail de comentário externo (comentario_id={comentario_id}) para {to_email}")
        try:
            from ..mail.email_utils import send_email_global
            send_email_global(
                subject=subject,
                body_html=corpo_html,
                recipients=[to_email],
                reply_to=usuario_cs_email,
                from_name=g.perfil.get('nome') if (g.perfil and isinstance(g.perfil, dict)) else usuario_cs_email,
                body_text=corpo_txt
            )
            logar_timeline(dados['impl_id'], usuario_cs_email, 'email_comentario_enviado', f"E-mail enviado para responsável com resumo de '{dados['tarefa_filho']}'.")
            api_logger.info(f"E-mail enviado (comentario_id={comentario_id}) para {to_email}")
            ctx = {'email_send_status': 'ok', 'tarefa_id': dados.get('tarefa_id'), 'responsavel_email': to_email, 'responsavel_nome': None}
            return render_inline_notice(ctx)
        except Exception as e:
            api_logger.error(f"Falha ao enviar e-mail (comentario_id={comentario_id}) para {to_email}: {e}", exc_info=True)
            ctx = {'email_send_status': 'error', 'email_send_error': str(e), 'tarefa_id': dados.get('tarefa_id'), 'responsavel_email': to_email}
            return render_inline_notice(ctx)

    except Exception as e:
        api_logger.error(f"Erro inesperado em enviar_email_comentario {comentario_id}: {e}", exc_info=True)
        return render_inline_notice({'email_send_status': 'error', 'email_send_error': f'Erro interno: {e}', 'tarefa_id': 0})

@api_bp.route('/excluir_comentario/<int:comentario_id>', methods=['POST'])
@login_required
@validate_api_origin                                    
@limiter.limit("30 per minute", key_func=lambda: g.user_email or get_remote_address())
def excluir_comentario(comentario_id):
    usuario_cs_email = g.user_email

    try:
        comentario_id = validate_integer(comentario_id, min_value=1)
    except ValidationError as e:
        api_logger.warning(f'Invalid comment ID in excluir_comentario: {str(e)} - User: {g.user_email}')
        return jsonify({'ok': False, 'error': f'ID de comentário inválido: {str(e)}'}), 400

    try:
        comentario = query_db(
            """
            SELECT c.*, i.id as impl_id, t.tarefa_filho, i.usuario_cs as implantacao_owner
            FROM comentarios c 
            JOIN tarefas t ON c.tarefa_id = t.id 
            JOIN implantacoes i ON t.implantacao_id = i.id 
            WHERE c.id = %s
            """, (comentario_id,), one=True
        )
        
        is_comment_owner = comentario.get('usuario_cs') == usuario_cs_email
        is_impl_owner = comentario.get('implantacao_owner') == usuario_cs_email
        is_manager = g.perfil and g.perfil.get('perfil_acesso') in PERFIS_COM_GESTAO
        
        if not comentario or not (is_comment_owner or is_impl_owner or is_manager):
            security_logger.warning(f'Permission denied for user {g.user_email} trying to delete comment {comentario_id}')
            return jsonify({'ok': False, 'error': 'Permissão negada.'}), 403

        imagem_url = comentario.get('imagem_url')
        public_url_base = current_app.config.get('CLOUDFLARE_PUBLIC_URL')
        bucket_name = current_app.config.get('CLOUDFLARE_BUCKET_NAME')
        
        if r2_client and public_url_base and bucket_name and imagem_url and imagem_url.startswith(public_url_base):
            try:
                object_key = imagem_url.replace(f"{public_url_base}/", "")
                if object_key:
                    r2_client.delete_object(Bucket=bucket_name, Key=object_key)
                    api_logger.info(f"Objeto R2 (comentário) excluído: {object_key}")
            except ClientError as e_delete:
                api_logger.warning(f"Falha ao excluir imagem R2 (key: {object_key}). Erro: {e_delete.response['Error']['Code']}")
            except Exception as e_delete:
                 api_logger.warning(f"Falha ao excluir imagem R2 (key: {object_key}). Erro: {e_delete}")
        else:
            api_logger.warning("R2 não configurado ou variáveis ausentes; exclusão seguirá apenas no banco de dados.")

        execute_db("DELETE FROM comentarios WHERE id = %s", (comentario_id,))
        logar_timeline(comentario['impl_id'], usuario_cs_email, 'comentario_excluido', f"Comentário em '{comentario['tarefa_filho']}' foi excluído.")
        
        api_logger.info(f'Comment {comentario_id} deleted by user {g.user_email}')

        return '', 200
        
    except Exception as e:
        api_logger.error(f"Erro ao excluir comentário ID {comentario_id}: {e}", exc_info=True)
        return jsonify({'ok': False, 'error': f"Erro interno do servidor: {e}"}), 500

@api_bp.route('/excluir_tarefa/<int:tarefa_id>', methods=['POST'])
@login_required
@validate_api_origin                                    
@limiter.limit("50 per minute", key_func=lambda: g.user_email or get_remote_address())
def excluir_tarefa(tarefa_id):
    usuario_cs_email = g.user_email

    try:
        tarefa_id = validate_integer(tarefa_id, min_value=1)
    except ValidationError as e:
        api_logger.warning(f'Invalid task ID in excluir_tarefa: {str(e)} - User: {g.user_email}')
        return jsonify({'ok': False, 'error': f'ID de tarefa inválido: {str(e)}'}), 400

    try:
        tarefa = query_db(
            """
            SELECT t.tarefa_filho, i.id as impl_id, i.usuario_cs, i.status 
            FROM tarefas t 
            JOIN implantacoes i ON t.implantacao_id = i.id 
            WHERE t.id = %s
            """, (tarefa_id,), one=True
        )

        is_owner = tarefa.get('usuario_cs') == usuario_cs_email
        is_manager = g.perfil and g.perfil.get('perfil_acesso') in PERFIS_COM_GESTAO
        
        if not tarefa or not (is_owner or is_manager):
            security_logger.warning(f'Permission denied for user {g.user_email} trying to delete task {tarefa_id}')
            return jsonify({'ok': False, 'error': 'Permissão negada.'}), 403
            
        impl_id = tarefa['impl_id']
        nome_tarefa = tarefa['tarefa_filho']

        if tarefa.get('status') in ['finalizada', 'parada', 'cancelada']:
            return jsonify({'ok': False, 'error': f'Não é possível excluir tarefas de implantações com status "{tarefa.get("status")}".'}), 400

        comentarios_tarefa = query_db("SELECT id, imagem_url FROM comentarios WHERE tarefa_id = %s", (tarefa_id,))
        public_url_base = current_app.config.get('CLOUDFLARE_PUBLIC_URL')
        bucket_name = current_app.config.get('CLOUDFLARE_BUCKET_NAME')
        
        if r2_client and public_url_base and bucket_name:
            for com in comentarios_tarefa:
                imagem_url = com.get('imagem_url')
                if imagem_url and imagem_url.startswith(public_url_base):
                    try:
                        object_key = imagem_url.replace(f"{public_url_base}/", "")
                        if object_key:
                            r2_client.delete_object(Bucket=bucket_name, Key=object_key)
                            api_logger.info(f"Objeto R2 (comentário {com['id']}) excluído: {object_key}")
                    except ClientError as e_delete:
                        api_logger.warning(f"Falha ao excluir imagem R2 (key: {object_key}). Erro: {e_delete.response['Error']['Code']}")
                    except Exception as e_delete:
                        api_logger.warning(f"Falha ao excluir imagem R2 (key: {object_key}). Erro: {e_delete}")
        else:
            api_logger.warning("R2 não configurado ou variáveis ausentes; exclusão seguirá apenas no banco de dados.")

        execute_db(
            """
            DELETE FROM tarefas
            WHERE id = %s
              AND EXISTS (
                SELECT 1 FROM implantacoes i
                WHERE i.id = tarefas.implantacao_id
                  AND i.status NOT IN ('finalizada', 'parada', 'cancelada')
              )
            """,
            (tarefa_id,)
        )
        logar_timeline(impl_id, usuario_cs_email, 'tarefa_excluida', f"Tarefa '{nome_tarefa}' foi excluída.")
        
        api_logger.info(f'Task {tarefa_id} deleted by user {g.user_email}')

        finalizada, log_finalizacao = False, None
        novo_prog, _, _ = _get_progress(impl_id)

        nome = g.perfil.get('nome', usuario_cs_email)
        log_exclusao = query_db(
            "SELECT *, %s as usuario_nome FROM timeline_log "
            "WHERE implantacao_id = %s AND tipo_evento = 'tarefa_excluida' "
            "ORDER BY id DESC LIMIT 1",
            (nome, impl_id), one=True
        )
        if log_exclusao:
            log_exclusao['data_criacao'] = format_date_iso_for_json(log_exclusao.get('data_criacao'))
            
        return jsonify({
            'ok': True,
            'log_exclusao': log_exclusao,
            'novo_progresso': novo_prog,
            'implantacao_finalizada': finalizada,
            'log_finalizacao': log_finalizacao
        })
        
    except Exception as e:
        api_logger.error(f"Erro ao excluir tarefa ID {tarefa_id}: {e}", exc_info=True)
        return jsonify({'ok': False, 'error': f"Erro interno do servidor: {e}"}), 500

@api_bp.route('/reordenar_tarefas', methods=['POST'])
@login_required
@validate_api_origin                                    
def reordenar_tarefas():
    usuario_cs_email = g.user_email
    try:
        data = request.get_json()
        impl_id = data.get('implantacao_id')
        tarefa_pai = data.get('tarefa_pai')             
        nova_ordem_ids = data.get('ordem')                             
        
        if not all([impl_id, tarefa_pai, isinstance(nova_ordem_ids, list)]):
            return jsonify({'ok': False, 'error': 'Dados inválidos.'}), 400
            
        impl = query_db("SELECT id, usuario_cs FROM implantacoes WHERE id = %s", (impl_id,), one=True)
        is_owner = impl and impl.get('usuario_cs') == usuario_cs_email
        is_manager = g.perfil and g.perfil.get('perfil_acesso') in PERFIS_COM_GESTAO
        
        if not (is_owner or is_manager):
            security_logger.warning(f'Permission denied for user {g.user_email} trying to reorder tasks in implantation {impl_id}')
            return jsonify({'ok': False, 'error': 'Permissão negada.'}), 403
        
        for index, tarefa_id in enumerate(nova_ordem_ids, 1):
            execute_db(
                "UPDATE tarefas SET ordem = %s WHERE id = %s AND implantacao_id = %s AND tarefa_pai = %s",
                (index, tarefa_id, impl_id, tarefa_pai)
            )
            
        logar_timeline(impl_id, usuario_cs_email, 'tarefas_reordenadas', f"A ordem das tarefas no módulo '{tarefa_pai}' foi alterada.")
        
        api_logger.info(f'Tasks reordered in module {tarefa_pai} of implantation {impl_id} by user {g.user_email}')
        
        nome = g.perfil.get('nome', usuario_cs_email)
        log_reordenar = query_db(
            "SELECT *, %s as usuario_nome FROM timeline_log "
            "WHERE implantacao_id = %s AND tipo_evento = 'tarefas_reordenadas' "
            "ORDER BY id DESC LIMIT 1",
            (nome, impl_id), one=True
        )
        if log_reordenar:
            log_reordenar['data_criacao'] = format_date_iso_for_json(log_reordenar.get('data_criacao'))
            
        return jsonify({'ok': True, 'log_reordenar': log_reordenar})
        
    except Exception as e:
        api_logger.error(f"Erro ao reordenar tarefas: {e}", exc_info=True)
        return jsonify({'ok': False, 'error': f"Erro interno do servidor: {e}"}), 500

@api_bp.route('/excluir_tarefas_modulo', methods=['POST'])
@login_required
@validate_api_origin                                    
def excluir_tarefas_modulo():
    """Exclui todas as tarefas de um módulo (tarefa_pai) específico."""
    usuario_cs_email = g.user_email
    data = request.get_json()
    impl_id = data.get('implantacao_id')
    tarefa_pai = data.get('tarefa_pai')             

    if not all([impl_id, tarefa_pai]):
        return jsonify({'ok': False, 'error': 'Dados inválidos (ID da implantação e Módulo são obrigatórios).'}), 400

    impl = query_db("SELECT id, nome_empresa, status, usuario_cs FROM implantacoes WHERE id = %s", (impl_id,), one=True)
    is_owner = impl and impl.get('usuario_cs') == usuario_cs_email
    is_manager = g.perfil and g.perfil.get('perfil_acesso') in PERFIS_COM_GESTAO
    
    if not (is_owner or is_manager):
        security_logger.warning(f'Permission denied for user {g.user_email} trying to delete tasks from module {tarefa_pai} in implantation {impl_id}')
        return jsonify({'ok': False, 'error': 'Permissão negada ou implantação não encontrada.'}), 403

    st = impl.get('status')
    if st in ['finalizada', 'parada', 'cancelada']:
        return jsonify({'ok': False, 'error': f'Não é possível excluir tarefas de implantações com status "{st}".'}), 400

    try:

        comentarios_img = query_db(
            """
            SELECT c.imagem_url
            FROM comentarios c
            JOIN tarefas t ON c.tarefa_id = t.id
            WHERE t.implantacao_id = %s AND t.tarefa_pai = %s AND c.imagem_url IS NOT NULL
            """, (impl_id, tarefa_pai)
        )
        
        public_url_base = current_app.config.get('CLOUDFLARE_PUBLIC_URL')
        bucket_name = current_app.config.get('CLOUDFLARE_BUCKET_NAME')

        if r2_client and public_url_base and bucket_name:
            for c in comentarios_img:
                imagem_url = c.get('imagem_url')
                if imagem_url and imagem_url.startswith(public_url_base):
                    try:
                        object_key = imagem_url.replace(f"{public_url_base}/", "")
                        if object_key:
                            r2_client.delete_object(Bucket=bucket_name, Key=object_key)
                            api_logger.info(f"Objeto R2 (módulo {tarefa_pai}) excluído: {object_key}")
                    except ClientError as e_delete:
                        api_logger.warning(f"Falha ao excluir imagem R2 (key: {object_key}). Erro: {e_delete.response['Error']['Code']}")
                    except Exception as e_delete:
                        api_logger.warning(f"Falha ao excluir imagem R2 (key: {object_key}). Erro: {e_delete}")
        else:
            api_logger.warning("R2 não configurado ou variáveis ausentes; exclusão seguirá apenas no banco de dados.")
        
        execute_db(
            """
            DELETE FROM tarefas
            WHERE implantacao_id = %s AND tarefa_pai = %s
              AND EXISTS (
                SELECT 1 FROM implantacoes i
                WHERE i.id = %s
                  AND i.status NOT IN ('finalizada', 'parada', 'cancelada')
              )
            """,
            (impl_id, tarefa_pai, impl_id)
        )

        logar_timeline(impl_id, usuario_cs_email, 'modulo_excluido', f"Todas as tarefas do módulo '{tarefa_pai}' foram excluídas.")
        
        api_logger.info(f'All tasks from module {tarefa_pai} in implantation {impl_id} deleted by user {g.user_email}')

        finalizada, log_finalizacao = False, None
        novo_prog, _, _ = _get_progress(impl_id)

        nome = g.perfil.get('nome', usuario_cs_email)
        log_exclusao = query_db(
            "SELECT *, %s as usuario_nome FROM timeline_log "
            "WHERE implantacao_id = %s AND tipo_evento = 'modulo_excluido' "
            "ORDER BY id DESC LIMIT 1",
            (nome, impl_id), one=True
        )
        if log_exclusao:

            log_exclusao['data_criacao'] = format_date_iso_for_json(log_exclusao.get('data_criacao'))

        return jsonify({
            'ok': True,
            'log_exclusao_modulo': log_exclusao,
            'novo_progresso': novo_prog,
            'implantacao_finalizada': finalizada,
            'log_finalizacao': log_finalizacao
        })

    except Exception as e:
        api_logger.error(f'Erro ao excluir tarefas do módulo {tarefa_pai} (Impl. ID {impl_id}): {e} - User: {g.user_email}', exc_info=True)
        return jsonify({'ok': False, 'error': f"Erro interno do servidor: {e}"}), 500
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
        novo_prog, _, _ = _get_progress(row['implantacao_id'])
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
        novo_prog, _, _ = _get_progress(row['implantacao_id'])
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
