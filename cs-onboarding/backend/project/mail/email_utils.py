import re
import smtplib
import socket
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import requests
from flask import current_app
from werkzeug.security import check_password_hash, generate_password_hash

from ..config.logging_config import app_logger, security_logger
from ..db import execute_db, query_db


class NetworkError(Exception):
    pass


def _hash_password(password):
    """Gera um hash para a senha."""
    if not password:
        return None
    return generate_password_hash(password)


def _check_password(hashed_password, provided_password):
    """Verifica a senha fornecida contra o hash."""
    if not hashed_password or not provided_password:
        return False
    return check_password_hash(hashed_password, provided_password)


def detect_smtp_settings(user_email):
    """
    Detecta automaticamente host/porta/SSL/TLS com base no domínio do e-mail.
    Retorna dict: {host, port, use_tls, use_ssl}.
    """
    if not user_email or "@" not in user_email:
        raise ValueError("E-mail inválido para detecção de SMTP.")

    domain = user_email.split("@", 1)[1].lower().strip()

    COMMON = {
        "gmail.com": ("smtp.gmail.com", 587, True, False),
        "googlemail.com": ("smtp.gmail.com", 587, True, False),
        "outlook.com": ("smtp.office365.com", 587, True, False),
        "hotmail.com": ("smtp.office365.com", 587, True, False),
        "live.com": ("smtp.office365.com", 587, True, False),
        "office365.com": ("smtp.office365.com", 587, True, False),
        "msn.com": ("smtp.office365.com", 587, True, False),
        "yahoo.com": ("smtp.mail.yahoo.com", 587, True, False),
        "yahoo.com.br": ("smtp.mail.yahoo.com", 587, True, False),
        "icloud.com": ("smtp.mail.me.com", 587, True, False),
        "me.com": ("smtp.mail.me.com", 587, True, False),
        "mac.com": ("smtp.mail.me.com", 587, True, False),
        "zoho.com": ("smtp.zoho.com", 587, True, False),
        "yandex.com": ("smtp.yandex.com", 587, True, False),
        "yandex.ru": ("smtp.yandex.ru", 587, True, False),
        "uol.com.br": ("smtp.uol.com.br", 587, True, False),
        "bol.com.br": ("smtp.bol.com.br", 587, True, False),
        "terra.com.br": ("smtp.terra.com.br", 587, True, False),
        "ig.com.br": ("smtp.ig.com.br", 587, True, False),
        "globo.com": ("smtp.globo.com", 587, True, False),
    }

    if domain in COMMON:
        host, port, use_tls, use_ssl = COMMON[domain]
        app_logger.info(f"Detecção SMTP: {domain} -> {host}:{port} (TLS={use_tls}, SSL={use_ssl})")
        return {
            "host": host,
            "port": port,
            "use_tls": use_tls,
            "use_ssl": use_ssl,
        }

    if re.search(r"(\.onmicrosoft\.com|\.office365\.com)$", domain):
        return {
            "host": "smtp.office365.com",
            "port": 587,
            "use_tls": True,
            "use_ssl": False,
        }

    candidates = [
        f"smtp.{domain}",
        f"mail.{domain}",
    ]

    chosen = candidates[0]
    app_logger.info(f"Detecção SMTP: domínio desconhecido '{domain}', usando heurística -> {chosen}:587 (TLS)")
    return {
        "host": chosen,
        "port": 587,
        "use_tls": True,
        "use_ssl": False,
    }


def load_smtp_settings(user_email):
    """
    Carrega as configurações SMTP para um usuário específico.
    NOTA: A senha retornada é o HASH, não a senha real.
    """
    if not user_email:
        return None

    try:
        settings = query_db(
            'SELECT host, port, "user", password as hashed_password, use_tls, use_ssl FROM smtp_settings WHERE usuario_email = %s',
            (user_email,),
            one=True,
        )
        return settings
    except Exception as e:
        app_logger.error(f"Erro ao carregar settings SMTP para {user_email}: {e}")
        return None


def save_smtp_settings(user_email, data):
    """
    Salva ou atualiza as configurações SMTP para um usuário específico.
    Armazena um hash da senha.
    """
    host = data.get("host")
    port = data.get("port")
    user = data.get("user")
    password = data.get("password")
    use_tls = data.get("use_tls", "true").lower() == "true"
    use_ssl = data.get("use_ssl", "false").lower() == "true"

    if not all([user_email, host, port, user]):
        raise ValueError("Dados de SMTP incompletos para salvar.")

    try:
        if password:
            hashed_password_to_save = _hash_password(password)

            # Verificar existência
            exists = query_db("SELECT 1 FROM smtp_settings WHERE usuario_email = %s", (user_email,), one=True)

            if exists:
                sql = """
                    UPDATE smtp_settings SET
                        host = %s,
                        port = %s,
                        "user" = %s,
                        password = %s,
                        use_tls = %s,
                        use_ssl = %s
                    WHERE usuario_email = %s
                """
                params = (host, int(port), user, hashed_password_to_save, use_tls, use_ssl, user_email)
            else:
                sql = """
                    INSERT INTO smtp_settings (usuario_email, host, port, "user", password, use_tls, use_ssl)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
                params = (user_email, host, int(port), user, hashed_password_to_save, use_tls, use_ssl)

        else:
            # Sem senha (somente update de configurações não sensíveis ou insert inicial incompleto?)
            # Assumindo comportamento original: update fields except password
            exists = query_db("SELECT 1 FROM smtp_settings WHERE usuario_email = %s", (user_email,), one=True)
            
            if exists:
                sql = """
                    UPDATE smtp_settings SET
                        host = %s,
                        port = %s,
                        "user" = %s,
                        use_tls = %s,
                        use_ssl = %s
                    WHERE usuario_email = %s
                """
                params = (host, int(port), user, use_tls, use_ssl, user_email)
            else:
                sql = """
                    INSERT INTO smtp_settings (usuario_email, host, port, "user", use_tls, use_ssl)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """
                params = (user_email, host, int(port), user, use_tls, use_ssl)

        result = execute_db(sql, params)
        if not result:
            app_logger.error(f"Persistência falhou ao salvar SMTP para {user_email} (sem retorno do execute_db)")
            raise RuntimeError("Falha ao salvar configurações SMTP.")
        app_logger.info(f"Configurações SMTP salvas para o usuário: {user_email}")

    except Exception as e:
        app_logger.error(f"Erro ao salvar settings SMTP para {user_email}: {e}")
        raise


def test_smtp_connection(settings, plain_password):
    """
    Testa a conexão SMTP e a autenticação usando as configurações e a senha em texto plano.
    'settings' deve vir de load_smtp_settings (contém o HASH da senha).
    'plain_password' deve vir do formulário de teste.
    """
    if not settings:
        raise ValueError("Configurações não encontradas.")

    hashed_password = settings.get("hashed_password")

    if not _check_password(hashed_password, plain_password):
        security_logger.warning(
            f"Falha no teste SMTP (Senha não confere com o HASH salvo) para usuário {settings.get('user')}"
        )
        raise smtplib.SMTPAuthenticationError(535, b"Senha invalida. Nao corresponde a configuracao salva.")

    host = settings.get("host")
    port = int(settings.get("port", 587))
    user = settings.get("user")
    use_tls = settings.get("use_tls", True)
    use_ssl = settings.get("use_ssl", False)

    app_logger.info(f"Testando conexão SMTP para {user} em {host}:{port} (SSL: {use_ssl}, TLS: {use_tls})")

    try:
        if use_ssl:
            context = smtplib.ssl.create_default_context()
            server = smtplib.SMTP_SSL(host, port, context=context)
        else:
            server = smtplib.SMTP(host, port, timeout=10)
            if use_tls:
                server.starttls()

        server.login(user, plain_password)
        server.quit()
        app_logger.info(f"Autenticação SMTP bem-sucedida para {user}")
        return True

    except smtplib.SMTPAuthenticationError as e:
        security_logger.warning(f"Falha de autenticacao SMTP (provedor rejeitou) para {user}: {e}")
        raise

    except (OSError, socket.gaierror, smtplib.SMTPConnectError, smtplib.SMTPServerDisconnected, TimeoutError) as e:
        app_logger.warning(f"Falha de conectividade SMTP para {user} em {host}:{port}: {e}")
        raise NetworkError(f"Erro de conexao: {e}") from e

    except Exception as e:
        app_logger.error(f"Erro inesperado no teste SMTP para {user}: {e}")
        raise ValueError(f"Erro de conexao: {e}") from e


def send_email(subject, body_html, recipients, smtp_settings, plain_password, from_name=None, reply_to=None):
    """
    Envia um e-mail real usando as configurações validadas.
    Requer a senha em texto plano, pois ela não é armazenada de forma reversível.
    """

    host = smtp_settings.get("host")
    port = int(smtp_settings.get("port", 587))
    user = smtp_settings.get("user")
    use_tls = smtp_settings.get("use_tls", True)
    use_ssl = smtp_settings.get("use_ssl", False)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{from_name} <{user}>" if from_name else user
    msg["To"] = ", ".join(recipients)
    if reply_to:
        msg["Reply-To"] = reply_to

    msg.attach(MIMEText(body_html, "html"))

    try:
        if use_ssl:
            context = smtplib.ssl.create_default_context()
            server = smtplib.SMTP_SSL(host, port, context=context)
        else:
            server = smtplib.SMTP(host, port, timeout=10)
            if use_tls:
                server.starttls()

        server.login(user, plain_password)
        server.sendmail(user, recipients, msg.as_string())
        server.quit()
        app_logger.info(f"E-mail enviado com sucesso por {user} para {recipients}")
        return True

    except Exception as e:
        app_logger.error(f"Falha ao enviar e-mail real por {user}: {e}")
        raise


def send_email_with_credentials(
    to_email,
    subject,
    body_text,
    body_html,
    reply_to,
    from_name,
    host,
    port,
    user,
    password,
    from_addr,
    use_tls=True,
    use_ssl=False,
    timeout=10,
):
    """
    Envia e-mail usando credenciais explícitas (branch usado no comentário externo).
    Retorna True em caso de sucesso; False em falha.
    """
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{from_name} <{from_addr}>" if from_name else from_addr
        msg["To"] = to_email
        if reply_to:
            msg["Reply-To"] = reply_to

        if body_text:
            msg.attach(MIMEText(body_text, "plain"))
        if body_html:
            msg.attach(MIMEText(body_html, "html"))

        if use_ssl:
            context = ssl.create_default_context()
            server = smtplib.SMTP_SSL(host, int(port), context=context, timeout=timeout)
        else:
            server = smtplib.SMTP(host, int(port), timeout=timeout)
            if use_tls:
                server.starttls()

        if user and password:
            server.login(user, password)
        server.sendmail(from_addr, [to_email], msg.as_string())
        server.quit()
        app_logger.info(f"E-mail enviado com credenciais para {to_email}")
        return True
    except Exception as e:
        app_logger.error(f"Falha ao enviar e-mail com credenciais para {to_email}: {e}")
        return False


def send_email_global(subject, body_html, recipients, from_name=None, reply_to=None, body_text=None):
    """
    Envia um e-mail usando a configuração global.
    Suporta drivers: 'smtp' (padrão) e 'sendgrid' (HTTP API em porta 443).
    Retorna True em caso de sucesso; lança exceção em falha.
    """
    cfg = current_app.config
    driver = (cfg.get("EMAIL_DRIVER") or "smtp").lower()

    from_addr = cfg.get("SMTP_FROM") or cfg.get("SMTP_USER")
    if not from_addr:
        raise ValueError("Configuração de e-mail inválida: remetente (SMTP_FROM) ausente.")

    if driver == "sendgrid":
        api_key = cfg.get("SENDGRID_API_KEY")
        if not api_key:
            raise ValueError("SendGrid não configurado: defina SENDGRID_API_KEY.")

        content = []

        if body_text:
            content.append({"type": "text/plain", "value": body_text})
        elif body_html:
            try:
                plain_fallback = re.sub(r"<[^>]+>", "", body_html)
                content.append({"type": "text/plain", "value": plain_fallback})
            except Exception:
                pass
        if body_html:
            content.append({"type": "text/html", "value": body_html})
        if not content:
            content = [{"type": "text/plain", "value": subject or "Mensagem"}]

        payload = {
            "from": {"email": from_addr, **({"name": from_name} if from_name else {})},
            "personalizations": [
                {
                    "to": [{"email": r} for r in recipients],
                    "subject": subject,
                }
            ],
            "content": content,
        }
        if reply_to:
            payload["reply_to"] = {"email": reply_to}

        try:
            disable_tracking_env = str(cfg.get("SENDGRID_DISABLE_TRACKING", "")).lower() in ("1", "true", "yes")
            domains_cfg = cfg.get("EMAIL_DISABLE_TRACKING_DOMAINS")
            disable_for_domain = False
            if domains_cfg:
                domains_set = {d.strip().lower() for d in str(domains_cfg).split(",") if d.strip()}
                for r in recipients:
                    if "@" in r:
                        r_dom = r.split("@", 1)[1].lower()
                        if r_dom in domains_set:
                            disable_for_domain = True
                            break
            if disable_tracking_env or disable_for_domain:
                payload["tracking_settings"] = {
                    "click_tracking": {"enable": False, "enable_text": False},
                    "open_tracking": {"enable": False},
                }
        except Exception:
            pass

        try:
            base = cfg.get("SENDGRID_ENDPOINT", "https://api.sendgrid.com")
            url = f"{base.rstrip('/')}/v3/mail/send"
            resp = requests.post(
                url,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=10,
            )

            if resp.status_code == 202:
                msg_id = resp.headers.get("X-Message-Id") or resp.headers.get("X-Message-ID")
                if msg_id:
                    app_logger.info(f"E-mail global (SendGrid) enviado para {recipients} (Message-ID: {msg_id})")
                else:
                    app_logger.info(f"E-mail global (SendGrid) enviado para {recipients}")
                return True
            else:
                raise RuntimeError(f"SendGrid falhou ({resp.status_code}): {resp.text}")
        except requests.RequestException as e:
            app_logger.error(f"Falha de rede no envio via SendGrid: {e}")
            raise

    host = cfg.get("SMTP_HOST")
    port = int(cfg.get("SMTP_PORT", 587))
    user = cfg.get("SMTP_USER")
    password = cfg.get("SMTP_PASSWORD")
    use_tls = cfg.get("SMTP_USE_TLS", True)
    use_ssl = cfg.get("SMTP_USE_SSL", False)

    if not host:
        raise ValueError("SMTP global não configurado (host ausente).")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{from_name} <{from_addr}>" if from_name else from_addr
    msg["To"] = ", ".join(recipients)
    if reply_to:
        msg["Reply-To"] = reply_to
    if body_text:
        msg.attach(MIMEText(body_text, "plain"))
    if body_html:
        msg.attach(MIMEText(body_html, "html"))

    try:
        if use_ssl:
            context = ssl.create_default_context()
            server = smtplib.SMTP_SSL(host, port, context=context, timeout=10)
        else:
            server = smtplib.SMTP(host, port, timeout=10)
            if use_tls:
                server.starttls()

        if user and password:
            server.login(user, password)
        server.sendmail(from_addr, recipients, msg.as_string())
        server.quit()
        app_logger.info(f"E-mail global (SMTP) enviado para {recipients}")
        return True
    except smtplib.SMTPAuthenticationError as e:
        app_logger.error(f"Falha de autenticação SMTP: {e}")
        raise
    except (OSError, socket.gaierror, smtplib.SMTPConnectError, smtplib.SMTPServerDisconnected, TimeoutError) as e:
        app_logger.error(f"Falha de conectividade SMTP ({host}:{port}): {e}")
        raise
    except Exception as e:
        app_logger.error(f"Falha no envio de e-mail global (SMTP): {e}")
        raise


def send_external_comment_notification(implantacao, comentario):
    """
    Envia notificação de um novo comentário externo para o responsável da implantação.
    Usa o sistema de email global (SMTP ou SendGrid).
    O envio é feito em background para não bloquear a requisição.

    Args:
        implantacao: dict com 'nome_empresa', 'email_responsavel'
        comentario: dict com 'texto', 'tarefa_filho', 'usuario_cs'

    Returns:
        True (sempre, pois o envio é assíncrono)
    """
    to_email = implantacao.get("email_responsavel")
    nome_empresa = implantacao.get("nome_empresa", "Empresa")
    tarefa_nome = comentario.get("tarefa_filho", "Tarefa")
    texto = comentario.get("texto", "")
    usuario_cs = comentario.get("usuario_cs", "CS")

    if not to_email:
        app_logger.warning("Email do responsável não configurado para envio de comentário externo")
        return True  # Retorna True pois a falha é na configuração, não no envio assíncrono

    subject = f"[CS Onboarding] Novo comentário na implantação - {nome_empresa}"

    body_html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background-color: #007bff; color: white; padding: 20px; border-radius: 8px 8px 0 0;">
                <h2 style="margin: 0;">Novo Comentário</h2>
            </div>
            <div style="background-color: #f8f9fa; padding: 20px; border: 1px solid #dee2e6; border-top: none; border-radius: 0 0 8px 8px;">
                <p><strong>Empresa:</strong> {nome_empresa}</p>
                <p><strong>Tarefa:</strong> {tarefa_nome}</p>
                <p><strong>Comentário de:</strong> {usuario_cs}</p>
                <hr style="border: none; border-top: 1px solid #dee2e6; margin: 15px 0;">
                <div style="background-color: white; padding: 15px; border-radius: 4px; border-left: 4px solid #007bff;">
                    <p style="margin: 0; white-space: pre-wrap;">{texto}</p>
                </div>
                <hr style="border: none; border-top: 1px solid #dee2e6; margin: 15px 0;">
                <p style="color: #6c757d; font-size: 12px;">
                    Este é um email automático do sistema CS Onboarding.
                </p>
            </div>
        </div>
    </body>
    </html>
    """

    body_text = f"""
Novo Comentário - CS Onboarding

Empresa: {nome_empresa}
Tarefa: {tarefa_nome}
Comentário de: {usuario_cs}

---
{texto}
---

Este é um email automático do sistema CS Onboarding.
    """

    # Função para enviar email em background
    def _send_email_background():
        from flask import current_app

        # Usar o contexto da aplicação Flask
        with current_app.app_context():
            try:
                send_email_global(
                    subject=subject,
                    body_html=body_html,
                    recipients=[to_email],
                    from_name="CS Onboarding",
                    body_text=body_text,
                )
                app_logger.info(f"Notificação de comentário externo enviada para {to_email}")
            except Exception as e:
                app_logger.error(f"Falha ao enviar notificação de comentário externo para {to_email}: {e}")

    # Enviar em background thread
    import threading

    from flask import current_app

    # Capturar a referência do app antes de criar a thread
    app = current_app._get_current_object()

    def _send_with_context():
        with app.app_context():
            _send_email_background()

    thread = threading.Thread(target=_send_with_context, daemon=True)
    thread.start()

    app_logger.info(f"Email de notificação agendado para envio em background para {to_email}")
    return True
