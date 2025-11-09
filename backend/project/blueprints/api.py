# app2/CSAPP/project/blueprints/api.py

from flask import Blueprint, request, jsonify, g, current_app, render_template
from datetime import datetime
import os
import time
from werkzeug.utils import secure_filename
from botocore.exceptions import ClientError, NoCredentialsError

from ..blueprints.auth import login_required
# --- INÍCIO DA CORREÇÃO (BUG 4) ---
# Importa a nova função 'execute_and_fetch_one'
from ..db import query_db, execute_db, logar_timeline, execute_and_fetch_one
# --- FIM DA CORREÇÃO (BUG 4) ---
from ..extensions import r2_client # <--- CORREÇÃO: Importação faltante
# --- INÍCIO DA CORREÇÃO (Refatoração) ---
# Importa da camada de domínio/serviço específica
from ..domain.implantacao_service import auto_finalizar_implantacao, _get_progress 
# --- FIM DA CORREÇÃO ---
from ..utils import allowed_file, format_date_iso_for_json, format_date_br
from ..constants import PERFIS_COM_GESTAO
from ..validation import validate_integer, sanitize_string, validate_email, ValidationError
from ..logging_config import api_logger, security_logger

api_bp = Blueprint('api', __name__, url_prefix='/api') # Prefixo /api

@api_bp.route('/toggle_tarefa/<int:tarefa_id>', methods=['POST'])
@login_required
def toggle_tarefa(tarefa_id):
    usuario_cs_email = g.user_email
    
    # Valida o ID da tarefa
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
            
        if tarefa.get('status') in ['finalizada', 'parada', 'futura']:
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
        
        auto_finalizar_implantacao(tarefa['implantacao_id'], usuario_cs_email)
        
        # Após a atualização, buscamos novamente os dados completos da tarefa para re-renderizar o template
        tarefa_atualizada = query_db("SELECT * FROM tarefas WHERE id = %s", (tarefa_id,), one=True)
        
        # Buscamos os comentários associados, pois o template parcial precisa deles
        comentarios = query_db(
            """
            SELECT c.*, p.nome as usuario_nome, p.foto_url 
            FROM comentarios c 
            JOIN perfil_usuario p ON c.usuario_cs = p.usuario 
            WHERE c.tarefa_id = %s 
            ORDER BY c.data_criacao ASC
            """, (tarefa_id,)
        )
        
        # Adicionamos os comentários formatados à tarefa
        tarefa_atualizada['comentarios'] = []
        for comentario in comentarios:
            comentario['data_criacao_fmt_d'] = format_date_br(comentario['data_criacao'])
            tarefa_atualizada['comentarios'].append(comentario)

        # Renderiza apenas o template do item da tarefa e o retorna
        return render_template('partials/_task_item.html', tarefa=tarefa_atualizada)
        
    except Exception as e:
        print(f"ERRO ao alternar tarefa ID {tarefa_id}: {e}")
        return jsonify({'ok': False, 'error': f"Erro interno: {e}"}), 500

@api_bp.route('/adicionar_comentario/<int:tarefa_id>', methods=['POST'])
@login_required
def adicionar_comentario(tarefa_id):
    usuario_cs_email = g.user_email
    
    # Valida o ID da tarefa
    try:
        tarefa_id = validate_integer(tarefa_id, min_value=1)
    except ValidationError as e:
        api_logger.warning(f'Invalid task ID in adicionar_comentario: {str(e)} - User: {g.user_email}')
        return jsonify({'ok': False, 'error': f'ID de tarefa inválido: {str(e)}'}), 400
    
    # Valida e sanitiza o texto do comentário
    try:
        texto = request.form.get('comentario', '')
        if texto:
            texto = sanitize_string(texto, max_length=8000, min_length=1)
        else:
            texto = ''
    except ValidationError as e:
        api_logger.warning(f'Invalid comment in adicionar_comentario: {str(e)} - User: {g.user_email}')
        return jsonify({'ok': False, 'error': f'Texto do comentário inválido: {str(e)}'}), 400
    
    img_url = None

    if not r2_client or not current_app.config['CLOUDFLARE_PUBLIC_URL']:
        return jsonify({'ok': False, 'error': 'Serviço de armazenamento R2 não está configurado.'}), 500

    # 1. Verifica permissão e status da implantação
    tarefa_info = query_db(
        "SELECT i.usuario_cs, i.id as implantacao_id, t.tarefa_filho, i.status "
        "FROM tarefas t JOIN implantacoes i ON t.implantacao_id = i.id "
        "WHERE t.id = %s",
        (tarefa_id,), one=True
    )

    is_owner = tarefa_info.get('usuario_cs') == usuario_cs_email
    is_manager = g.perfil and g.perfil.get('perfil_acesso') in PERFIS_COM_GESTAO
    
    if not tarefa_info or not (is_owner or is_manager):
        return jsonify({'ok': False, 'error': 'Permissão negada.'}), 403
        
    if tarefa_info.get('status') in ['finalizada', 'parada']:
        status_atual = tarefa_info.get('status')
        return jsonify({'ok': False, 'error': f'Não é possível adicionar comentários a implantações com status "{status_atual}".'}), 400

    # Lida com o upload da imagem
    if 'imagem' in request.files:
        file = request.files.get('imagem')
        if file and file.filename and allowed_file(file.filename):
            try:
                impl_id = tarefa_info['implantacao_id']
                
                # Cria nome único
                filename = secure_filename(file.filename)
                nome_base, extensao = os.path.splitext(filename)
                nome_unico = f"{nome_base}_task{tarefa_id}_{int(time.time())}{extensao}"
                object_name = f"comment_images/impl_{impl_id}/task_{tarefa_id}/{nome_unico}"

                # Upload para R2
                file.seek(0)
                r2_client.upload_fileobj(
                    file, 
                    current_app.config['CLOUDFLARE_BUCKET_NAME'], 
                    object_name, 
                    ExtraArgs={'ContentType': file.content_type}
                )
                img_url = f"{current_app.config['CLOUDFLARE_PUBLIC_URL']}/{object_name}"
                print(f"SUCESSO (R2): Upload de comentário para {object_name}.")
                
            except (ClientError, NoCredentialsError) as upload_err:
                print(f"ERRO upload R2 comentário: {upload_err}")
                return jsonify({'ok': False, 'error': 'Erro ao fazer upload da imagem para o R2.'}), 500
            except Exception as e:
                return jsonify({'ok': False, 'error': f'Falha ao processar imagem: {e}'}), 500
        elif file and file.filename and not allowed_file(file.filename):
            return jsonify({'ok': False, 'error': 'Tipo de arquivo de imagem não permitido.'}), 400

    if not texto and not img_url:
        return jsonify({'ok': False, 'error': 'O comentário não pode estar vazio se não houver imagem.'}), 400

    try:
        agora = datetime.now()
        result = execute_and_fetch_one(
            "INSERT INTO comentarios (tarefa_id, usuario_cs, texto, data_criacao, imagem_url) "
            "VALUES (%s, %s, %s, %s, %s) RETURNING id",
            (tarefa_id, usuario_cs_email, texto, agora, img_url)
        )
        
        novo_id = result.get('id') if result else None
        
        if not novo_id:
            raise Exception("Falha ao salvar comentário e obter ID.")

        # Loga na timeline
        detalhe = f"Comentário em '{tarefa_info['tarefa_filho']}':\n{texto}" if texto else f"Imagem adicionada em '{tarefa_info['tarefa_filho']}'."
        if texto and img_url:
            detalhe = f"Comentário em '{tarefa_info['tarefa_filho']}':\n{texto}\n[Imagem Adicionada]"
        logar_timeline(tarefa_info['implantacao_id'], usuario_cs_email, 'novo_comentario', detalhe)
        
        api_logger.info(f'Comment added to task {tarefa_id} by user {g.user_email}')
        
        # Busca o comentário recém-criado com os dados do perfil
        novo_comentario_dados = query_db(
            """
            SELECT c.*, p.nome as usuario_nome
            FROM comentarios c
            JOIN perfil_usuario p ON c.usuario_cs = p.usuario
            WHERE c.id = %s
            """, (novo_id,), one=True
        )

        if not novo_comentario_dados:
            return jsonify({'ok': False, 'error': 'Falha ao recuperar o comentário após a criação.'}), 500

        # Renderiza o template do comentário e o retorna como HTML
        return render_template('partials/_comment_item.html', comentario=novo_comentario_dados)
        
    except Exception as e:
        print(f"ERRO ao salvar comentário para tarefa {tarefa_id}: {e}")
        return jsonify({'ok': False, 'error': f"Erro interno do servidor: {e}"}), 500

@api_bp.route('/excluir_comentario/<int:comentario_id>', methods=['POST'])
@login_required
def excluir_comentario(comentario_id):
    usuario_cs_email = g.user_email
    
    # Valida o ID do comentário
    try:
        comentario_id = validate_integer(comentario_id, min_value=1)
    except ValidationError as e:
        api_logger.warning(f'Invalid comment ID in excluir_comentario: {str(e)} - User: {g.user_email}')
        return jsonify({'ok': False, 'error': f'ID de comentário inválido: {str(e)}'}), 400

    if not r2_client:
        return jsonify({'ok': False, 'error': 'Serviço R2 não configurado.'}), 500
        
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

        # Exclui imagem do R2
        imagem_url = comentario.get('imagem_url')
        public_url_base = current_app.config['CLOUDFLARE_PUBLIC_URL']
        bucket_name = current_app.config['CLOUDFLARE_BUCKET_NAME']
        
        if imagem_url and public_url_base and imagem_url.startswith(public_url_base):
            try:
                object_key = imagem_url.replace(f"{public_url_base}/", "")
                if object_key:
                    r2_client.delete_object(Bucket=bucket_name, Key=object_key)
                    print(f"Objeto R2 (comentário) excluído: {object_key}")
            except ClientError as e_delete:
                print(f"Aviso: Falha ao excluir imagem R2 (key: {object_key}). Erro: {e_delete.response['Error']['Code']}")
            except Exception as e_delete:
                 print(f"Aviso: Falha ao excluir imagem R2 (key: {object_key}). Erro: {e_delete}")

        # Exclui do DB
        execute_db("DELETE FROM comentarios WHERE id = %s", (comentario_id,))
        logar_timeline(comentario['impl_id'], usuario_cs_email, 'comentario_excluido', f"Comentário em '{comentario['tarefa_filho']}' foi excluído.")
        
        api_logger.info(f'Comment {comentario_id} deleted by user {g.user_email}')
        
        # Retorna uma resposta vazia, o HTMX vai remover o elemento
        return '', 200
        
    except Exception as e:
        print(f"ERRO ao excluir comentário ID {comentario_id}: {e}")
        return jsonify({'ok': False, 'error': f"Erro interno do servidor: {e}"}), 500

@api_bp.route('/excluir_tarefa/<int:tarefa_id>', methods=['POST'])
@login_required
def excluir_tarefa(tarefa_id):
    usuario_cs_email = g.user_email
    
    # Valida o ID da tarefa
    try:
        tarefa_id = validate_integer(tarefa_id, min_value=1)
    except ValidationError as e:
        api_logger.warning(f'Invalid task ID in excluir_tarefa: {str(e)} - User: {g.user_email}')
        return jsonify({'ok': False, 'error': f'ID de tarefa inválido: {str(e)}'}), 400

    if not r2_client:
        return jsonify({'ok': False, 'error': 'Serviço R2 não configurado.'}), 500
        
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
        
        if tarefa.get('status') == 'finalizada':
            return jsonify({'ok': False, 'error': 'Não é possível excluir tarefas de implantações finalizadas.'}), 400

        # Excluir imagens associadas aos comentários ANTES de excluir a tarefa
        comentarios_tarefa = query_db("SELECT id, imagem_url FROM comentarios WHERE tarefa_id = %s", (tarefa_id,))
        public_url_base = current_app.config['CLOUDFLARE_PUBLIC_URL']
        bucket_name = current_app.config['CLOUDFLARE_BUCKET_NAME']
        
        for com in comentarios_tarefa:
             imagem_url = com.get('imagem_url')
             if imagem_url and public_url_base and imagem_url.startswith(public_url_base):
                try:
                    object_key = imagem_url.replace(f"{public_url_base}/", "")
                    if object_key:
                        r2_client.delete_object(Bucket=bucket_name, Key=object_key)
                        print(f"Objeto R2 (comentário {com['id']}) excluído: {object_key}")
                except ClientError as e_delete:
                    print(f"Aviso: Falha ao excluir imagem R2 (key: {object_key}). Erro: {e_delete.response['Error']['Code']}")
                except Exception as e_delete:
                     print(f"Aviso: Falha ao excluir imagem R2 (key: {object_key}). Erro: {e_delete}")

        # Agora exclui a tarefa (comentários são excluídos por CASCATA no DB)
        execute_db("DELETE FROM tarefas WHERE id = %s", (tarefa_id,))
        logar_timeline(impl_id, usuario_cs_email, 'tarefa_excluida', f"Tarefa '{nome_tarefa}' foi excluída.")
        
        api_logger.info(f'Task {tarefa_id} deleted by user {g.user_email}')
        
        # Verifica se a implantação deve ser auto-finalizada
        finalizada, log_finalizacao = auto_finalizar_implantacao(impl_id, usuario_cs_email)
        novo_prog, _, _ = _get_progress(impl_id)
        
        # Prepara resposta
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
        print(f"ERRO ao excluir tarefa ID {tarefa_id}: {e}")
        return jsonify({'ok': False, 'error': f"Erro interno do servidor: {e}"}), 500

@api_bp.route('/reordenar_tarefas', methods=['POST'])
@login_required
def reordenar_tarefas():
    usuario_cs_email = g.user_email
    try:
        data = request.get_json()
        impl_id = data.get('implantacao_id')
        tarefa_pai = data.get('tarefa_pai') # O "Módulo"
        nova_ordem_ids = data.get('ordem') # Lista de IDs na nova ordem
        
        if not all([impl_id, tarefa_pai, isinstance(nova_ordem_ids, list)]):
            return jsonify({'ok': False, 'error': 'Dados inválidos.'}), 400
            
        impl = query_db("SELECT id, usuario_cs FROM implantacoes WHERE id = %s", (impl_id,), one=True)
        is_owner = impl and impl.get('usuario_cs') == usuario_cs_email
        is_manager = g.perfil and g.perfil.get('perfil_acesso') in PERFIS_COM_GESTAO
        
        if not (is_owner or is_manager):
            security_logger.warning(f'Permission denied for user {g.user_email} trying to reorder tasks in implantation {impl_id}')
            return jsonify({'ok': False, 'error': 'Permissão negada.'}), 403
        
        # Atualiza a ordem no DB em um loop
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
        print(f"ERRO ao reordenar tarefas: {e}")
        return jsonify({'ok': False, 'error': f"Erro interno do servidor: {e}"}), 500

@api_bp.route('/excluir_tarefas_modulo', methods=['POST'])
@login_required
def excluir_tarefas_modulo():
    """Exclui todas as tarefas de um módulo (tarefa_pai) específico."""
    usuario_cs_email = g.user_email
    data = request.get_json()
    impl_id = data.get('implantacao_id')
    tarefa_pai = data.get('tarefa_pai') # O "Módulo"

    if not all([impl_id, tarefa_pai]):
        return jsonify({'ok': False, 'error': 'Dados inválidos (ID da implantação e Módulo são obrigatórios).'}), 400

    # 1. Verificar Permissão
    impl = query_db("SELECT id, nome_empresa, status, usuario_cs FROM implantacoes WHERE id = %s", (impl_id,), one=True)
    is_owner = impl and impl.get('usuario_cs') == usuario_cs_email
    is_manager = g.perfil and g.perfil.get('perfil_acesso') in PERFIS_COM_GESTAO
    
    if not (is_owner or is_manager):
        security_logger.warning(f'Permission denied for user {g.user_email} trying to delete tasks from module {tarefa_pai} in implantation {impl_id}')
        return jsonify({'ok': False, 'error': 'Permissão negada ou implantação não encontrada.'}), 403

    if impl.get('status') == 'finalizada':
        return jsonify({'ok': False, 'error': 'Não é possível excluir tarefas de implantações finalizadas.'}), 400

    # 2. Verificar R2
    if not r2_client:
        return jsonify({'ok': False, 'error': 'Serviço de armazenamento (R2) não configurado.'}), 500

    try:
        # 3. Buscar imagens de comentários ANTES de excluir as tarefas
        comentarios_img = query_db(
            """
            SELECT c.imagem_url
            FROM comentarios c
            JOIN tarefas t ON c.tarefa_id = t.id
            WHERE t.implantacao_id = %s AND t.tarefa_pai = %s AND c.imagem_url IS NOT NULL
            """, (impl_id, tarefa_pai)
        )
        
        public_url_base = current_app.config['CLOUDFLARE_PUBLIC_URL']
        bucket_name = current_app.config['CLOUDFLARE_BUCKET_NAME']

        # 4. Excluir imagens do R2
        for c in comentarios_img:
            imagem_url = c.get('imagem_url')
            if imagem_url and public_url_base and imagem_url.startswith(public_url_base):
                try:
                    object_key = imagem_url.replace(f"{public_url_base}/", "")
                    if object_key:
                        r2_client.delete_object(Bucket=bucket_name, Key=object_key)
                        print(f"Objeto R2 (módulo {tarefa_pai}) excluído: {object_key}")
                except ClientError as e_delete:
                    print(f"Aviso: Falha ao excluir imagem R2 (key: {object_key}). Erro: {e_delete.response['Error']['Code']}")
                except Exception as e_delete:
                    print(f"Aviso: Falha ao excluir imagem R2 (key: {object_key}). Erro: {e_delete}")
        
        # 5. Excluir Tarefas (ON DELETE CASCADE cuidará dos comentários no DB)
        execute_db("DELETE FROM tarefas WHERE implantacao_id = %s AND tarefa_pai = %s", (impl_id, tarefa_pai))
        
        # 6. Logar
        logar_timeline(impl_id, usuario_cs_email, 'modulo_excluido', f"Todas as tarefas do módulo '{tarefa_pai}' foram excluídas.")
        
        api_logger.info(f'All tasks from module {tarefa_pai} in implantation {impl_id} deleted by user {g.user_email}')
        
        # 7. Recalcular Progresso e verificar Auto-Finalização
        finalizada, log_finalizacao = auto_finalizar_implantacao(impl_id, usuario_cs_email)
        novo_prog, _, _ = _get_progress(impl_id)
        
        # 8. Buscar Log para retornar à UI
        nome = g.perfil.get('nome', usuario_cs_email)
        log_exclusao = query_db(
            "SELECT *, %s as usuario_nome FROM timeline_log "
            "WHERE implantacao_id = %s AND tipo_evento = 'modulo_excluido' "
            "ORDER BY id DESC LIMIT 1",
            (nome, impl_id), one=True
        )
        if log_exclusao:
            # Formata a data para JSON
            log_exclusao['data_criacao'] = format_date_iso_for_json(log_exclusao.get('data_criacao'))

        return jsonify({
            'ok': True,
            'log_exclusao_modulo': log_exclusao,
            'novo_progresso': novo_prog,
            'implantacao_finalizada': finalizada,
            'log_finalizacao': log_finalizacao
        })

    except Exception as e:
        api_logger.error(f'Error deleting tasks from module {tarefa_pai} in implantation {impl_id}: {str(e)} - User: {g.user_email}')
        print(f"ERRO ao excluir tarefas do módulo {tarefa_pai} (Impl. ID {impl_id}): {e}")
        return jsonify({'ok': False, 'error': f"Erro interno do servidor: {e}"}), 500