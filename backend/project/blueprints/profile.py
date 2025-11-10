import os
import time
from flask import (
    Blueprint, render_template, request, flash, redirect, url_for, g, current_app
)
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash
from botocore.exceptions import ClientError, NoCredentialsError

from ..blueprints.auth import login_required
from ..db import execute_db, query_db
from ..extensions import r2_client
from ..utils import allowed_file
from ..constants import CARGOS_LIST, PERFIL_IMPLANTADOR # <-- ALTERADO
from ..validation import sanitize_string, ValidationError

profile_bp = Blueprint('profile', __name__)

@profile_bp.route('/perfil', methods=['GET', 'POST'])
@login_required
def perfil():
    usuario_cs_email = g.user_email
    current_perfil = g.perfil # Perfil carregado pelo @login_required

    if request.method == 'POST':
        # Verifica se o R2 está configurado antes de tentar o upload
        if not r2_client or not current_app.config['CLOUDFLARE_PUBLIC_URL']:
            flash("Erro: Serviço de armazenamento (R2) não configurado. Não é possível alterar a foto.", "error")
            return redirect(url_for('profile.perfil'))
            
        try:
            # Pega e valida os dados do formulário
            try:
                form_nome = request.form.get('nome', '')
                if form_nome:
                    form_nome = sanitize_string(form_nome, max_length=100, min_length=1)
                else:
                    form_nome = ''
                    
                form_cargo = request.form.get('cargo', '')
                if form_cargo:
                    form_cargo = sanitize_string(form_cargo, max_length=50)
                else:
                    form_cargo = ''
            except ValidationError as e:
                flash(f'Erro de validação: {str(e)}', 'error')
                return redirect(url_for('profile.perfil'))
            
            # --- Lógica de Restrição ATUALIZADA ---
            is_implantador = current_perfil.get('perfil_acesso') == PERFIL_IMPLANTADOR # <-- ALTERADO
            
            # DEFINE nome_to_save: Se não for implantador, usa o valor do form.
            if not is_implantador:
                 nome_to_save = form_nome if form_nome else None
            else:
                 nome_to_save = current_perfil.get('nome')
            
            # Cargo só é salvo se não for implantador.
            cargo_to_save = current_perfil.get('cargo') # Mantém o atual por padrão
            if not is_implantador:
                if not form_cargo: 
                    cargo_to_save = None
                elif form_cargo in CARGOS_LIST:
                    cargo_to_save = form_cargo
                else:
                    cargo_to_save = current_perfil.get('cargo') 
            # --------------------------
            
            foto_url_atual = current_perfil.get('foto_url')

            # --- Lógica de Upload para R2 (original) ---
            if 'foto_perfil' in request.files:
                file = request.files['foto_perfil']
                if file and file.filename and allowed_file(file.filename):
                    try:
                        # Cria um nome de arquivo único
                        nome_base, extensao = os.path.splitext(secure_filename(file.filename))
                        email_hash = generate_password_hash(usuario_cs_email).split('$')[-1][:8]
                        object_name = f"profile_pics/perfil_{email_hash}_{int(time.time())}{extensao}"

                        # Faz o upload para o R2
                        file.seek(0)
                        r2_client.upload_fileobj(
                            file,
                            current_app.config['CLOUDFLARE_BUCKET_NAME'],
                            object_name,
                            ExtraArgs={'ContentType': file.content_type}
                        )
                        
                        # Constrói a URL pública
                        nova_foto_url = f"{current_app.config['CLOUDFLARE_PUBLIC_URL']}/{object_name}"
                        print(f"Upload R2 concluído: {nova_foto_url}")

                        # --- Excluir foto ANTIGA do R2 ---
                        if foto_url_atual and foto_url_atual != nova_foto_url:
                            try:
                                old_object_key = foto_url_atual.replace(f"{current_app.config['CLOUDFLARE_PUBLIC_URL']}/", "")
                                if old_object_key and old_object_key != foto_url_atual:
                                    print(f"Tentando excluir objeto R2 antigo: {old_object_key}")
                                    r2_client.delete_object(
                                        Bucket=current_app.config['CLOUDFLARE_BUCKET_NAME'], 
                                        Key=old_object_key
                                    )
                                    print(f"Objeto R2 antigo excluído.")
                            except Exception as e_delete:
                                print(f"Aviso: Falha ao excluir foto antiga do R2. {e_delete}")
                        
                        foto_url_atual = nova_foto_url

                    except (ClientError, NoCredentialsError) as e_upload:
                        print(f"ERRO upload R2: {e_upload}")
                        flash("Erro ao fazer upload da nova foto (credenciais/conexão R2?).", "error")
                    except Exception as e_upload:
                        print(f"ERRO upload R2: {e_upload}")
                        flash("Erro ao fazer upload da nova foto.", "error")

            # Atualiza o banco de dados com os valores corretos (respeitando a restrição)
            execute_db(
                """
                UPDATE perfil_usuario 
                SET nome = %s, cargo = %s, foto_url = %s 
                WHERE usuario = %s
                """,
                (nome_to_save, cargo_to_save, foto_url_atual, usuario_cs_email)
            )
            
            if is_implantador and (request.form.get('nome', '').strip() != current_perfil.get('nome') or request.form.get('cargo', '').strip() != current_perfil.get('cargo')):
                 # Verifica se a intenção era mudar (o form submetido é diferente do valor inicial)
                 flash(f'Perfil atualizado. Nome e Cargo não podem ser alterados pelo perfil {PERFIL_IMPLANTADOR}.', 'warning') # <-- ALTERADO
            else:
                 flash('Perfil atualizado com sucesso!', 'success')
            
            # Recarrega o perfil para refletir a mudança no request atual
            g.perfil = query_db("SELECT * FROM perfil_usuario WHERE usuario = %s", (usuario_cs_email,), one=True)
            
            return redirect(url_for('profile.perfil'))
            
        except Exception as e:
            print(f"ERRO GERAL ao atualizar perfil para {usuario_cs_email}: {e}")
            flash(f'Erro ao atualizar perfil: {e}', 'error')
            return redirect(url_for('profile.perfil'))

    # Método GET
    return render_template('perfil.html', user_info=g.user, perfil=current_perfil, cargos_list=CARGOS_LIST)
@profile_bp.route('/email', methods=['GET'])
@login_required
def email_settings():
    usuario_cs_email = g.user_email
    # Garante tabela mínima
    try:
        execute_db(
            """
            CREATE TABLE IF NOT EXISTS email_accounts (
                usuario_cs TEXT PRIMARY KEY,
                smtp_user TEXT NOT NULL,
                smtp_password TEXT NOT NULL,
                from_name TEXT,
                active INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
    except Exception as e:
        print(f"Aviso: falha ao garantir tabela email_accounts: {e}")

    settings = query_db(
        "SELECT * FROM email_accounts WHERE usuario_cs = %s",
        (usuario_cs_email,), one=True
    )
    return render_template('email_settings.html', settings=settings)


@profile_bp.route('/email/save', methods=['POST'])
@login_required
def email_settings_save():
    usuario_cs_email = g.user_email
    try:
        smtp_user = sanitize_string(request.form.get('smtp_user', ''), max_length=200)
        smtp_password = sanitize_string(request.form.get('smtp_password', ''), max_length=200)
        from_name = request.form.get('from_name', '')
        if from_name:
            from_name = sanitize_string(from_name, max_length=200)
        if not smtp_user or not smtp_password:
            raise ValidationError('Email e App Password são obrigatórios.')
    except ValidationError as e:
        flash(f'Erro: {str(e)}', 'error')
        return redirect(url_for('profile.email_settings'))

    try:
        # Upsert simples
        existing = query_db(
            "SELECT usuario_cs FROM email_accounts WHERE usuario_cs = %s",
            (usuario_cs_email,), one=True
        )
        if existing:
            execute_db(
                "UPDATE email_accounts SET smtp_user = %s, smtp_password = %s, from_name = %s, active = 1, updated_at = CURRENT_TIMESTAMP WHERE usuario_cs = %s",
                (smtp_user, smtp_password, from_name, usuario_cs_email)
            )
        else:
            execute_db(
                "INSERT INTO email_accounts (usuario_cs, smtp_user, smtp_password, from_name, active) VALUES (%s, %s, %s, %s, 1)",
                (usuario_cs_email, smtp_user, smtp_password, from_name)
            )
        flash('Configurações de e-mail salvas com sucesso.', 'success')
    except Exception as e:
        print(f"ERRO ao salvar configurações de e-mail para {usuario_cs_email}: {e}")
        flash('Erro ao salvar configurações de e-mail.', 'error')

    return redirect(url_for('profile.email_settings'))


@profile_bp.route('/email/test', methods=['POST'])
@login_required
def email_settings_test():
    from ..email_utils import send_email_with_credentials
    usuario_cs_email = g.user_email
    try:
        test_email = sanitize_string(request.form.get('test_email', ''), max_length=200)
        if not test_email:
            raise ValidationError('Informe um e-mail de teste válido.')
    except ValidationError as e:
        flash(f'Erro: {str(e)}', 'error')
        return redirect(url_for('profile.email_settings'))

    settings = query_db(
        "SELECT * FROM email_accounts WHERE usuario_cs = %s AND active = 1",
        (usuario_cs_email,), one=True
    )
    if not settings:
        flash('Nenhuma configuração de e-mail ativa encontrada para seu usuário.', 'warning')
        return redirect(url_for('profile.email_settings'))

    # Usa Gmail padrão com TLS
    ok = send_email_with_credentials(
        to_email=test_email,
        subject='Teste de envio - CSAPP',
        body_text='Este é um e-mail de teste do CSAPP.',
        body_html='<p>Este é um <strong>e-mail de teste</strong> do CSAPP.</p>',
        reply_to=usuario_cs_email,
        from_name=settings.get('from_name') or usuario_cs_email,
        host='smtp.gmail.com',
        port=587,
        user=settings.get('smtp_user'),
        password=settings.get('smtp_password'),
        from_addr=settings.get('smtp_user'),
        use_tls=True,
        use_ssl=False,
        timeout=12,
    )

    if ok:
        flash(f'E-mail de teste enviado para {test_email}.', 'success')
    else:
        flash('Falha ao enviar e-mail de teste. Verifique App Password e permissões.', 'error')

    return redirect(url_for('profile.email_settings'))