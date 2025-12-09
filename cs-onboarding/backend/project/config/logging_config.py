import logging
import os
from logging.handlers import TimedRotatingFileHandler

from flask import g


class ContextFilter(logging.Filter):
    """Filtro para adicionar contexto do Flask aos logs.
    Preenche 'user_email' e 'user_profile' de forma resiliente, mesmo fora de app context.
    """

    def filter(self, record):
        try:
            user_email = getattr(g, 'user_email', None)
            perfil = getattr(g, 'perfil', None)
        except Exception:
            user_email = None
            perfil = None

        if user_email:
            record.user_email = user_email
            if isinstance(perfil, dict):
                perfil_acesso = perfil.get('perfil_acesso', 'unknown')
                nome = perfil.get('nome', user_email)
                record.user_profile = f"{nome} ({perfil_acesso})"
            else:
                record.user_profile = user_email
        else:
            record.user_email = 'system'
            record.user_profile = 'system'
        return True


def setup_logging(app):
    """Configura o sistema de logs para a aplicação."""

    default_dir = os.path.join(os.path.dirname(__file__), '..', 'logs')
    log_dir = app.config.get('LOG_DIR') or default_dir
    os.makedirs(log_dir, exist_ok=True)

    log_level_str = app.config.get('LOG_LEVEL', 'INFO')
    log_level = getattr(logging, str(log_level_str).upper(), logging.INFO)

    log_format = '%(asctime)s - %(levelname)s - %(user_email)s - %(user_profile)s - %(name)s - %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'
    formatter = logging.Formatter(log_format, date_format)

    rotation_enabled = bool(app.config.get('LOG_ROTATION_ENABLED', True))
    retention_days = int(app.config.get('LOG_RETENTION_DAYS', 14))

    if rotation_enabled:
        file_handler = TimedRotatingFileHandler(
            os.path.join(log_dir, 'app.log'), when='midnight', backupCount=retention_days, encoding='utf-8'
        )
        error_handler = TimedRotatingFileHandler(
            os.path.join(log_dir, 'errors.log'), when='midnight', backupCount=retention_days, encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
    else:
        file_handler = logging.FileHandler(os.path.join(log_dir, 'app.log'), encoding='utf-8')
        error_handler = logging.FileHandler(os.path.join(log_dir, 'errors.log'), encoding='utf-8')
        error_handler.setLevel(logging.ERROR)

    file_handler.setFormatter(formatter)
    file_handler.addFilter(ContextFilter())
    error_handler.setFormatter(formatter)
    error_handler.addFilter(ContextFilter())

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.addFilter(ContextFilter())

    root_logger = logging.getLogger('root')
    root_logger.setLevel(log_level)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(error_handler)
    root_logger.addHandler(console_handler)

    app.logger.setLevel(log_level)
    app.logger.addHandler(file_handler)
    app.logger.addHandler(error_handler)
    app.logger.addHandler(console_handler)
    app.logger.addFilter(ContextFilter())

    for name in ['app', 'auth', 'api', 'database', 'implantacao', 'gamification', 'analytics', 'security', 'management', 'planos']:
        named_logger = logging.getLogger(name)
        named_logger.setLevel(log_level)
        named_logger.addHandler(file_handler)
        named_logger.addHandler(error_handler)
        named_logger.addHandler(console_handler)
        named_logger.addFilter(ContextFilter())

    app.logger.info('Sistema de logging configurado com sucesso')


def get_logger(name):
    """Obtém um logger com o nome especificado"""
    return logging.getLogger(name)


auth_logger = get_logger('auth')
api_logger = get_logger('api')
db_logger = get_logger('database')
implantacao_logger = get_logger('implantacao')
gamification_logger = get_logger('gamification')
analytics_logger = get_logger('analytics')
security_logger = get_logger('security')
management_logger = get_logger('management')
app_logger = get_logger('app')
planos_logger = get_logger('planos')
