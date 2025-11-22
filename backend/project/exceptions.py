"""
Exceções customizadas para o projeto CSAPP.
Facilita tratamento de erros específicos e melhora debugging.
"""


class CSAPPException(Exception):
    """Exceção base para todas as exceções do CSAPP."""

    def __init__(self, message: str, details: dict = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class DatabaseError(CSAPPException):
    """Erro relacionado a operações de banco de dados."""

    pass


class ValidationError(CSAPPException):
    """Erro de validação de dados (já existe em validation.py, mas mantemos aqui para consistência)."""

    pass


class AuthenticationError(CSAPPException):
    """Erro de autenticação (login, senha, etc)."""

    pass


class AuthorizationError(CSAPPException):
    """Erro de autorização (permissões insuficientes)."""

    pass


class ResourceNotFoundError(CSAPPException):
    """Recurso não encontrado (implantação, tarefa, usuário, etc)."""

    def __init__(self, resource_type: str, resource_id: any):
        message = f"{resource_type} com ID {resource_id} não encontrado"
        details = {"resource_type": resource_type, "resource_id": resource_id}
        super().__init__(message, details)


class DuplicateResourceError(CSAPPException):
    """Recurso duplicado (email já cadastrado, etc)."""

    def __init__(self, resource_type: str, identifier: str):
        message = f"{resource_type} '{identifier}' já existe"
        details = {"resource_type": resource_type, "identifier": identifier}
        super().__init__(message, details)


class ExternalServiceError(CSAPPException):
    """Erro ao comunicar com serviço externo (R2, SendGrid, Google, etc)."""

    def __init__(self, service_name: str, original_error: Exception = None):
        message = f"Erro ao comunicar com {service_name}"
        details = {
            "service_name": service_name,
            "original_error": str(original_error) if original_error else None,
        }
        super().__init__(message, details)


class FileUploadError(CSAPPException):
    """Erro no upload de arquivo."""

    def __init__(self, filename: str, reason: str):
        message = f"Erro ao fazer upload de '{filename}': {reason}"
        details = {"filename": filename, "reason": reason}
        super().__init__(message, details)


class ConfigurationError(CSAPPException):
    """Erro de configuração (variáveis de ambiente faltando, etc)."""

    pass


class RateLimitExceededError(CSAPPException):
    """Limite de requisições excedido."""

    def __init__(self, limit: str, retry_after: int = None):
        message = f"Limite de requisições excedido: {limit}"
        details = {"limit": limit, "retry_after": retry_after}
        super().__init__(message, details)


class BusinessLogicError(CSAPPException):
    """Erro de lógica de negócio (ex: não pode finalizar implantação com tarefas pendentes)."""

    pass
