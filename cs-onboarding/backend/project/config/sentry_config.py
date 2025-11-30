"""
Configuração do Sentry para monitoramento de erros em produção.

Sentry captura automaticamente:
- Exceções não tratadas
- Erros de HTTP (4xx, 5xx)
- Performance (traces)
- Breadcrumbs (logs de contexto)
"""

import os

try:
    import sentry_sdk
    from sentry_sdk.integrations.flask import FlaskIntegration
    from sentry_sdk.integrations.logging import LoggingIntegration
    SENTRY_AVAILABLE = True
except ImportError:
    SENTRY_AVAILABLE = False


def init_sentry(app):
    """
    Inicializa o Sentry para monitoramento de erros.

    Args:
        app: Instância do Flask app

    Configuração:
        SENTRY_DSN: URL do projeto Sentry
        FLASK_ENV: Ambiente (development, staging, production)
    """

    if not SENTRY_AVAILABLE:
        app.logger.info("Sentry não disponível (sentry-sdk não instalado)")
        return

    sentry_dsn = app.config.get('SENTRY_DSN') or os.environ.get('SENTRY_DSN')

    if not sentry_dsn:
        app.logger.info("Sentry não configurado (SENTRY_DSN não definido)")
        return

    environment = app.config.get('FLASK_ENV', 'production')

    logging_integration = LoggingIntegration(
        level=None,
        event_level='ERROR'
    )

    sentry_sdk.init(
        dsn=sentry_dsn,
        integrations=[
            FlaskIntegration(),
            logging_integration,
        ],
        traces_sample_rate=0.1,
        environment=environment,
        release=app.config.get('APP_VERSION', 'unknown'),
        send_default_pii=False,
        max_breadcrumbs=50,
        before_send=before_send_filter,
    )

    app.logger.info(f"Sentry inicializado: environment={environment}, traces_sample_rate=0.1")


def before_send_filter(event, hint):
    """
    Filtro de eventos antes de enviar para o Sentry.

    Permite:
    - Remover informações sensíveis
    - Ignorar certos tipos de erro
    - Adicionar contexto adicional

    Args:
        event: Evento do Sentry
        hint: Dica com informações adicionais

    Returns:
        event modificado ou None para ignorar
    """

    if event.get('level') == 'error':
        exception = event.get('exception', {}).get('values', [{}])[0]
        if exception.get('type') == 'NotFound':
            return None

    if 'request' in event:
        headers = event['request'].get('headers', {})
        if 'Authorization' in headers:
            headers['Authorization'] = '[Filtered]'
        if 'Cookie' in headers:
            headers['Cookie'] = '[Filtered]'

    try:
        from flask import g
        if hasattr(g, 'user_email'):
            event.setdefault('user', {})['email'] = g.user_email
    except Exception:
        pass

    return event


def capture_exception(exception, context=None):
    """
    Captura uma exceção manualmente e envia para o Sentry.

    Args:
        exception: Exceção a ser capturada
        context: Contexto adicional (dict)
    """
    if context:
        with sentry_sdk.push_scope() as scope:
            for key, value in context.items():
                scope.set_extra(key, value)
            sentry_sdk.capture_exception(exception)
    else:
        sentry_sdk.capture_exception(exception)


def capture_message(message, level='info', context=None):
    """
    Captura uma mensagem manualmente e envia para o Sentry.

    Args:
        message: Mensagem a ser capturada
        level: Nível (debug, info, warning, error, fatal)
        context: Contexto adicional (dict)
    """
    if context:
        with sentry_sdk.push_scope() as scope:
            for key, value in context.items():
                scope.set_extra(key, value)
            sentry_sdk.capture_message(message, level=level)
    else:
        sentry_sdk.capture_message(message, level=level)
