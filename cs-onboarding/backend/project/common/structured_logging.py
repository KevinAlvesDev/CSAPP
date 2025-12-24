"""
Sistema de logging estruturado para melhor rastreabilidade e debugging
"""

import logging
import json
from datetime import datetime, timezone
from flask import g, request, has_request_context
from functools import wraps


class StructuredLogger:
    """Logger que adiciona contexto estruturado aos logs"""
    
    def __init__(self, logger_name: str):
        self.logger = logging.getLogger(logger_name)
    
    def _get_context(self):
        """Extrai contexto da requisição atual"""
        context = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
        }
        
        if has_request_context():
            context.update({
                'request_id': getattr(g, 'request_id', None),
                'user_email': getattr(g, 'user_email', None),
                'ip_address': request.remote_addr,
                'method': request.method,
                'path': request.path,
                'user_agent': request.headers.get('User-Agent', '')[:100]
            })
        
        return context
    
    def info(self, message: str, **extra):
        """Log nível INFO com contexto"""
        context = self._get_context()
        context.update(extra)
        self.logger.info(f"{message} | Context: {json.dumps(context, ensure_ascii=False)}")
    
    def warning(self, message: str, **extra):
        """Log nível WARNING com contexto"""
        context = self._get_context()
        context.update(extra)
        self.logger.warning(f"{message} | Context: {json.dumps(context, ensure_ascii=False)}")
    
    def error(self, message: str, exc_info=False, **extra):
        """Log nível ERROR com contexto"""
        context = self._get_context()
        context.update(extra)
        self.logger.error(f"{message} | Context: {json.dumps(context, ensure_ascii=False)}", exc_info=exc_info)
    
    def critical(self, message: str, exc_info=False, **extra):
        """Log nível CRITICAL com contexto"""
        context = self._get_context()
        context.update(extra)
        self.logger.critical(f"{message} | Context: {json.dumps(context, ensure_ascii=False)}", exc_info=exc_info)


def log_function_call(logger: StructuredLogger = None):
    """
    Decorator para logar entrada e saída de funções.
    Útil para debugging e auditoria.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            nonlocal logger
            if logger is None:
                logger = StructuredLogger(f.__module__)
            
            # Log entrada
            logger.info(
                f"Entering {f.__name__}",
                function=f.__name__,
                args_count=len(args),
                kwargs_keys=list(kwargs.keys())
            )
            
            try:
                result = f(*args, **kwargs)
                
                # Log saída bem-sucedida
                logger.info(
                    f"Exiting {f.__name__} successfully",
                    function=f.__name__,
                    has_result=result is not None
                )
                
                return result
                
            except Exception as e:
                # Log erro
                logger.error(
                    f"Error in {f.__name__}: {str(e)}",
                    function=f.__name__,
                    error_type=type(e).__name__,
                    exc_info=True
                )
                raise
        
        return decorated_function
    return decorator


def log_database_query(query_type: str = "SELECT"):
    """
    Decorator para logar queries de banco de dados.
    Útil para performance monitoring.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            logger = StructuredLogger('database')
            start_time = datetime.now(timezone.utc)
            
            try:
                result = f(*args, **kwargs)
                
                duration = (datetime.now(timezone.utc) - start_time).total_seconds()
                
                # Log query bem-sucedida
                logger.info(
                    f"Database {query_type} completed",
                    query_type=query_type,
                    duration_seconds=duration,
                    function=f.__name__
                )
                
                # Alerta se query demorada
                if duration > 1.0:  # Mais de 1 segundo
                    logger.warning(
                        f"Slow database query detected",
                        query_type=query_type,
                        duration_seconds=duration,
                        function=f.__name__
                    )
                
                return result
                
            except Exception as e:
                duration = (datetime.now(timezone.utc) - start_time).total_seconds()
                
                logger.error(
                    f"Database {query_type} failed: {str(e)}",
                    query_type=query_type,
                    duration_seconds=duration,
                    function=f.__name__,
                    error_type=type(e).__name__,
                    exc_info=True
                )
                raise
        
        return decorated_function
    return decorator


def log_external_api_call(api_name: str):
    """
    Decorator para logar chamadas a APIs externas.
    Útil para monitorar integrações.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            logger = StructuredLogger('external_api')
            start_time = datetime.now(timezone.utc)
            
            logger.info(
                f"Calling external API: {api_name}",
                api_name=api_name,
                function=f.__name__
            )
            
            try:
                result = f(*args, **kwargs)
                
                duration = (datetime.now(timezone.utc) - start_time).total_seconds()
                
                logger.info(
                    f"External API call successful: {api_name}",
                    api_name=api_name,
                    duration_seconds=duration,
                    function=f.__name__
                )
                
                return result
                
            except Exception as e:
                duration = (datetime.now(timezone.utc) - start_time).total_seconds()
                
                logger.error(
                    f"External API call failed: {api_name} - {str(e)}",
                    api_name=api_name,
                    duration_seconds=duration,
                    function=f.__name__,
                    error_type=type(e).__name__,
                    exc_info=True
                )
                raise
        
        return decorated_function
    return decorator


class AuditLogger:
    """Logger especializado para auditoria de ações críticas"""
    
    def __init__(self):
        self.logger = StructuredLogger('audit')
    
    def log_user_action(self, action: str, resource_type: str, resource_id: any = None, 
                       details: dict = None, success: bool = True):
        """
        Loga ação do usuário para auditoria.
        
        Args:
            action: Ação realizada (create, update, delete, view, etc)
            resource_type: Tipo de recurso (implantacao, user, checklist, etc)
            resource_id: ID do recurso afetado
            details: Detalhes adicionais da ação
            success: Se a ação foi bem-sucedida
        """
        log_data = {
            'action': action,
            'resource_type': resource_type,
            'resource_id': resource_id,
            'success': success,
            'details': details or {}
        }
        
        if success:
            self.logger.info(
                f"User action: {action} {resource_type}",
                **log_data
            )
        else:
            self.logger.warning(
                f"Failed user action: {action} {resource_type}",
                **log_data
            )
    
    def log_permission_check(self, resource_type: str, resource_id: any, 
                            required_permission: str, granted: bool):
        """
        Loga verificação de permissão.
        
        Args:
            resource_type: Tipo de recurso
            resource_id: ID do recurso
            required_permission: Permissão necessária
            granted: Se a permissão foi concedida
        """
        log_data = {
            'resource_type': resource_type,
            'resource_id': resource_id,
            'required_permission': required_permission,
            'granted': granted
        }
        
        if not granted:
            self.logger.warning(
                f"Permission denied: {required_permission} on {resource_type}",
                **log_data
            )
        else:
            self.logger.info(
                f"Permission granted: {required_permission} on {resource_type}",
                **log_data
            )
    
    def log_data_export(self, export_type: str, record_count: int, format: str = 'csv'):
        """
        Loga exportação de dados.
        
        Args:
            export_type: Tipo de dados exportados
            record_count: Número de registros
            format: Formato do export
        """
        self.logger.info(
            f"Data export: {export_type}",
            export_type=export_type,
            record_count=record_count,
            format=format
        )


# Instância global do audit logger
audit_logger = AuditLogger()
