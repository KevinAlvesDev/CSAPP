import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler
from flask import has_app_context, g

class ContextFilter(logging.Filter):
    """Filtro para adicionar contexto do Flask aos logs"""
    
    def filter(self, record):
        if has_app_context():
            record.user_email = getattr(g, 'user_email', 'anonymous')
            record.perfil = getattr(g, 'perfil', {}).get('perfil_acesso', 'unknown')
        else:
            record.user_email = 'system'
            record.perfil = 'system'
        return True

def setup_logging(app):
    """Configura o sistema de logs para a aplicação"""
    
    # Cria diretório de logs se não existir
    log_dir = os.path.join(os.path.dirname(__file__), '..', 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    # Configuração do formato de log
    log_format = '%(asctime)s - %(levelname)s - %(user_email)s - %(perfil)s - %(name)s - %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'
    
    formatter = logging.Formatter(log_format, date_format)
    
    # Handler para arquivo de log rotativo
    file_handler = RotatingFileHandler(
        os.path.join(log_dir, 'app.log'),
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    file_handler.setFormatter(formatter)
    file_handler.addFilter(ContextFilter())
    
    # Handler para arquivo de erro (apenas erros)
    error_handler = RotatingFileHandler(
        os.path.join(log_dir, 'errors.log'),
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    error_handler.addFilter(ContextFilter())
    
    # Handler para console
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.addFilter(ContextFilter())
    
    # Configura o logger raiz
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(error_handler)
    root_logger.addHandler(console_handler)
    
    # Configura o logger da aplicação
    app.logger.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.addHandler(error_handler)
    app.logger.addHandler(console_handler)
    
    # Adiciona filtro ao logger do Flask
    app.logger.addFilter(ContextFilter())
    
    # Log inicial
    app.logger.info('Sistema de logging configurado com sucesso')

def get_logger(name):
    """Obtém um logger com o nome especificado"""
    return logging.getLogger(name)

# Loggers específicos para diferentes módulos
auth_logger = get_logger('auth')
api_logger = get_logger('api')
db_logger = get_logger('database')
implantacao_logger = get_logger('implantacao')
gamification_logger = get_logger('gamification')
analytics_logger = get_logger('analytics')
security_logger = get_logger('security')
management_logger = get_logger('management')