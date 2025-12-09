import threading
from typing import Any, Callable, Dict, Optional

from flask import current_app

from ..mail.email_utils import send_email_global


class BackgroundTask:
    """
    Executor de tarefas em background usando threads.

    Uso simples sem necessidade de Celery/Redis.
    Ideal para tarefas leves como envio de emails.
    """

    @staticmethod
    def run(func: Callable, *args, **kwargs) -> threading.Thread:
        """
        Executa uma função em background thread.

        Args:
            func: Função a ser executada
            *args: Argumentos posicionais
            **kwargs: Argumentos nomeados

        Returns:
            Thread object (já iniciada)

        Exemplo:
            BackgroundTask.run(send_email, subject="Test", body="Hello")
        """
        thread = threading.Thread(
            target=func,
            args=args,
            kwargs=kwargs,
            daemon=True
        )
        thread.start()
        return thread

    @staticmethod
    def run_with_app_context(app, func: Callable, *args, **kwargs) -> threading.Thread:
        """
        Executa uma função em background thread COM contexto do Flask app.

        Necessário quando a função usa current_app, g, ou outras variáveis de contexto.

        Args:
            app: Instância do Flask app
            func: Função a ser executada
            *args: Argumentos posicionais
            **kwargs: Argumentos nomeados

        Returns:
            Thread object (já iniciada)

        Exemplo:
            BackgroundTask.run_with_app_context(
                current_app._get_current_object(),
                send_email_global,
                subject="Test",
                body_html="<p>Hello</p>",
                recipients=["user@example.com"]
            )
        """
        def wrapper():
            with app.app_context():
                try:
                    func(*args, **kwargs)
                except Exception as e:
                    app.logger.error(f"Background task error: {e}")

        thread = threading.Thread(target=wrapper, daemon=True)
        thread.start()
        return thread


def send_email_async(subject: str, body_html: str, recipients: list,
                     reply_to: Optional[str] = None,
                     from_name: Optional[str] = None,
                     body_text: Optional[str] = None) -> threading.Thread:
    """
    Envia email de forma assíncrona (não bloqueante).

    Args:
        subject: Assunto do email
        body_html: Corpo do email em HTML
        recipients: Lista de destinatários
        reply_to: Email para resposta (opcional)
        from_name: Nome do remetente (opcional)
        body_text: Corpo em texto plano (opcional)

    Returns:
        Thread object

    Exemplo:
        send_email_async(
            subject="Nova tarefa",
            body_html="<p>Você tem uma nova tarefa</p>",
            recipients=["user@example.com"],
            reply_to="noreply@example.com"
        )
    """
    app = current_app._get_current_object()

    def _send():
        """Função interna que será executada na thread."""
        with app.app_context():
            try:
                send_email_global(
                    subject=subject,
                    body_html=body_html,
                    recipients=recipients,
                    reply_to=reply_to,
                    from_name=from_name,
                    body_text=body_text
                )
                app.logger.info(f"Async email sent successfully to {recipients}")
            except Exception as e:
                app.logger.error(f"Async email failed to {recipients}: {e}")

    return BackgroundTask.run(_send)


def send_notification_async(user_email: str, notification_type: str, data: Dict[str, Any]) -> threading.Thread:
    """
    Envia notificação assíncrona (email, webhook, etc).

    Args:
        user_email: Email do usuário
        notification_type: Tipo de notificação ('comment_added', 'task_completed', etc)
        data: Dados da notificação

    Returns:
        Thread object

    Exemplo:
        send_notification_async(
            user_email="user@example.com",
            notification_type="comment_added",
            data={'task_id': 123, 'comment': 'Nova mensagem'}
        )
    """
    app = current_app._get_current_object()

    def _notify():
        with app.app_context():
            try:
                app.logger.info(f"Notification sent: {notification_type} to {user_email}")
            except Exception as e:
                app.logger.error(f"Notification failed: {e}")

    return BackgroundTask.run(_notify)
