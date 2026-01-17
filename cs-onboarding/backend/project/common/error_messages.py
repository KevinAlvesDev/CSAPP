"""
Error Messages - Centralized error message system
Provides specific, user-friendly error messages for all error types
"""

# Validation errors
VALIDATION_ERRORS = {
    "email_invalid": "E-mail inválido. Use o formato: exemplo@dominio.com",
    "telefone_invalid": "Telefone inválido. Use o formato: (XX) XXXXX-XXXX",
    "cnpj_invalid": "CNPJ inválido. Verifique os dígitos verificadores.",
    "alunos_negative": "Número de alunos não pode ser negativo",
    "valor_negative": "Valor não pode ser negativo",
    "data_invalid": "Data inválida. Use o formato: DD/MM/AAAA",
    "campo_obrigatorio": "Este campo é obrigatório",
}

# Database errors
DATABASE_ERRORS = {
    "connection_failed": "Erro de conexão com o banco de dados. Tente novamente em alguns segundos.",
    "timeout": "Operação demorou muito tempo. Verifique sua conexão.",
    "constraint_violation": "Dados inválidos. Verifique os valores informados.",
    "duplicate_key": "Registro já existe no sistema.",
}

# Permission errors
PERMISSION_ERRORS = {
    "not_found": "Registro não encontrado. Ele pode ter sido excluído.",
    "permission_denied": "Você não tem permissão para realizar esta ação.",
    "not_owner": "Apenas o responsável ou gestor pode editar este registro.",
}

# Network/API errors
NETWORK_ERRORS = {
    "network_error": "Erro de conexão. Verifique sua internet e tente novamente.",
    "timeout_error": "Tempo de espera esgotado. Tente novamente.",
    "server_error": "Erro no servidor. Nossa equipe foi notificada.",
}

# OAMD specific errors
OAMD_ERRORS = {
    "oamd_not_found": "Dados não encontrados no OAMD. Verifique a chave informada.",
    "oamd_timeout": "Não foi possível consultar OAMD. Tente novamente em alguns segundos.",
    "oamd_invalid_key": "Chave OAMD inválida.",
}


def get_error_message(error_code: str, **kwargs) -> str:
    """
    Get user-friendly error message by error code.

    Args:
        error_code: Error code (e.g., 'email_invalid')
        **kwargs: Optional parameters for message formatting

    Returns:
        User-friendly error message
    """
    # Search in all error dictionaries
    for error_dict in [VALIDATION_ERRORS, DATABASE_ERRORS, PERMISSION_ERRORS, NETWORK_ERRORS, OAMD_ERRORS]:
        if error_code in error_dict:
            message = error_dict[error_code]
            if kwargs:
                return message.format(**kwargs)
            return message

    # Default message
    return "Erro desconhecido. Por favor, tente novamente."


def format_validation_errors(errors: list) -> str:
    """
    Format multiple validation errors into a single message.

    Args:
        errors: List of error messages

    Returns:
        Formatted error message
    """
    if not errors:
        return ""

    if len(errors) == 1:
        return f"❌ {errors[0]}"

    # Multiple errors
    error_list = "\n".join(f"• {error}" for error in errors)
    return f"❌ Foram encontrados os seguintes erros:\n{error_list}"
