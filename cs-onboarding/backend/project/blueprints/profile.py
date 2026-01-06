import io
import os
import time

from flask import Blueprint, current_app, flash, g, redirect, render_template, request, session, url_for
from werkzeug.utils import secure_filename

from ..blueprints.auth import login_required
from ..config.logging_config import app_logger
from ..core.extensions import r2_client
from ..domain.auth_service import atualizar_dados_perfil_service

profile_bp = Blueprint('profile', __name__, url_prefix='/profile')


def _upload_profile_photo(foto, user_email):
    """
    Função auxiliar para fazer upload de foto de perfil.
    Tenta primeiro R2/Cloudflare, depois fallback para storage local.
    
    Args:
        foto: FileStorage object do Flask
        user_email: Email do usuário (para nomear arquivo)
        
    Returns:
        str: URL da foto ou None se falhar
    """
    if not foto or not foto.filename:
        return None
        
    try:
        foto_bytes = foto.read()
    except Exception:
        app_logger.error(f"Falha ao ler bytes da foto para {user_email}")
        return None
        
    filename = secure_filename(foto.filename)
    
    # Tentar upload para R2 (Cloudflare)
    if g.R2_CONFIGURED and r2_client:
        try:
            s3_key = f"fotos_perfil/{user_email}_{filename}"
            data_stream = io.BytesIO(foto_bytes)
            data_stream.seek(0)
            
            r2_client.upload_fileobj(
                data_stream,
                current_app.config['CLOUDFLARE_BUCKET_NAME'],
                s3_key,
                ExtraArgs={'ContentType': foto.content_type}
            )
            
            base_public_url = current_app.config['CLOUDFLARE_PUBLIC_URL']
            foto_url = f"{base_public_url}/{s3_key}"
            app_logger.info(f"Foto de perfil carregada para R2: {user_email} -> {foto_url}")
            return foto_url
            
        except Exception as e:
            app_logger.error(f"Falha no upload para R2 para {user_email}: {e}")
            # Continua para fallback local
    
    # Fallback: salvar localmente
    try:
        unique_name = f"{user_email}_{int(time.time())}_{filename}"
        static_dir = current_app.static_folder
        target_dir = os.path.join(static_dir, 'uploads', 'profile')
        os.makedirs(target_dir, exist_ok=True)
        save_path = os.path.join(target_dir, unique_name)
        
        with open(save_path, 'wb') as f_out:
            f_out.write(foto_bytes)
            
        foto_url = f"/static/uploads/profile/{unique_name}"
        app_logger.info(f"Foto de perfil salva localmente: {user_email} -> {foto_url}")
        return foto_url
        
    except Exception as e:
        app_logger.error(f"Falha ao salvar foto local para {user_email}: {e}")
        flash("Erro ao salvar foto.", "error")
        return None


@profile_bp.before_request
@login_required
def before_request():
    """Protege todas as rotas de perfil."""
    pass


@profile_bp.route('/')
def profile():
    """Exibe a página de perfil do usuário."""
    return render_template('pages/perfil.html', r2_configurado=g.R2_CONFIGURED)


@profile_bp.route('/modal')
def profile_modal():
    """Retorna apenas o conteúdo parcial para exibir dentro do modal de Perfil."""
    return render_template('modals/_perfil_content.html', r2_configurado=g.R2_CONFIGURED)


@profile_bp.route('/save', methods=['POST'])
def save_profile():
    """Salva as informações básicas do perfil e faz upload da foto."""

    nome = request.form.get('nome')
    cargo = request.form.get('cargo')
    foto = request.files.get('foto')

    if not nome or not cargo:
        flash("Nome e Cargo são obrigatórios.", "error")
        return redirect(url_for('profile.profile'))

    # Manter foto atual se não houver nova
    foto_url = g.perfil.get('foto_url')
    
    # Fazer upload da nova foto se fornecida
    if foto and foto.filename:
        new_foto_url = _upload_profile_photo(foto, g.user_email)
        if new_foto_url:
            foto_url = new_foto_url

    try:
        atualizar_dados_perfil_service(g.user_email, nome, cargo, foto_url)

        session['user'] = session.get('user', {})
        session['user']['name'] = nome
        session['user']['picture'] = foto_url
        session.modified = True

        # Atualizar g.perfil para refletir mudanças no template imediatamente
        if hasattr(g, 'perfil') and g.perfil:
            if isinstance(g.perfil, dict):
                g.perfil['nome'] = nome
                g.perfil['cargo'] = cargo
                g.perfil['foto_url'] = foto_url
            else:
                g.perfil.nome = nome
                g.perfil.cargo = cargo
                g.perfil.foto_url = foto_url

        flash("Perfil atualizado com sucesso!", "success")

    except Exception as e:
        app_logger.error(f"Erro ao salvar perfil no DB para {g.user_email}: {e}")
        flash("Erro ao salvar perfil no banco de dados.", "error")

    if request.headers.get('HX-Request') == 'true':
        from flask import make_response
        response = make_response(render_template('modals/_perfil_content.html', r2_configurado=g.R2_CONFIGURED))
        response.headers['X-Updated-Photo-Url'] = foto_url or ''
        response.headers['X-Updated-Name'] = nome or ''
        response.headers['X-Updated-Cargo'] = cargo or ''
        return response
    
    return redirect(url_for('profile.profile'))

