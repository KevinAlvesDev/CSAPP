
import smtplib
import socket
from email.mime.text import MIMEText
import ssl
from email.mime.multipart import MIMEMultipart
from werkzeug.security import generate_password_hash, check_password_hash
import requests
from ..db import query_db, execute_db
from flask import current_app
from ..config.logging_config import security_logger, app_logger
import re

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

    Objetivo: permitir configuração com apenas e-mail + app password.
    """
    if not user_email or '@' not in user_email:
        raise ValueError("E-mail inválido para detecção de SMTP.")

    domain = user_email.split('@', 1)[1].lower().strip()

    COMMON = {

        'gmail.com': ('smtp.gmail.com', 587, True, False),
        'googlemail.com': ('smtp.gmail.com', 587, True, False),

        'outlook.com': ('smtp.office365.com', 587, True, False),
        'hotmail.com': ('smtp.office365.com', 587, True, False),
        'live.com': ('smtp.office365.com', 587, True, False),
        'office365.com': ('smtp.office365.com', 587, True, False),
        'msn.com': ('smtp.office365.com', 587, True, False),

        'yahoo.com': ('smtp.mail.yahoo.com', 587, True, False),
        'yahoo.com.br': ('smtp.mail.yahoo.com', 587, True, False),

        'icloud.com': ('smtp.mail.me.com', 587, True, False),
        'me.com': ('smtp.mail.me.com', 587, True, False),
        'mac.com': ('smtp.mail.me.com', 587, True, False),

        'zoho.com': ('smtp.zoho.com', 587, True, False),

        'yandex.com': ('smtp.yandex.com', 587, True, False),
        'yandex.ru': ('smtp.yandex.ru', 587, True, False),

        'uol.com.br': ('smtp.uol.com.br', 587, True, False),
        'bol.com.br': ('smtp.bol.com.br', 587, True, False),
        'terra.com.br': ('smtp.terra.com.br', 587, True, False),
        'ig.com.br': ('smtp.ig.com.br', 587, True, False),
        'globo.com': ('smtp.globo.com', 587, True, False),
    }

    if domain in COMMON:
        host, port, use_tls, use_ssl = COMMON[domain]
        app_logger.info(f"Detecção SMTP: {domain} -> {host}:{port} (TLS={use_tls}, SSL={use_ssl})")
        return {
            'host': host,
            'port': port,
            'use_tls': use_tls,
            'use_ssl': use_ssl,
        }

    if re.search(r"(\.onmicrosoft\.com|\.office365\.com)$", domain):
        return {
            'host': 'smtp.office365.com',
            'port': 587,
            'use_tls': True,
            'use_ssl': False,
        }

    candidates = [
        f"smtp.{domain}",
        f"mail.{domain}",
    ]


    chosen = candidates[0]
    app_logger.info(f"Detecção SMTP: domínio desconhecido '{domain}', usando heurística -> {chosen}:587 (TLS)")
    return {
        'host': chosen,
        'port': 587,
        'use_tls': True,
        'use_ssl': False,
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
            one=True
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
    host = data.get('host')
    port = data.get('port')
    user = data.get('user')                                                                  
    password = data.get('password')                                     
    use_tls = data.get('use_tls', 'true').lower() == 'true'
    use_ssl = data.get('use_ssl', 'false').lower() == 'true'

    if not all([user_email, host, port, user]):
        raise ValueError("Dados de SMTP incompletos para salvar.")

    try:


        if password:
            hashed_password_to_save = _hash_password(password)


            sql = """
                INSERT INTO smtp_settings (usuario_email, host, port, "user", password, use_tls, use_ssl)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (usuario_email) DO UPDATE SET
                    host = EXCLUDED.host,
                    port = EXCLUDED.port,
                    "user" = EXCLUDED."user",
                    password = EXCLUDED.password,
                    use_tls = EXCLUDED.use_tls,
                    use_ssl = EXCLUDED.use_ssl;
            """
            params = (user_email, host, int(port), user, hashed_password_to_save, use_tls, use_ssl)
        
        else:


            sql = """
                INSERT INTO smtp_settings (usuario_email, host, port, "user", use_tls, use_ssl)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (usuario_email) DO UPDATE SET
                    host = EXCLUDED.host,
                    port = EXCLUDED.port,
                    "user" = EXCLUDED."user",
                    use_tls = EXCLUDED.use_tls,
                    use_ssl = EXCLUDED.use_ssl;
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
        
    hashed_password = settings.get('hashed_password')

    if not _check_password(hashed_password, plain_password):
        security_logger.warning(f"Falha no teste SMTP (Senha não confere com o HASH salvo) para usuário {settings.get('user')}")
        raise smtplib.SMTPAuthenticationError(535, b"Senha invalida. Nao corresponde a configuracao salva.")

    host = settings.get('host')
    port = int(settings.get('port', 587))
    user = settings.get('user')                                                           
    use_tls = settings.get('use_tls', True)
    use_ssl = settings.get('use_ssl', False)
    
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
        raise NetworkError(f"Erro de conexao: {e}")
    
    except Exception as e:
        app_logger.error(f"Erro inesperado no teste SMTP para {user}: {e}")
        raise ValueError(f"Erro de conexao: {e}")


def send_email(subject, body_html, recipients, smtp_settings, plain_password, from_name=None, reply_to=None):
    """
    Envia um e-mail real usando as configurações validadas.
    Requer a senha em texto plano, pois ela não é armazenada de forma reversível.
    """


    host = smtp_settings.get('host')
    port = int(smtp_settings.get('port', 587))
    user = smtp_settings.get('user')
    use_tls = smtp_settings.get('use_tls', True)
    use_ssl = smtp_settings.get('use_ssl', False)
    
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = f"{from_name} <{user}>" if from_name else user
    msg['To'] = ", ".join(recipients)
    if reply_to:
        msg['Reply-To'] = reply_to
    
    msg.attach(MIMEText(body_html, 'html'))
    
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

def send_email_with_credentials(to_email, subject, body_text, body_html, reply_to,
                                from_name, host, port, user, password, from_addr,
                                use_tls=True, use_ssl=False, timeout=10):
    """
    Envia e-mail usando credenciais explícitas (branch usado no comentário externo).
    Retorna True em caso de sucesso; False em falha.
    """
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = f"{from_name} <{from_addr}>" if from_name else from_addr
        msg['To'] = to_email
        if reply_to:
            msg['Reply-To'] = reply_to

        if body_text:
            msg.attach(MIMEText(body_text, 'plain'))
        if body_html:
            msg.attach(MIMEText(body_html, 'html'))

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
    driver = (cfg.get('EMAIL_DRIVER') or 'smtp').lower()

    from_addr = cfg.get('SMTP_FROM') or cfg.get('SMTP_USER')
    if not from_addr:
        raise ValueError('Configuração de e-mail inválida: remetente (SMTP_FROM) ausente.')

    if driver == 'sendgrid':
        api_key = cfg.get('SENDGRID_API_KEY')
        if not api_key:
            raise ValueError('SendGrid não configurado: defina SENDGRID_API_KEY.')

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
            "personalizations": [{
                "to": [{"email": r} for r in recipients],
                "subject": subject,
            }],
            "content": content
        }
        if reply_to:
            payload["reply_to"] = {"email": reply_to}

        try:
            disable_tracking_env = str(cfg.get('SENDGRID_DISABLE_TRACKING', '')).lower() in ('1', 'true', 'yes')
            domains_cfg = cfg.get('EMAIL_DISABLE_TRACKING_DOMAINS')
            disable_for_domain = False
            if domains_cfg:
                domains_set = {d.strip().lower() for d in str(domains_cfg).split(',') if d.strip()}
                for r in recipients:
                    if '@' in r:
                        r_dom = r.split('@', 1)[1].lower()
                        if r_dom in domains_set:
                            disable_for_domain = True
                            break
            if disable_tracking_env or disable_for_domain:
                payload["tracking_settings"] = {
                    "click_tracking": {"enable": False, "enable_text": False},
                    "open_tracking": {"enable": False}
                }
        except Exception:

            pass

        try:
            base = cfg.get('SENDGRID_ENDPOINT', 'https://api.sendgrid.com')
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
                msg_id = resp.headers.get('X-Message-Id') or resp.headers.get('X-Message-ID')
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

    host = cfg.get('SMTP_HOST')
    port = int(cfg.get('SMTP_PORT', 587))
    user = cfg.get('SMTP_USER')
    password = cfg.get('SMTP_PASSWORD')
    use_tls = cfg.get('SMTP_USE_TLS', True)
    use_ssl = cfg.get('SMTP_USE_SSL', False)

    if not host:
        raise ValueError('SMTP global não configurado (host ausente).')

    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = f"{from_name} <{from_addr}>" if from_name else from_addr
    msg['To'] = ", ".join(recipients)
    if reply_to:
        msg['Reply-To'] = reply_to
    if body_text:
        msg.attach(MIMEText(body_text, 'plain'))
    if body_html:
        msg.attach(MIMEText(body_html, 'html'))

    try:
        if use_ssl:
            context = ssl.create_default_context()
            server = smtplib.SMTP_SSL(host, port, context=context)
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
    except Exception as e:
        app_logger.error(f"Falha no envio de e-mail global (SMTP): {e}")
        raise
    

def send_external_comment_notification(implantacao, comentario):
    """
    Envia notificação de um novo comentário externo.
    
    *** ATENÇÃO: Esta função está quebrada ***
    Ela foi desenhada para um SMTP GLOBAL (id=1).
    Agora, ela precisa ser redesenhada. Qual usuário deve enviar o e-mail?
    O 'implantador_email' da implantação?
    
    Esta função precisa ser refatorada para:
    1. Obter o `implantador_email` da `implantacao`.
    2. Carregar as configurações SMTP desse implantador (load_smtp_settings(implantador_email)).
    3. Ela NÃO PODE ENVIAR, pois não temos a senha de texto plano do implantador.
    
    A funcionalidade de "notificação por e-mail" precisa ser repensada.
    Por enquanto, vamos apenas logar e falhar silenciosamente.
    """
    
    implantador_email = implantacao.get('implantador_email')
    
    app_logger.warning(
        f"Tentativa de envio de notificacao de comentario para {implantador_email} (RECURSO DESATIVADO). "
        f"A funcao 'send_external_comment_notification' precisa ser refatorada para o sistema de SMTP por usuario."
    )
    return False




