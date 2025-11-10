import smtplib
from email.message import EmailMessage
from typing import Optional
from flask import current_app

def send_email(to_email: str, subject: str, body_text: str, body_html: Optional[str] = None) -> bool:
    """
    Envia um e-mail simples via SMTP usando configurações de current_app.config.
    Retorna True em caso de sucesso, False caso contrário.
    """
    cfg = current_app.config
    host = cfg.get('SMTP_HOST')
    port = cfg.get('SMTP_PORT', 587)
    user = cfg.get('SMTP_USER')
    password = cfg.get('SMTP_PASSWORD')
    from_addr = cfg.get('SMTP_FROM') or user
    use_tls = cfg.get('SMTP_USE_TLS', True)
    use_ssl = cfg.get('SMTP_USE_SSL', False)

    if not host or not port or not from_addr:
        return False

    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = from_addr
    msg['To'] = to_email
    msg.set_content(body_text or '')
    if body_html:
        msg.add_alternative(body_html, subtype='html')

    try:
        if use_ssl:
            with smtplib.SMTP_SSL(host, port) as server:
                if user and password:
                    server.login(user, password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(host, port) as server:
                server.ehlo()
                if use_tls:
                    server.starttls()
                    server.ehlo()
                if user and password:
                    server.login(user, password)
                server.send_message(msg)
        return True
    except Exception as e:
        print(f"AVISO: Falha ao enviar e-mail para {to_email}: {e}")
        return False