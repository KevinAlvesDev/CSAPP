from flask import (
    Blueprint, request, g, jsonify, current_app
)
from botocore.exceptions import ClientError
import mimetypes
import os

from ..blueprints.auth import login_required
from ..db import query_db, execute_db, logar_timeline
from ..extensions import r2_client
from ..utils import get_now_utc, allowed_file

# --- CORREÇÃO 1: Removido o url_prefix daqui ---
api_bp = Blueprint('api', __name__)

# --- CORREÇÃO 2: Adicionado '/api' ao início da rota ---
@api_bp.route('/api/atualizar_tarefa', methods=['POST'])
@login_required
def atualizar_tarefa():
    usuario_cs_email = g.user_email
    data = request.json
    tarefa_id = data.get('tarefa_id')
    concluida = data.get('concluida')

    if tarefa_id is None or concluida is None:
        return jsonify(success=False, error="Dados incompletos (tarefa_id, concluida)."), 400

    try:
        # Verifica se o usuário tem permissão (é dono da implantação da tarefa)
        tarefa = query_db(
            """ SELECT t.id, i.usuario_cs 
                FROM tarefas t 
                JOIN implantacoes i ON t.implantacao_id = i.id 
                WHERE t.id = %s """, 
            (tarefa_id,), one=True
        )
        if not tarefa or tarefa.get('usuario_cs') != usuario_cs_email:
            # (Adicionar verificação de Gestor se necessário)
            return jsonify(success=False, error="Permissão negada."), 403

        execute_db(
            "UPDATE tarefas SET concluida = %s WHERE id = %s",
            (concluida, tarefa_id)
        )
        
        # Logar na timeline (opcional, mas bom)
        try:
            tarefa_info = query_db("SELECT implantacao_id, tarefa_filho FROM tarefas WHERE id = %s", (tarefa_id,), one=True)
            if tarefa_info:
                status_str = "concluída" if concluida else "reaberta"
                logar_timeline(
                    tarefa_info['implantacao_id'], 
                    usuario_cs_email, 
                    'tarefa_atualizada', 
                    f"Tarefa '{tarefa_info['tarefa_filho']}' marcada como {status_str}."
                )
        except Exception as e_log:
            print(f"AVISO: Falha ao logar atualização da tarefa {tarefa_id}. Erro: {e_log}")
            
        return jsonify(success=True, message="Tarefa atualizada.")
        
    except Exception as e:
        print(f"Erro ao atualizar tarefa {tarefa_id}: {e}")
        return jsonify(success=False, error=f"Erro de servidor ao atualizar tarefa: {e}"), 500


# --- CORREÇÃO 3: Adicionado '/api' ao início da rota ---
@api_bp.route('/api/adicionar_comentario', methods=['POST'])
@login_required
def adicionar_comentario():
    usuario_cs_email = g.user_email
    
    # Recebendo como 'form-data' por causa da imagem
    tarefa_id = request.form.get('tarefa_id')
    comentario_texto = request.form.get('comentario_texto', '').strip()
    imagem_file = request.files.get('imagem_file')
    
    if not tarefa_id or (not comentario_texto and not imagem_file):
        return jsonify(success=False, error="Dados incompletos (tarefa_id e texto ou imagem)."), 400

    try:
        # Verifica permissão
        tarefa = query_db(
            """ SELECT t.id, t.implantacao_id, i.usuario_cs 
                FROM tarefas t 
                JOIN implantacoes i ON t.implantacao_id = i.id 
                WHERE t.id = %s """, 
            (tarefa_id,), one=True
        )
        if not tarefa or tarefa.get('usuario_cs') != usuario_cs_email:
            return jsonify(success=False, error="Permissão negada."), 403

        implantacao_id = tarefa.get('implantacao_id')
        imagem_url_final = None
        agora = get_now_utc()

        # Lógica de Upload R2 (se imagem_file existir)
        if imagem_file and allowed_file(imagem_file.filename):
            if not r2_client:
                return jsonify(success=False, error="Serviço de armazenamento (R2) não configurado."), 500
            
            try:
                bucket_name = current_app.config['CLOUDFLARE_BUCKET_NAME']
                public_url_base = current_app.config['CLOUDFLARE_PUBLIC_URL']
                
                # Gera um nome de ficheiro único
                extension = os.path.splitext(imagem_file.filename)[1]
                object_key = f"comment_images/impl_{implantacao_id}/task_{tarefa_id}/{agora.timestamp()}{extension}"
                
                content_type = mimetypes.guess_type(imagem_file.filename)[0] or 'application/octet-stream'
                
                r2_client.upload_fileobj(
                    imagem_file,
                    bucket_name,
                    object_key,
                    ExtraArgs={'ContentType': content_type, 'ACL': 'public-read'}
                )
                imagem_url_final = f"{public_url_base}/{object_key}"
                
            except ClientError as e_upload:
                print(f"Erro ao fazer upload R2 (tarefa {tarefa_id}): {e_upload}")
                return jsonify(success=False, error=f"Erro ao salvar a imagem: {e_upload}"), 500
            except Exception as e_upload:
                print(f"Erro inesperado no upload (tarefa {tarefa_id}): {e_upload}")
                return jsonify(success=False, error=f"Erro inesperado ao salvar a imagem: {e_upload}"), 500
        
        # Insere o comentário no DB
        comentario_id = execute_db(
            "INSERT INTO comentarios (tarefa_id, usuario_cs, comentario, imagem_url, data_criacao) VALUES (%s, %s, %s, %s, %s) RETURNING id",
            (tarefa_id, usuario_cs_email, comentario_texto, imagem_url_final, agora),
            fetch_id=True
        )
        
        # Busca o comentário recém-criado para retornar ao front-end
        novo_comentario = query_db(
            """ SELECT c.*, COALESCE(p.nome, c.usuario_cs) as usuario_nome 
                FROM comentarios c 
                LEFT JOIN perfil_usuario p ON c.usuario_cs = p.usuario 
                WHERE c.id = %s """, 
            (comentario_id,), one=True
        )
        if novo_comentario:
            novo_comentario['data_criacao_fmt_d'] = utils.format_date_br(novo_comentario.get('data_criacao'))
            
        # Logar na timeline
        log_msg = f"Comentário adicionado à tarefa (ID: {tarefa_id})."
        if imagem_url_final: log_msg += " (com imagem)"
        logar_timeline(implantacao_id, usuario_cs_email, 'comentario_adicionado', log_msg)

        return jsonify(success=True, message="Comentário adicionado.", comentario=novo_comentario), 201

    except Exception as e:
        print(f"Erro ao adicionar comentário (tarefa {tarefa_id}): {e}")
        return jsonify(success=False, error=f"Erro de servidor ao adicionar comentário: {e}"), 500

# --- CORREÇÃO 4: Adicionado '/api' ao início da rota ---
@api_bp.route('/api/excluir_comentario', methods=['POST'])
@login_required
def excluir_comentario():
    usuario_cs_email = g.user_email
    data = request.json
    comentario_id = data.get('comentario_id')

    if not comentario_id:
        return jsonify(success=False, error="Dados incompletos (comentario_id)."), 400

    try:
        # Verifica permissão
        comentario = query_db(
            """ SELECT c.id, c.usuario_cs, c.imagem_url, t.implantacao_id
                FROM comentarios c
                JOIN tarefas t ON c.tarefa_id = t.id
                WHERE c.id = %s """,
            (comentario_id,), one=True
        )
        if not comentario:
            return jsonify(success=False, error="Comentário não encontrado."), 404
        if comentario.get('usuario_cs') != usuario_cs_email:
            return jsonify(success=False, error="Permissão negada (não é o dono)."), 403

        # Excluir imagem do R2 (se existir)
        imagem_url = comentario.get('imagem_url')
        if imagem_url and r2_client:
            public_url_base = current_app.config['CLOUDFLARE_PUBLIC_URL']
            bucket_name = current_app.config['CLOUDFLARE_BUCKET_NAME']
            if imagem_url.startswith(public_url_base):
                try:
                    object_key = imagem_url.replace(f"{public_url_base}/", "")
                    if object_key: r2_client.delete_object(Bucket=bucket_name, Key=object_key)
                except ClientError as e_delete:
                    print(f"Aviso: Falha ao excluir R2 (key: {object_key}). Erro: {e_delete}")

        # Excluir do DB
        execute_db("DELETE FROM comentarios WHERE id = %s", (comentario_id,))
        
        logar_timeline(comentario.get('implantacao_id'), usuario_cs_email, 'comentario_excluido', f"Comentário (ID: {comentario_id}) excluído.")
        
        return jsonify(success=True, message="Comentário excluído.", deleted_id=comentario_id)

    except Exception as e:
        print(f"Erro ao excluir comentário {comentario_id}: {e}")
        return jsonify(success=False, error=f"Erro de servidor ao excluir comentário: {e}"), 500

# --- CORREÇÃO 5: Adicionado '/api' ao início da rota ---
@api_bp.route('/api/atualizar_ordem_tarefas', methods=['POST'])
@login_required
def atualizar_ordem_tarefas():
    usuario_cs_email = g.user_email
    data = request.json
    ordered_ids = data.get('ordered_ids')
    modulo = data.get('modulo')
    implantacao_id = data.get('implantacao_id')

    if not all([ordered_ids, modulo, implantacao_id]):
        return jsonify(success=False, error="Dados incompletos (ids, modulo, implantacao_id)."), 400

    try:
        # Verifica permissão
        impl = query_db("SELECT id, usuario_cs FROM implantacoes WHERE id = %s", (implantacao_id,), one=True)
        if not impl or impl.get('usuario_cs') != usuario_cs_email:
            return jsonify(success=False, error="Permissão negada."), 403

        # Atualização em lote (requer uma query para cada)
        # (Para DBs mais robustos, um CASE WHEN seria mais eficiente)
        query_args = []
        for index, tarefa_id in enumerate(ordered_ids):
            query_args.append((index + 1, tarefa_id, implantacao_id, modulo))
        
        execute_db(
            "UPDATE tarefas SET ordem = %s WHERE id = %s AND implantacao_id = %s AND tarefa_pai = %s",
            query_args,
            many=True
        )

        logar_timeline(implantacao_id, usuario_cs_email, 'tarefa_ordenada', f"Ordem das tarefas do módulo '{modulo}' foi atualizada.")
        
        return jsonify(success=True, message="Ordem das tarefas atualizada.")

    except Exception as e:
        print(f"Erro ao reordenar tarefas (Impl {implantacao_id}, Módulo {modulo}): {e}")
        return jsonify(success=False, error=f"Erro de servidor ao reordenar tarefas: {e}"), 500

# --- CORREÇÃO 6: Adicionado '/api' ao início da rota ---
@api_bp.route('/api/excluir_tarefa', methods=['POST'])
@login_required
def excluir_tarefa():
    usuario_cs_email = g.user_email
    data = request.json
    tarefa_id = data.get('tarefa_id')

    if not tarefa_id:
        return jsonify(success=False, error="Dados incompletos (tarefa_id)."), 400

    try:
        # Verifica permissão
        tarefa = query_db(
            """ SELECT t.id, t.tarefa_filho, t.implantacao_id, i.usuario_cs 
                FROM tarefas t 
                JOIN implantacoes i ON t.implantacao_id = i.id 
                WHERE t.id = %s """, 
            (tarefa_id,), one=True
        )
        if not tarefa:
            return jsonify(success=False, error="Tarefa não encontrada."), 404
        if tarefa.get('usuario_cs') != usuario_cs_email:
            return jsonify(success=False, error="Permissão negada (não é o dono)."), 403
            
        # (Adicionar lógica para excluir imagens R2 dos comentários, se necessário)

        # Excluir do DB (comentários são excluídos em cascata)
        execute_db("DELETE FROM tarefas WHERE id = %s", (tarefa_id,))
        
        logar_timeline(
            tarefa.get('implantacao_id'), 
            usuario_cs_email, 
            'tarefa_excluida', 
            f"Tarefa '{tarefa.get('tarefa_filho')}' (ID: {tarefa_id}) foi excluída."
        )
        
        return jsonify(success=True, message="Tarefa excluída.", deleted_id=tarefa_id)

    except Exception as e:
        print(f"Erro ao excluir tarefa {tarefa_id}: {e}")
        return jsonify(success=False, error=f"Erro de servidor ao excluir tarefa: {e}"), 500