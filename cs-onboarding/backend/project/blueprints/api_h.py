from flask import Blueprint, request, jsonify, g, current_app, render_template, make_response, url_for
from datetime import datetime
import os
import time
import json
from werkzeug.utils import secure_filename
from botocore.exceptions import ClientError, NoCredentialsError

from ..blueprints.auth import login_required
from ..db import query_db, execute_db, logar_timeline, execute_and_fetch_one
from ..core.extensions import r2_client, limiter
from ..common.utils import allowed_file, format_date_iso_for_json, format_date_br
from ..common.file_validation import validate_uploaded_file
from ..constants import PERFIS_COM_GESTAO
from ..common.validation import validate_integer, sanitize_string, ValidationError
from ..config.logging_config import api_logger, security_logger
from flask_limiter.util import get_remote_address
from ..security.api_security import validate_api_origin

api_h_bp = Blueprint('api_h', __name__, url_prefix='/api')

# Mapeamento de tipo para coluna de ID (whitelist explícita)
COLUNA_ID_MAP = {
    'tarefa': 'tarefa_h_id',
    'subtarefa': 'subtarefa_h_id'
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
    
    # Validar tipo usando whitelist explícita
    coluna_id = COLUNA_ID_MAP.get(tipo)
    if not coluna_id:
        return render_hx_error('Tipo inválido. Deve ser "tarefa" ou "subtarefa".', 400)

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
            SELECT th.nome as item_nome, i.usuario_cs, i.id as implantacao_id, i.status, i.nome_empresa, i.email_responsavel, i.responsavel_cliente
            FROM tarefas_h th
            JOIN grupos g ON th.grupo_id = g.id
            JOIN fases f ON g.fase_id = f.id
            JOIN implantacoes i ON f.implantacao_id = i.id
            WHERE th.id = %s
            """, (item_id,), one=True
        )
    else:
        info = query_db(
            """
            SELECT sh.nome as item_nome, i.usuario_cs, i.id as implantacao_id, i.status, i.nome_empresa, i.email_responsavel, i.responsavel_cliente
            FROM subtarefas_h sh
            JOIN tarefas_h th ON sh.tarefa_id = th.id
            JOIN grupos g ON th.grupo_id = g.id
            JOIN fases f ON g.fase_id = f.id
            JOIN implantacoes i ON f.implantacao_id = i.id
            WHERE sh.id = %s
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
        # coluna_id já foi definida na validação acima
        
        result = execute_and_fetch_one(
            f"INSERT INTO comentarios_h ({coluna_id}, usuario_cs, texto, data_criacao, imagem_url, visibilidade) "
            "VALUES (%s, %s, %s, %s, %s, %s) RETURNING id",
            (item_id, usuario_cs_email, texto, agora, img_url, visibilidade)
        )
        
        novo_id = result.get('id') if result else None
        if not novo_id:
            # Fallback para SQLite
            if current_app.config.get('USE_SQLITE_LOCALLY'):
                execute_db(
                    f"INSERT INTO comentarios_h ({coluna_id}, usuario_cs, texto, data_criacao, imagem_url, visibilidade) "
                    "VALUES (%s, %s, %s, %s, %s, %s)",
                    (item_id, usuario_cs_email, texto, agora, img_url, visibilidade)
                )
                novo_id = query_db("SELECT last_insert_rowid() as id", one=True)['id']

        detalhe = f"Comentário em '{info['item_nome']}':\n{texto}"
        if img_url:
            detalhe += "\n[Imagem Adicionada]"
        logar_timeline(info['implantacao_id'], usuario_cs_email, 'novo_comentario', detalhe)
        
        # Recuperar comentário para renderizar
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

        # Envio de e-mail (simplificado)
        if visibilidade == 'externo':
             # Lógica de e-mail aqui (similar ao anterior)
             pass

        novo_comentario_dados['delete_url'] = url_for('api_h.excluir_comentario_h', comentario_id=novo_id)

        # Se for requisição HX-Request, retornar HTML
        if request.headers.get('HX-Request') == 'true':
            item_html = render_template('partials/_comment_item.html', comentario=novo_comentario_dados)
            oob_stub = f"<div id='no-comment-{tipo}-{item_id}' hx-swap-oob='delete'></div>"
            resp = make_response(item_html + oob_stub, 200)
            resp.headers['Content-Type'] = 'text/html; charset=utf-8'
            return resp
        
        # Caso contrário, retornar JSON
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
    
    # Validar tipo usando whitelist explícita
    coluna_id = COLUNA_ID_MAP.get(tipo)
    if not coluna_id:
        return jsonify({'ok': False, 'error': 'Tipo inválido. Deve ser "tarefa" ou "subtarefa".'}), 400
    
    try:
        
        # Obter email do responsável da implantação
        impl_info = {}
        try:
            if tipo == 'tarefa':
                impl_info = query_db(
                    """
                    SELECT i.email_responsavel
                    FROM tarefas_h th
                    JOIN grupos g ON th.grupo_id = g.id
                    JOIN fases f ON g.fase_id = f.id
                    JOIN implantacoes i ON f.implantacao_id = i.id
                    WHERE th.id = %s
                    """, (item_id,), one=True
                ) or {}
            else:
                impl_info = query_db(
                    """
                    SELECT i.email_responsavel
                    FROM subtarefas_h sh
                    JOIN tarefas_h th ON sh.tarefa_id = th.id
                    JOIN grupos g ON th.grupo_id = g.id
                    JOIN fases f ON g.fase_id = f.id
                    JOIN implantacoes i ON f.implantacao_id = i.id
                    WHERE sh.id = %s
                    """, (item_id,), one=True
                ) or {}
        except Exception as e:
            api_logger.warning(f"Erro ao buscar email_responsavel: {e}")
            impl_info = {}
        
        comentarios = query_db(
            f"""
            SELECT c.id, c.texto, c.usuario_cs, c.data_criacao, c.imagem_url, c.visibilidade,
                   p.nome as usuario_nome
            FROM comentarios_h c
            LEFT JOIN perfil_usuario p ON c.usuario_cs = p.usuario
            WHERE c.{coluna_id} = %s
            ORDER BY c.data_criacao DESC
            """,
            (item_id,)
        ) or []
        
        # Adicionar email do responsável a cada comentário
        email_resp = impl_info.get('email_responsavel', '')
        for c in comentarios:
            c['email_responsavel'] = email_resp
            # Formatar data
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
                   COALESCE(th.nome, sh.nome) as item_nome,
                   i.id as impl_id, i.usuario_cs as implantacao_owner
            FROM comentarios_h c
            LEFT JOIN tarefas_h th ON c.tarefa_h_id = th.id
            LEFT JOIN subtarefas_h sh ON c.subtarefa_h_id = sh.id
            LEFT JOIN grupos g ON th.grupo_id = g.id
            LEFT JOIN tarefas_h th_sub ON sh.tarefa_id = th_sub.id
            LEFT JOIN grupos g_sub ON th_sub.grupo_id = g_sub.id
            LEFT JOIN fases f ON COALESCE(g.fase_id, g_sub.fase_id) = f.id
            LEFT JOIN implantacoes i ON f.implantacao_id = i.id
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
        
        execute_db("DELETE FROM comentarios_h WHERE id = %s", (comentario_id,))
        logar_timeline(comentario['impl_id'], usuario_cs_email, 'comentario_excluido', f"Comentário em '{comentario['item_nome']}' excluído.")
        
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
                   COALESCE(th.id, sh.tarefa_id) as tarefa_id, -- Approximation for target ID
                   COALESCE(th.nome, sh.nome) as tarefa_filho,
                   i.id as impl_id, i.nome_empresa, i.email_responsavel, i.usuario_cs as implantacao_owner
            FROM comentarios_h c
            LEFT JOIN tarefas_h th ON c.tarefa_h_id = th.id
            LEFT JOIN subtarefas_h sh ON c.subtarefa_h_id = sh.id
            LEFT JOIN grupos g ON th.grupo_id = g.id
            LEFT JOIN tarefas_h th_sub ON sh.tarefa_id = th_sub.id
            LEFT JOIN grupos g_sub ON th_sub.grupo_id = g_sub.id
            LEFT JOIN fases f ON COALESCE(g.fase_id, g_sub.fase_id) = f.id
            LEFT JOIN implantacoes i ON f.implantacao_id = i.id
            WHERE c.id = %s
            """,
            (comentario_id,), one=True
        )
        if not dados:
            return render_inline_notice({'email_send_status': 'error', 'email_send_error': 'Comentário não encontrado.', 'tarefa_id': 0})

        dados = query_db(
            """
            SELECT c.id, c.texto, c.imagem_url, c.visibilidade, c.usuario_cs,
                   COALESCE(th.id, sh.tarefa_id) as tarefa_id, 
                   COALESCE(th.nome, sh.nome) as tarefa_filho,
                   i.id as impl_id, i.nome_empresa, i.email_responsavel, i.usuario_cs as implantacao_owner
            FROM comentarios_h c
            LEFT JOIN tarefas_h th ON c.tarefa_h_id = th.id
            LEFT JOIN subtarefas_h sh ON c.subtarefa_h_id = sh.id
            LEFT JOIN grupos g ON th.grupo_id = g.id
            LEFT JOIN tarefas_h th_sub ON sh.tarefa_id = th_sub.id
            LEFT JOIN grupos g_sub ON th_sub.grupo_id = g_sub.id
            LEFT JOIN fases f ON COALESCE(g.fase_id, g_sub.fase_id) = f.id
            LEFT JOIN implantacoes i ON f.implantacao_id = i.id
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
