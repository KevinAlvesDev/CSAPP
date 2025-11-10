import smtplib
from email.message import EmailMessage
from email.utils import formataddr
from typing import Optional
from flask import current_app
import base64
import requests

def send_email(
    to_email: str,
    subject: str,
    body_text: str,
    body_html: Optional[str] = None,
    reply_to: Optional[str] = None,
    from_name: Optional[str] = None,
) -> bool:
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
    timeout = cfg.get('SMTP_TIMEOUT', 12)  # falha rápida para ambientes com egress restrito

    if not host or not port or not from_addr:
        return False

    msg = EmailMessage()
    msg['Subject'] = subject
    # Exibe nome do autor no From, mantendo o endereço autenticado
    if from_name:
        msg['From'] = formataddr((from_name, from_addr))
    else:
        msg['From'] = from_addr
    msg['To'] = to_email
    if reply_to:
        msg['Reply-To'] = reply_to
    msg.set_content(body_text or '')
    if body_html:
        msg.add_alternative(body_html, subtype='html')

    try:
        if use_ssl:
            with smtplib.SMTP_SSL(host, port, timeout=timeout) as server:
                if user and password:
                    server.login(user, password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(host, port, timeout=timeout) as server:
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


def send_email_with_credentials(
    to_email: str,
    subject: str,
    body_text: str,
    body_html: Optional[str] = None,
    reply_to: Optional[str] = None,
    from_name: Optional[str] = None,
    host: Optional[str] = None,
    port: Optional[int] = None,
    user: Optional[str] = None,
    password: Optional[str] = None,
    from_addr: Optional[str] = None,
    use_tls: bool = True,
    use_ssl: bool = False,
    timeout: int = 12,
) -> bool:
    """
    Envia e-mail usando credenciais explícitas (por usuário). Útil para App Password do Gmail.
    """
    if not host or not port or not (from_addr or user):
        return False

    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = formataddr((from_name, from_addr or user)) if from_name else (from_addr or user)
    msg['To'] = to_email
    if reply_to:
        msg['Reply-To'] = reply_to
    msg.set_content(body_text or '')
    if body_html:
        msg.add_alternative(body_html, subtype='html')

    try:
        if use_ssl:
            with smtplib.SMTP_SSL(host, port, timeout=timeout) as server:
                if user and password:
                    server.login(user, password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(host, port, timeout=timeout) as server:
                server.ehlo()
                if use_tls:
                    server.starttls()
                    server.ehlo()
                if user and password:
                    server.login(user, password)
                server.send_message(msg)
        return True
    except Exception as e:
        print(f"AVISO: Falha ao enviar (credenciais de usuário) para {to_email}: {e}")
        return False


def send_email_via_gmail_api(
    access_token: str,
    to_email: str,
    subject: str,
    body_text: str,
    body_html: Optional[str] = None,
    reply_to: Optional[str] = None,
    from_name: Optional[str] = None,
) -> bool:
    """
    Envia e-mail via Gmail API (HTTPS) usando o access_token OAuth do usuário.
    Observação: o Gmail definirá o "From" automaticamente para a conta autenticada.
    """
    try:
        msg = EmailMessage()
        msg['Subject'] = subject
        msg['To'] = to_email
        if reply_to:
            msg['Reply-To'] = reply_to
        # Não define explicitamente o From; Gmail usa a conta autenticada.
        if body_html:
            msg.set_content(body_text or '')
            msg.add_alternative(body_html, subtype='html')
        else:
            msg.set_content(body_text or '')

        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode('ascii')
        resp = requests.post(
            'https://gmail.googleapis.com/gmail/v1/users/me/messages/send',
            headers={'Authorization': f'Bearer {access_token}', 'Content-Type': 'application/json'},
            json={'raw': raw},
            timeout=12,
        )
        if resp.status_code >= 400:
            print(f"AVISO: Falha Gmail API ({resp.status_code}): {resp.text}")
            return False
        return True
    except Exception as e:
        print(f"AVISO: Erro ao enviar via Gmail API: {e}")
        return False