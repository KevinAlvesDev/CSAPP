import os
import time
from datetime import datetime

from flask import Blueprint, current_app, g, jsonify, make_response, render_template, request, url_for
from flask_limiter.util import get_remote_address

from ..blueprints.auth import login_required
from ..common.file_validation import validate_uploaded_file
from ..common.utils import format_date_iso_for_json
from ..common.validation import ValidationError, sanitize_string, validate_integer
from ..config.logging_config import api_logger
from ..constants import PERFIS_COM_GESTAO
from ..core.extensions import limiter, r2_client
from ..db import execute_and_fetch_one, execute_db, logar_timeline, query_db
from ..security.api_security import validate_api_origin

api_h_bp = Blueprint('api_h', __name__, url_prefix='/api')

COLUNA_ID_MAP = {
    'tarefa': 'checklist_item_id',
    'subtarefa': 'checklist_item_id'
}

@api_h_bp.before_request
def _api_origin_guard():
    return validate_api_origin(lambda: None)()

@api_h_bp.route('/adicionar_comentario_h/<string:tipo>/<int:item_id>', methods=['POST'])
@login_required
@validate_api_origin
@limiter.limit("20 per minute", key_func=lambda: g.user_email or get_remote_address())
def adicionar_comentario_h(tipo, item_id):
    def render_hx_error(message, status_code=400):
        if request.headers.get('HX-Request') == 'true':
            html = render_template('partials/_comment_error.html', message=message)
            resp = make_response(html, 200)
            return resp
        return jsonify({'ok': False, 'error': message}), status_code

    usuario_cs_email = g.user_email

    try:
        item_id = validate_integer(item_id, min_value=1)
    except ValidationError as e:
        return render_hx_error(f'ID inválido: {str(e)}', 400)

    if tipo not in ('tarefa', 'subtarefa'):
        return render_hx_error('Tipo inválido. Deve ser "tarefa" ou "subtarefa".', 400)

    coluna_id = 'checklist_item_id'

    try:
        texto = request.form.get('comentario', '')
        if texto:
            texto = sanitize_string(texto, max_length=8000, min_length=1)
        else:
            texto = ''
    except ValidationError as e:
        return render_hx_error(f'Texto do comentário inválido: {str(e)}', 400)

    img_url = None
    visibilidade = (request.form.get('visibilidade', 'interno') or 'interno').strip().lower()
    if visibilidade not in ('interno', 'externo'):
        visibilidade = 'interno'

    if tipo == 'tarefa':
        info = query_db(
            """
            SELECT ci.title as item_nome, i.usuario_cs, i.id as implantacao_id, i.status, i.nome_empresa, i.email_responsavel, i.responsavel_cliente
            FROM checklist_items ci
            JOIN implantacoes i ON ci.implantacao_id = i.id
            WHERE ci.id = %s AND ci.tipo_item = 'tarefa'
            """, (item_id,), one=True
        )
    else:
        info = query_db(
            """
            SELECT ci.title as item_nome, i.usuario_cs, i.id as implantacao_id, i.status, i.nome_empresa, i.email_responsavel, i.responsavel_cliente
            FROM checklist_items ci
            JOIN implantacoes i ON ci.implantacao_id = i.id
            WHERE ci.id = %s AND ci.tipo_item = 'subtarefa'
            """, (item_id,), one=True
        )

    if not info:
        return render_hx_error('Item não encontrado.', 404)

    is_owner = info.get('usuario_cs') == usuario_cs_email
    is_manager = g.perfil and g.perfil.get('perfil_acesso') in PERFIS_COM_GESTAO

    if not (is_owner or is_manager):
        return render_hx_error('Permissão negada.', 403)

    if info.get('status') in ['finalizada', 'parada']:
        return render_hx_error(f'Não é possível adicionar comentários a implantações com status "{info.get("status")}".', 400)

    if 'imagem' in request.files:
        file = request.files.get('imagem')
        if file and file.filename:
            is_valid, error_msg, metadata = validate_uploaded_file(file)
            if not is_valid:
                return render_hx_error(f'Arquivo inválido: {error_msg}', 400)

            try:
                if not r2_client or not current_app.config.get('CLOUDFLARE_PUBLIC_URL'):
                    return render_hx_error('Serviço de armazenamento (R2) não configurado.', 500)

                impl_id = info['implantacao_id']
                safe_filename = metadata['safe_filename']
                nome_base, extensao = os.path.splitext(safe_filename)
                nome_unico = f"{nome_base}_{tipo}{item_id}_{int(time.time())}{extensao}"
                object_name = f"comment_images/impl_{impl_id}/{tipo}_{item_id}/{nome_unico}"

                file.seek(0)
                r2_client.upload_fileobj(
                    file,
                    current_app.config['CLOUDFLARE_BUCKET_NAME'],
                    object_name,
                    ExtraArgs={'ContentType': metadata['mime_type']}
                )
                img_url = f"{current_app.config['CLOUDFLARE_PUBLIC_URL']}/{object_name}"

            except Exception as e:
                api_logger.error(f"File upload error: {e}")
                return render_hx_error(f'Falha ao processar imagem: {e}', 500)

    if not texto and not img_url:
        return render_hx_error('O comentário não pode estar vazio se não houver imagem.', 400)

    try:
        agora = datetime.now()

        try:
            from project.database.db_pool import get_db_connection
            conn_check, db_type_check = get_db_connection()
            if db_type_check == 'sqlite':
                cursor_check = conn_check.cursor()
                cursor_check.execute("PRAGMA table_info(comentarios_h)")
                colunas_existentes = [row[1] for row in cursor_check.fetchall()]
                if 'checklist_item_id' not in colunas_existentes:
                    cursor_check.execute("ALTER TABLE comentarios_h ADD COLUMN checklist_item_id INTEGER")
                    conn_check.commit()
                conn_check.close()
        except Exception:
            pass

        result = execute_and_fetch_one(
            "INSERT INTO comentarios_h (checklist_item_id, usuario_cs, texto, data_criacao, imagem_url, visibilidade) "
            "VALUES (%s, %s, %s, %s, %s, %s) RETURNING id",
            (item_id, usuario_cs_email, texto, agora, img_url, visibilidade)
        )

        novo_id = result.get('id') if result else None
        if not novo_id:
            # Fallback para SQLite
            if current_app.config.get('USE_SQLITE_LOCALLY'):
                execute_db(
                    "INSERT INTO comentarios_h (checklist_item_id, usuario_cs, texto, data_criacao, imagem_url, visibilidade) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (item_id, usuario_cs_email, texto, agora, img_url, visibilidade)
                )
                novo_id = query_db("SELECT last_insert_rowid() as id", one=True)['id']

        detalhe = f"Comentário criado — {info['item_nome']} <span class=\"d-none related-id\" data-item-id=\"{item_id}\"></span>"
        logar_timeline(info['implantacao_id'], usuario_cs_email, 'novo_comentario', detalhe)

        novo_comentario_dados = query_db(
            """
            SELECT c.*, p.nome as usuario_nome
            FROM comentarios_h c
            LEFT JOIN perfil_usuario p ON c.usuario_cs = p.usuario
            WHERE c.id = %s
            """, (novo_id,), one=True
        )

        if not novo_comentario_dados:
             return render_hx_error('Erro ao recuperar comentário.', 500)

        if visibilidade == 'externo':
             pass

        novo_comentario_dados['delete_url'] = url_for('api_h.excluir_comentario_h', comentario_id=novo_id)

        if request.headers.get('HX-Request') == 'true':
            item_html = render_template('partials/_comment_item.html', comentario=novo_comentario_dados)
            oob_stub = f"<div id='no-comment-{tipo}-{item_id}' hx-swap-oob='delete'></div>"
            resp = make_response(item_html + oob_stub, 200)
            resp.headers['Content-Type'] = 'text/html; charset=utf-8'
            return resp

        if novo_comentario_dados.get('data_criacao'):
            novo_comentario_dados['data_criacao'] = format_date_iso_for_json(novo_comentario_dados['data_criacao'])

        resp = jsonify({
            'ok': True,
            'success': True,
            'comentario': novo_comentario_dados
        })
        resp.headers['Content-Type'] = 'application/json'
        return resp

    except Exception as e:
        api_logger.error(f"Erro ao salvar comentário_h: {e}", exc_info=True)
        return render_hx_error(f"Erro interno: {e}", 500)

@api_h_bp.route('/listar_comentarios_h/<string:tipo>/<int:item_id>', methods=['GET'])
@login_required
@validate_api_origin
def listar_comentarios_h(tipo, item_id):
    """Lista comentários de uma tarefa ou subtarefa hierárquica"""
    try:
        item_id = validate_integer(item_id, min_value=1)
    except ValidationError as e:
        return jsonify({'ok': False, 'error': f'ID inválido: {str(e)}'}), 400

    if tipo not in ('tarefa', 'subtarefa'):
        return jsonify({'ok': False, 'error': 'Tipo inválido. Deve ser "tarefa" ou "subtarefa".'}), 400

    coluna_id = 'checklist_item_id'

    try:
        impl_info = {}
        try:
            if tipo == 'tarefa':
                impl_info = query_db(
                    """
                    SELECT i.email_responsavel
                    FROM checklist_items ci
                    JOIN implantacoes i ON ci.implantacao_id = i.id
                    WHERE ci.id = %s AND ci.tipo_item = 'tarefa'
                    """, (item_id,), one=True
                ) or {}
            else:
                impl_info = query_db(
                    """
                    SELECT i.email_responsavel
                    FROM checklist_items ci
                    JOIN implantacoes i ON ci.implantacao_id = i.id
                    WHERE ci.id = %s AND ci.tipo_item = 'subtarefa'
                    """, (item_id,), one=True
                ) or {}
        except Exception as e:
            api_logger.warning(f"Erro ao buscar email_responsavel: {e}")
            impl_info = {}

        comentarios = query_db(
            """
            SELECT c.id, c.texto, c.usuario_cs, c.data_criacao, c.imagem_url, c.visibilidade,
                   p.nome as usuario_nome
            FROM comentarios_h c
            LEFT JOIN perfil_usuario p ON c.usuario_cs = p.usuario
            WHERE c.checklist_item_id = %s
            ORDER BY c.data_criacao DESC
            """,
            (item_id,)
        ) or []

        email_resp = impl_info.get('email_responsavel', '')
        for c in comentarios:
            c['email_responsavel'] = email_resp
            if c.get('data_criacao'):
                c['data_criacao'] = format_date_iso_for_json(c['data_criacao'])

        return jsonify({'ok': True, 'success': True, 'comentarios': comentarios}), 200

    except Exception as e:
        api_logger.error(f"Erro ao listar comentários_h: {e}", exc_info=True)
        return jsonify({'ok': False, 'error': str(e)}), 500


@api_h_bp.route('/excluir_comentario_h/<int:comentario_id>', methods=['POST'])
@login_required
@validate_api_origin
def excluir_comentario_h(comentario_id):
    usuario_cs_email = g.user_email
    try:
        comentario = query_db(
            """
            SELECT c.*, 
                   ci.title as item_nome,
                   i.id as impl_id, i.usuario_cs as implantacao_owner
            FROM comentarios_h c
            LEFT JOIN checklist_items ci ON c.checklist_item_id = ci.id
            LEFT JOIN implantacoes i ON ci.implantacao_id = i.id
            WHERE c.id = %s
            """, (comentario_id,), one=True
        )

        if not comentario:
            return jsonify({'ok': False, 'error': 'Comentário não encontrado'}), 404

        is_owner = comentario.get('usuario_cs') == usuario_cs_email
        is_impl_owner = comentario.get('implantacao_owner') == usuario_cs_email
        is_manager = g.perfil and g.perfil.get('perfil_acesso') in PERFIS_COM_GESTAO

        if not (is_owner or is_impl_owner or is_manager):
            return jsonify({'ok': False, 'error': 'Permissão negada'}), 403

        # Capture related checklist item id BEFORE deletion
        try:
            item_id_row = query_db("SELECT checklist_item_id FROM comentarios_h WHERE id = %s", (comentario_id,), one=True)
        except Exception:
            item_id_row = None
        execute_db("DELETE FROM comentarios_h WHERE id = %s", (comentario_id,))
        related_id = item_id_row['checklist_item_id'] if (item_id_row and isinstance(item_id_row, dict)) else (item_id_row[0] if item_id_row else None)
        detalhe = f"Comentário excluído — {comentario.get('item_nome','')} <span class=\"d-none related-id\" data-item-id=\"{related_id or ''}\"></span>"
        logar_timeline(comentario['impl_id'], usuario_cs_email, 'comentario_excluido', detalhe)

        return jsonify({'ok': True, 'success': True}), 200
    except Exception as e:
        api_logger.error(f"Erro ao excluir comentario_h: {e}")
        return jsonify({'ok': False, 'error': str(e)}), 500

@api_h_bp.route('/enviar_email_comentario_h/<int:comentario_id>', methods=['POST'])
@login_required
@validate_api_origin
@limiter.limit("20 per minute", key_func=lambda: g.user_email or get_remote_address())
def enviar_email_comentario_h(comentario_id):
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
        return render_inline_notice({'email_send_status': 'error', 'email_send_error': f'ID inválido: {e}', 'tarefa_id': 0})

    try:
        dados = query_db(
            """
            SELECT c.id, c.texto, c.imagem_url, c.visibilidade, 
                   ci.id as tarefa_id,
                   ci.title as tarefa_filho,
                   i.id as impl_id, i.nome_empresa, i.email_responsavel, i.usuario_cs as implantacao_owner
            FROM comentarios_h c
            LEFT JOIN checklist_items ci ON c.checklist_item_id = ci.id
            LEFT JOIN implantacoes i ON ci.implantacao_id = i.id
            WHERE c.id = %s
            """,
            (comentario_id,), one=True
        )
        if not dados:
            return render_inline_notice({'email_send_status': 'error', 'email_send_error': 'Comentário não encontrado.', 'tarefa_id': 0})

        dados = query_db(
            """
            SELECT c.id, c.texto, c.imagem_url, c.visibilidade, c.usuario_cs,
                   ci.id as tarefa_id, 
                   ci.title as tarefa_filho,
                   i.id as impl_id, i.nome_empresa, i.email_responsavel, i.usuario_cs as implantacao_owner
            FROM comentarios_h c
            LEFT JOIN checklist_items ci ON c.checklist_item_id = ci.id
            LEFT JOIN implantacoes i ON ci.implantacao_id = i.id
            WHERE c.id = %s
            """,
            (comentario_id,), one=True
        )

        is_owner = dados.get('usuario_cs') == usuario_cs_email
        is_impl_owner = dados.get('implantacao_owner') == usuario_cs_email
        is_manager = g.perfil and g.perfil.get('perfil_acesso') in PERFIS_COM_GESTAO

        if not (is_owner or is_impl_owner or is_manager):
            return render_inline_notice({'email_send_status': 'error', 'email_send_error': 'Permissão negada.', 'tarefa_id': dados.get('tarefa_id')})

        if str(dados.get('visibilidade', 'interno')).lower() != 'externo':
            return render_inline_notice({'email_send_status': 'error', 'email_send_error': 'Comentário não é externo.', 'tarefa_id': dados.get('tarefa_id')})

        to_email = dados.get('email_responsavel')
        if not to_email:
            return render_inline_notice({'email_send_status': 'error', 'email_send_error': 'E-mail do responsável não configurado.', 'tarefa_id': dados.get('tarefa_id')})

        if not current_app.config.get('EMAIL_CONFIGURADO'):
            return render_inline_notice({'email_send_status': 'error', 'email_send_error': 'Serviço de e-mail não configurado.', 'tarefa_id': dados.get('tarefa_id'), 'responsavel_email': to_email})

        subject = f"Resumo de reunião - {dados.get('nome_empresa') or 'Academia'}"
        texto = dados.get('texto') or ''
        img_url = dados.get('imagem_url')
        corpo_txt = f"Olá,\n\nCompartilhamos o resumo da reunião referente à implantação.\n\nResumo:\n{texto}\n\n"
        if img_url:
            corpo_txt += f"Imagem: {img_url}\n\n"
        corpo_html = f"<p>Olá,</p><p>Compartilhamos o resumo da reunião referente à implantação.</p><p><strong>Resumo:</strong></p><div>{texto.replace('\n','<br>')}</div>" + (f"<p><a href='{img_url}' target='_blank'>Ver imagem</a></p>" if img_url else "")

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
            ctx = {'email_send_status': 'ok', 'tarefa_id': dados.get('tarefa_id'), 'responsavel_email': to_email, 'responsavel_nome': None}
            return render_inline_notice(ctx)
        except Exception as e:
            api_logger.error(f"Falha ao enviar e-mail: {e}", exc_info=True)
            ctx = {'email_send_status': 'error', 'email_send_error': str(e), 'tarefa_id': dados.get('tarefa_id'), 'responsavel_email': to_email}
            return render_inline_notice(ctx)

    except Exception as e:
        api_logger.error(f"Erro inesperado em enviar_email_comentario_h {comentario_id}: {e}", exc_info=True)
        return render_inline_notice({'email_send_status': 'error', 'email_send_error': f'Erro interno: {e}', 'tarefa_id': 0})
