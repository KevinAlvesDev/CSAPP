# backend/project/sentry_config.py
"""
Configuração do Sentry para monitoramento de erros em produção.

Sentry captura automaticamente:
- Exceções não tratadas
- Erros de HTTP (4xx, 5xx)
- Performance (traces)
- Breadcrumbs (logs de contexto)
"""

import os

# Importações opcionais (Sentry pode não estar instalado)
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
        SENTRY_DSN: URL do projeto Sentry (obtenha em https://sentry.io/)
        FLASK_ENV: Ambiente (development, staging, production)
    
    Exemplo de .env:
        SENTRY_DSN=https://abc123@o123456.ingest.sentry.io/123456
        FLASK_ENV=production
    """
    # Verifica se Sentry está disponível
    if not SENTRY_AVAILABLE:
        app.logger.info("Sentry não disponível (sentry-sdk não instalado)")
        return

    sentry_dsn = app.config.get('SENTRY_DSN') or os.environ.get('SENTRY_DSN')

    # Só inicializa se DSN estiver configurado
    if not sentry_dsn:
        app.logger.info("Sentry não configurado (SENTRY_DSN não definido)")
        return
    
    # Determina ambiente
    environment = app.config.get('FLASK_ENV', 'production')
    
    # Configuração de logging
    logging_integration = LoggingIntegration(
        level=None,  # Captura todos os níveis
        event_level='ERROR'  # Envia eventos apenas para ERROR e acima
    )
    
    # Inicializa Sentry
    sentry_sdk.init(
        dsn=sentry_dsn,
        integrations=[
            FlaskIntegration(),
            logging_integration,
        ],
        
        # Configurações de performance
        traces_sample_rate=0.1,  # 10% das transações (ajuste conforme necessário)
        
        # Configurações de ambiente
        environment=environment,
        
        # Release (versão da aplicação)
        release=app.config.get('APP_VERSION', 'unknown'),
        
        # Configurações de privacidade
        send_default_pii=False,  # Não envia informações pessoais por padrão
        
        # Configurações de breadcrumbs
        max_breadcrumbs=50,
        
        # Filtros de eventos
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
    
    # Ignora erros 404 (Not Found) - muito comuns e não são bugs
    if event.get('level') == 'error':
        exception = event.get('exception', {}).get('values', [{}])[0]
        if exception.get('type') == 'NotFound':
            return None
    
    # Remove informações sensíveis de headers
    if 'request' in event:
        headers = event['request'].get('headers', {})
        
        # Remove tokens de autenticação
        if 'Authorization' in headers:
            headers['Authorization'] = '[Filtered]'
        
        if 'Cookie' in headers:
            headers['Cookie'] = '[Filtered]'
    
    # Adiciona contexto do usuário (se disponível)
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
    
    Exemplo:
        try:
            # código que pode falhar
        except Exception as e:
            capture_exception(e, {'user_id': 123, 'action': 'create_task'})
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
    
    Exemplo:
        capture_message('Operação crítica realizada', level='warning', 
                       context={'user_id': 123})
    """
    if context:
        with sentry_sdk.push_scope() as scope:
            for key, value in context.items():
                scope.set_extra(key, value)
            sentry_sdk.capture_message(message, level=level)
    else:
        sentry_sdk.capture_message(message, level=level)

