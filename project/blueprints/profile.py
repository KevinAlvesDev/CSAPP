from flask import (
    Blueprint, request, g, jsonify, current_app, session
)
from werkzeug.security import check_password_hash, generate_password_hash
from botocore.exceptions import ClientError
import os
import mimetypes

from ..db import query_db, execute_db
from ..blueprints.auth import login_required
from ..extensions import r2_client
from ..utils import get_now_utc

profile_bp = Blueprint('profile', __name__)

@profile_bp.route('/perfil', methods=['GET'])
@login_required
def perfil():
    """Retorna os dados do perfil do usuário logado."""
    # g.perfil é carregado pelo decorator @login_required
    if not g.perfil:
        return jsonify(success=False, error="Perfil não encontrado."), 404
        
    return jsonify(success=True, perfil=g.perfil)


@profile_bp.route('/perfil/atualizar', methods=['POST'])
@login_required
def atualizar_perfil():
    """
    Atualiza o perfil do usuário (nome, cargo, foto).
    Espera 'multipart/form-data' por causa do upload da foto.
    """
    usuario_email = g.user_email
    
    # Dados do formulário (enviados como multipart/form-data)
    nome = request.form.get('nome', '').strip()
    cargo = request.form.get('cargo', '').strip()
    foto_file = request.files.get('foto_url')

    if not nome:
        return jsonify(success=False, error="O nome é obrigatório."), 400

    try:
        current_profile = g.perfil
        new_foto_url = current_profile.get('foto_url') # Mantém a URL antiga por padrão

        # 1. Lógica de Upload da Foto (se enviada)
        if foto_file and foto_file.filename != '':
            if not r2_client:
                 return jsonify(success=False, error="Serviço de armazenamento (R2) não configurado."), 500

            bucket_name = current_app.config['CLOUDFLARE_BUCKET_NAME']
            public_url_base = current_app.config['CLOUDFLARE_PUBLIC_URL']
            
            safe_email = "".join(c if c.isalnum() else "_" for c in usuario_email)
            timestamp = int(get_now_utc().timestamp())
            original_filename = foto_file.filename
            extension = os.path.splitext(original_filename)[1]
            object_key = f"profile_photos/{safe_email}/{timestamp}{extension}"
            content_type = mimetypes.guess_type(original_filename)[0] or 'application/octet-stream'

            try:
                # 2. Excluir foto antiga do R2 (se existir e for do R2)
                old_foto_url = current_profile.get('foto_url')
                if old_foto_url and old_foto_url.startswith(public_url_base):
                    old_key = old_foto_url.replace(f"{public_url_base}/", "")
                    try:
                        r2_client.delete_object(Bucket=bucket_name, Key=old_key)
                        print(f"Foto de perfil antiga excluída: {old_key}")
                    except ClientError as e_del:
                        print(f"Aviso: Falha ao excluir foto antiga {old_key}. Erro: {e_del}")

                # 3. Fazer upload da nova foto
                r2_client.upload_fileobj(
                    foto_file,
                    bucket_name,
                    object_key,
                    ExtraArgs={
                        'ContentType': content_type,
                        'ACL': 'public-read' # Garante que a imagem seja pública
                    }
                )
                new_foto_url = f"{public_url_base}/{object_key}"
                print(f"Nova foto de perfil carregada: {new_foto_url}")

            except ClientError as e_upload:
                print(f"Erro ao fazer upload para R2: {e_upload}")
                return jsonify(success=False, error=f"Erro ao salvar a foto: {e_upload}"), 500
            except Exception as e_upload:
                 print(f"Erro inesperado no upload: {e_upload}")
                 return jsonify(success=False, error=f"Erro inesperado ao salvar a foto: {e_upload}"), 500

        # 4. Atualizar o banco de dados
        execute_db(
            "UPDATE perfil_usuario SET nome = %s, cargo = %s, foto_url = %s WHERE usuario = %s",
            (nome, cargo, new_foto_url, usuario_email)
        )
        
        # 5. Atualizar a sessão (g.perfil)
        g.perfil['nome'] = nome
        g.perfil['cargo'] = cargo
        g.perfil['foto_url'] = new_foto_url
        
        if 'user' in session and session['user'].get('name') != nome:
            session['user']['name'] = nome
            
        return jsonify(
            success=True, 
            message="Perfil atualizado com sucesso!",
            updated_profile=g.perfil # Retorna o perfil atualizado
        )

    except Exception as e:
        print(f"Erro ao atualizar perfil para {usuario_email}: {e}")
        return jsonify(success=False, error=f"Erro ao atualizar perfil: {e}"), 500

# Esta rota provavelmente não é usada com Auth0, mas está aqui convertida
@profile_bp.route('/perfil/atualizar_senha', methods=['POST'])
@login_required
def atualizar_senha():
    usuario_email = g.user_email
    data = request.json
    senha_antiga = data.get('senha_antiga')
    nova_senha = data.get('nova_senha')

    if not senha_antiga or not nova_senha:
        return jsonify(success=False, error="Senha antiga e nova são obrigatórias."), 400

    try:
        # Verifica se é usuário Auth0 (não pode trocar senha aqui)
        is_auth0_user = session.get('user', {}).get('sub', '').startswith(('auth0|', 'google-oauth2|'))
        if is_auth0_user:
             return jsonify(success=False, error="Usuários autenticados via Google/Auth0 devem redefinir a senha na plataforma de origem."), 400

        user_db = query_db("SELECT senha FROM usuarios WHERE usuario = %s", (usuario_email,), one=True)

        if not user_db or not check_password_hash(user_db['senha'], senha_antiga):
            return jsonify(success=False, error="Senha antiga incorreta."), 403

        nova_senha_hash = generate_password_hash(nova_senha)
        execute_db("UPDATE usuarios SET senha = %s WHERE usuario = %s", (nova_senha_hash, usuario_email))
        
        return jsonify(success=True, message="Senha atualizada com sucesso.")

    except Exception as e:
        print(f"Erro ao atualizar senha para {usuario_email}: {e}")
        return jsonify(success=False, error=f"Erro ao atualizar senha: {e}"), 500