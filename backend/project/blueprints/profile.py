# testo/CSAPP/backend/project/blueprints/profile.py
from flask import (
    Blueprint, render_template, request, flash, redirect, url_for, g, current_app, session
)
from ..blueprints.auth import login_required
from ..db import query_db, execute_db
from ..extensions import r2_client
from werkzeug.utils import secure_filename
import smtplib
from ..email_utils import load_smtp_settings, save_smtp_settings, test_smtp_connection, send_email, detect_smtp_settings
from ..validation import validate_email, ValidationError
from ..logging_config import app_logger

profile_bp = Blueprint('profile', __name__, url_prefix='/profile')

@profile_bp.before_request
@login_required
def before_request():
    """Protege todas as rotas de perfil."""
    pass

@profile_bp.route('/')
def profile():
    """Exibe a página de perfil do usuário e as configurações de e-mail."""
    
    # Carrega configurações SMTP pessoais
    smtp_settings = load_smtp_settings(g.user_email)
    
    # Prepara dados para o formulário (sem a senha)
    settings_data = {
        'host': smtp_settings.get('host', '') if smtp_settings else '',
        'port': smtp_settings.get('port', 587) if smtp_settings else 587,
        'user': smtp_settings.get('user', '') if smtp_settings else '', # 'user' é o nome da coluna no dict
        'use_tls': smtp_settings.get('use_tls', True) if smtp_settings else True,
        'use_ssl': smtp_settings.get('use_ssl', False) if smtp_settings else False,
    }
    
    # A senha NUNCA é enviada de volta para o template.
    # O campo de senha estará sempre vazio.
    
    return render_template('perfil.html', 
                           smtp_settings=settings_data, 
                           r2_configurado=g.R2_CONFIGURED)

@profile_bp.route('/save', methods=['POST'])
def save_profile():
    """Salva as informações básicas do perfil e faz upload da foto."""
    
    nome = request.form.get('nome')
    cargo = request.form.get('cargo')
    foto = request.files.get('foto')
    
    if not nome or not cargo:
        flash("Nome e Cargo são obrigatórios.", "error")
        return redirect(url_for('profile.profile'))

    foto_url = g.perfil.get('foto_url') # Mantém a foto existente por padrão

    if foto and g.R2_CONFIGURED:
        try:
            filename = secure_filename(foto.filename)
            # Define um 'caminho' no R2, ex: 'fotos_perfil/usuario_email.ext'
            s3_key = f"fotos_perfil/{g.user_email}_{filename}"
            
            r2_client.upload_fileobj(
                foto,
                current_app.config['CLOUDFLARE_BUCKET_NAME'],
                s3_key,
                ExtraArgs={'ContentType': foto.content_type}
            )
            # URL pública do R2 (configurada no .env)
            base_public_url = current_app.config['CLOUDFLARE_PUBLIC_URL']
            foto_url = f"{base_public_url}/{s3_key}"
            
            app_logger.info(f"Foto de perfil carregada para {g.user_email} em {foto_url}")

        except Exception as e:
            app_logger.error(f"Falha no upload para o R2 para {g.user_email}: {e}")
            flash("Erro ao fazer upload da foto.", "error")

    try:
        execute_db(
            "UPDATE perfil_usuario SET nome = %s, cargo = %s, foto_url = %s WHERE usuario = %s",
            (nome, cargo, foto_url, g.user_email)
        )
        
        # Atualiza a sessão para refletir o novo nome/foto imediatamente
        session['user'] = session.get('user', {})
        session['user']['name'] = nome
        session['user']['picture'] = foto_url
        session.modified = True
        
        flash("Perfil atualizado com sucesso!", "success")
        
    except Exception as e:
        app_logger.error(f"Erro ao salvar perfil no DB para {g.user_email}: {e}")
        flash("Erro ao salvar perfil no banco de dados.", "error")

    return redirect(url_for('profile.profile'))

# --- ROTAS DE E-MAIL (MOVIDAS DA GESTÃO) ---

@profile_bp.route('/email/save', methods=['POST'])
def save_email_settings():
    """Salva as configurações de SMTP pessoais do usuário."""
    data = request.form
    try:
        # Passa o e-mail do usuário logado para a função de salvar
        save_smtp_settings(g.user_email, data)
        flash("Configurações de SMTP salvas com sucesso!", "success")
    except ValueError as e:
        app_logger.warning(f"Falha ao salvar SMTP (dados incompletos) para {g.user_email}: {e}")
        flash(f"Erro ao salvar: {e}", "error")
    except Exception as e:
        app_logger.error(f"Erro ao salvar SMTP para {g.user_email}: {e}")
        flash("Ocorreu um erro ao salvar as configurações.", "error")
        
    return redirect(url_for('profile.profile'))

@profile_bp.route('/email/test', methods=['POST'])
def test_email():
    """Testa as configurações de SMTP pessoais do usuário."""
    
    # A senha para o teste DEVE ser fornecida no formulário
    test_password = request.form.get('password')
    
    if not test_password:
        flash("Para testar, você deve preencher o campo 'Senha' com sua App Password.", "warning")
        return redirect(url_for('profile.profile'))
        
    try:
        # 1. Carrega as configurações salvas (que têm o HASH)
        settings = load_smtp_settings(g.user_email)
        if not settings:
            flash("Nenhuma configuração de SMTP salva para testar.", "error")
            return redirect(url_for('profile.profile'))

        # 2. Testa a conexão (compara o hash e tenta o login no provedor)
        test_smtp_connection(settings, test_password)
        
        flash("Conexão SMTP bem-sucedida!", "success")
        
    except smtplib.SMTPAuthenticationError as e:
        app_logger.warning(f"Falha no teste de autenticação SMTP para {g.user_email}: {e}")
        flash(f"Falha na autenticação: {e}. Verifique sua App Password e se o SMTP_USER está correto.", "error")
    except Exception as e:
        app_logger.error(f"Erro no teste de SMTP para {g.user_email}: {e}")
        flash(f"Falha ao testar conexão: {e}", "error")

    return redirect(url_for('profile.profile'))

@profile_bp.route('/email/send-test', methods=['POST'])
def email_send_test():
    """Envia um e-mail de teste usando as configurações pessoais do usuário."""
    try:
        test_recipient = request.form.get('test_recipient', '').strip()
        from_name = request.form.get('from_name', '').strip() or g.perfil.get('nome') or g.user_email
        plain_password = request.form.get('password')

        if not plain_password:
            flash("Para enviar teste, preencha o campo 'Senha' com sua App Password.", "warning")
            return redirect(url_for('profile.profile'))

        # Valida destinatário
        try:
            test_recipient = validate_email(test_recipient)
        except ValidationError as e:
            flash(f"Destinatário inválido: {str(e)}", "error")
            return redirect(url_for('profile.profile'))

        # Carrega configurações salvas e valida conexão
        settings = load_smtp_settings(g.user_email)
        if not settings:
            flash("Nenhuma configuração de SMTP salva para enviar.", "error")
            return redirect(url_for('profile.profile'))

        # Primeiro testa autenticação para garantir credenciais válidas
        test_smtp_connection(settings, plain_password)

        # Envia o e-mail de teste
        subject = "Teste de envio - CSAPP"
        body_html = (
            f"<p>Este é um envio de <strong>teste</strong> da plataforma CSAPP.</p>"
            f"<p>Solicitado por: {from_name} ({g.user_email})</p>"
            f"<p>Se recebeu este e-mail, o envio está configurado corretamente.</p>"
        )
        ok = send_email(subject, body_html, [test_recipient], settings, plain_password, from_name=from_name, reply_to=g.user_email)

        if ok:
            flash(f"E-mail de teste enviado para {test_recipient}.", "success")
        else:
            flash(f"Falha ao enviar e-mail de teste para {test_recipient}.", "error")

    except smtplib.SMTPAuthenticationError as e:
        app_logger.warning(f"Falha de autenticação SMTP ao enviar teste para {g.user_email}: {e}")
        flash(f"Falha na autenticação: {e}. Verifique sua App Password.", "error")
    except Exception as e:
        app_logger.error(f"Erro ao enviar e-mail de teste para {g.user_email}: {e}")
        flash(f"Erro ao enviar teste: {e}", "error")

    return redirect(url_for('profile.profile'))

@profile_bp.route('/email/quick-setup', methods=['POST'])
def quick_setup_email():
    """Configuração rápida: usa apenas e-mail do usuário e App Password.
    Detecta automaticamente host/porta/TLS/SSL com base no domínio e salva.
    Em seguida, testa a autenticação com a App Password fornecida.
    """
    # O e-mail do usuário está fixo como g.user_email
    user_email = g.user_email
    plain_password = request.form.get('quick_password')

    if not plain_password:
        flash("Informe sua App Password para configurar.", "warning")
        return redirect(url_for('profile.profile'))

    try:
        # 1) Detecta o provedor SMTP
        auto = detect_smtp_settings(user_email)

        # 2) Salva configurações com hash da senha (user = g.user_email)
        save_payload = {
            'host': auto['host'],
            'port': auto['port'],
            'user': user_email,
            'password': plain_password,  # será hasheada internamente
            'use_tls': 'true' if auto.get('use_tls') else 'false',
            'use_ssl': 'true' if auto.get('use_ssl') else 'false',
        }
        save_smtp_settings(user_email, save_payload)

        # 3) Carrega e testa autenticação com a senha em texto plano
        settings = load_smtp_settings(user_email)
        test_smtp_connection(settings, plain_password)

        flash(
            f"Configuração automática concluída para {user_email} usando {auto['host']}:{auto['port']}.",
            "success"
        )
    
    except smtplib.SMTPAuthenticationError as e:
        app_logger.warning(f"Falha de autenticação SMTP no quick-setup para {user_email}: {e}")
        flash(
            "Falha na autenticação com o provedor. Verifique sua App Password e se o seu e-mail pertence ao provedor correto.",
            "error"
        )
    except Exception as e:
        app_logger.error(f"Erro no quick-setup SMTP para {user_email}: {e}")
        flash(f"Não foi possível configurar automático: {e}", "error")

    return redirect(url_for('profile.profile'))