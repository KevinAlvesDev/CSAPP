class CSAPPException(Exception):
    def __init__(self, message: str, details: dict = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class DatabaseError(CSAPPException):
    pass


class ValidationError(CSAPPException):
    pass


class AuthenticationError(CSAPPException):
    pass


class AuthorizationError(CSAPPException):
    pass


class ResourceNotFoundError(CSAPPException):
    def __init__(self, resource_type: str, resource_id: any):
        message = f"{resource_type} com ID {resource_id} não encontrado"
        details = {'resource_type': resource_type, 'resource_id': resource_id}
        super().__init__(message, details)


class DuplicateResourceError(CSAPPException):
    def __init__(self, resource_type: str, identifier: str):
        message = f"{resource_type} '{identifier}' já existe"
        details = {'resource_type': resource_type, 'identifier': identifier}
        super().__init__(message, details)


class ExternalServiceError(CSAPPException):
    def __init__(self, service_name: str, original_error: Exception = None):
        message = f"Erro ao comunicar com {service_name}"
        details = {
            'service_name': service_name,
            'original_error': str(original_error) if original_error else None
        }
        super().__init__(message, details)


class FileUploadError(CSAPPException):
    def __init__(self, filename: str, reason: str):
        message = f"Erro ao fazer upload de '{filename}': {reason}"
        details = {'filename': filename, 'reason': reason}
        super().__init__(message, details)


class ConfigurationError(CSAPPException):
    pass


class RateLimitExceededError(CSAPPException):
    def __init__(self, limit: str, retry_after: int = None):
        message = f"Limite de requisições excedido: {limit}"
        details = {'limit': limit, 'retry_after': retry_after}
        super().__init__(message, details)


class BusinessLogicError(CSAPPException):
    pass
