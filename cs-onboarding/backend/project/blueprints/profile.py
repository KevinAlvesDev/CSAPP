from flask import (
    Blueprint, render_template, request, flash, redirect, url_for, g, current_app, session
)
from ..blueprints.auth import login_required
from ..db import execute_db
from ..core.extensions import r2_client
from werkzeug.utils import secure_filename
from ..config.logging_config import app_logger
import os
import time
import io

profile_bp = Blueprint('profile', __name__, url_prefix='/profile')


@profile_bp.before_request
@login_required
def before_request():
    """Protege todas as rotas de perfil."""
    pass


@profile_bp.route('/')
def profile():
    """Exibe a página de perfil do usuário."""
    return render_template('perfil.html', r2_configurado=g.R2_CONFIGURED)


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

    foto_url = g.perfil.get('foto_url')

    if foto and g.R2_CONFIGURED and r2_client:
        try:
            try:
                foto_bytes = foto.read()
            except Exception:
                foto_bytes = None
            filename = secure_filename(foto.filename)

            s3_key = f"fotos_perfil/{g.user_email}_{filename}"

            if foto_bytes is None:
                raise ValueError("Falha ao ler bytes da foto para upload")
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

            app_logger.info(f"Foto de perfil carregada para {g.user_email} em {foto_url}")

        except Exception as e:
            app_logger.error(f"Falha no upload para o R2 para {g.user_email}: {e}")
            flash("Erro ao fazer upload da foto.", "error")
            try:
                filename = secure_filename(foto.filename)
                unique_name = f"{g.user_email}_{int(time.time())}_{filename}"
                static_dir = current_app.static_folder
                target_dir = os.path.join(static_dir, 'uploads', 'profile')
                os.makedirs(target_dir, exist_ok=True)
                save_path = os.path.join(target_dir, unique_name)
                if 'foto_bytes' not in locals() or foto_bytes is None:
                    try:
                        foto_bytes = foto.read()
                    except Exception:
                        foto_bytes = None
                if foto_bytes is None:
                    raise ValueError("Falha ao obter conteúdo da foto para salvar localmente")
                with open(save_path, 'wb') as f_out:
                    f_out.write(foto_bytes)
                foto_url = f"/static/uploads/profile/{unique_name}"
                app_logger.info(f"Foto de perfil salva localmente para {g.user_email} em {foto_url}")
            except Exception as e2:
                app_logger.error(f"Falha ao salvar foto local para {g.user_email}: {e2}")
    elif foto:
        try:
            try:
                foto_bytes = foto.read()
            except Exception:
                foto_bytes = None
            filename = secure_filename(foto.filename)
            unique_name = f"{g.user_email}_{int(time.time())}_{filename}"
            static_dir = current_app.static_folder
            target_dir = os.path.join(static_dir, 'uploads', 'profile')
            os.makedirs(target_dir, exist_ok=True)
            save_path = os.path.join(target_dir, unique_name)
            if foto_bytes is None:
                raise ValueError("Falha ao obter conteúdo da foto para salvar localmente")
            with open(save_path, 'wb') as f_out:
                f_out.write(foto_bytes)
            foto_url = f"/static/uploads/profile/{unique_name}"
            app_logger.info(f"Foto de perfil salva localmente para {g.user_email} em {foto_url}")
        except Exception as e:
            app_logger.error(f"Falha ao salvar foto local para {g.user_email}: {e}")
            flash("Erro ao salvar foto local.", "error")

    try:
        execute_db(
            "UPDATE perfil_usuario SET nome = %s, cargo = %s, foto_url = %s WHERE usuario = %s",
            (nome, cargo, foto_url, g.user_email)
        )

        session['user'] = session.get('user', {})
        session['user']['name'] = nome
        session['user']['picture'] = foto_url
        session.modified = True

        flash("Perfil atualizado com sucesso!", "success")

    except Exception as e:
        app_logger.error(f"Erro ao salvar perfil no DB para {g.user_email}: {e}")
        flash("Erro ao salvar perfil no banco de dados.", "error")

    if request.headers.get('HX-Request') == 'true':
        return render_template('modals/_perfil_content.html', r2_configurado=g.R2_CONFIGURED)
    return redirect(url_for('profile.profile'))
