# project/validation.py
"""
Módulo de validação para sanitização e validação de inputs.
Protege contra SQL Injection, XSS e outros ataques.
"""

import re
import html
from datetime import datetime, date
from typing import Optional, Union, List, Any


class ValidationError(Exception):
    """Exceção levantada quando uma validação falha."""
    pass


def sanitize_string(value: str, max_length: int = None, min_length: int = 0, 
                   allow_html: bool = False, allowed_chars: str = None) -> str:
    """
    Sanitiza uma string removendo caracteres perigosos.
    
    Args:
        value: String a ser sanitizada
        max_length: Comprimento máximo permitido
        min_length: Comprimento mínimo permitido
        allow_html: Se True, permite tags HTML básicas
        allowed_chars: Regex de caracteres permitidos adicionais
    
    Returns:
        String sanitizada
    
    Raises:
        ValidationError: Se a validação falhar
    """
    if not isinstance(value, str):
        raise ValidationError("Valor deve ser uma string")
    
    # Remove espaços extras
    value = value.strip()
    
    # Verifica comprimento
    if min_length > 0 and len(value) < min_length:
        raise ValidationError(f"String deve ter no mínimo {min_length} caracteres")
    
    if max_length and len(value) > max_length:
        raise ValidationError(f"String deve ter no máximo {max_length} caracteres")
    
    # Remove caracteres de controle perigosos
    value = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', value)
    
    # Se não permitir HTML, escapa caracteres especiais
    if not allow_html:
        value = html.escape(value)
    else:
        # Permite apenas tags HTML básicas seguras
        allowed_tags = ['<b>', '</b>', '<i>', '</i>', '<u>', '</u>', '<br>', '<br/>']
        for tag in allowed_tags:
            value = value.replace(tag, tag.lower())
        # Remove qualquer outra tag HTML
        value = re.sub(r'<[^>]*>', '', value)
    
    # Verifica caracteres permitidos adicionais
    if allowed_chars:
        if not re.match(f'^[a-zA-Z0-9\\s{allowed_chars}]+$', value):
            raise ValidationError(f"Caracteres inválidos detectados. Use apenas: {allowed_chars}")
    
    return value


def validate_email(email: str) -> str:
    """
    Valida e sanitiza um endereço de email.
    
    Args:
        email: Email a ser validado
    
    Returns:
        Email validado e em lowercase
    
    Raises:
        ValidationError: Se o email for inválido
    """
    if not isinstance(email, str):
        raise ValidationError("Email deve ser uma string")
    
    email = email.strip().lower()
    
    # Regex para email válido
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    if not re.match(email_regex, email):
        raise ValidationError("Email inválido")
    
    if len(email) > 254:  # RFC 5321
        raise ValidationError("Email muito longo")
    
    return email


def validate_integer(value: Any, min_value: int = None, max_value: int = None, 
                    allow_none: bool = False) -> Optional[int]:
    """
    Valida e converte um valor para inteiro.
    
    Args:
        value: Valor a ser validado
        min_value: Valor mínimo permitido
        max_value: Valor máximo permitido
        allow_none: Se True, permite None
    
    Returns:
        Inteiro validado ou None
    
    Raises:
        ValidationError: Se a validação falhar
    """
    if value is None and allow_none:
        return None
    
    try:
        int_value = int(value)
    except (ValueError, TypeError):
        raise ValidationError("Valor deve ser um número inteiro válido")
    
    if min_value is not None and int_value < min_value:
        raise ValidationError(f"Valor deve ser no mínimo {min_value}")
    
    if max_value is not None and int_value > max_value:
        raise ValidationError(f"Valor deve ser no máximo {max_value}")
    
    return int_value


def validate_float(value: Any, min_value: float = None, max_value: float = None, 
                    allow_none: bool = False, decimal_places: int = None) -> Optional[float]:
    """
    Valida e converte um valor para float.
    
    Args:
        value: Valor a ser validado
        min_value: Valor mínimo permitido
        max_value: Valor máximo permitido
        allow_none: Se True, permite None
        decimal_places: Número máximo de casas decimais
    
    Returns:
        Float validado ou None
    
    Raises:
        ValidationError: Se a validação falhar
    """
    if value is None and allow_none:
        return None
    
    try:
        float_value = float(value)
    except (ValueError, TypeError):
        raise ValidationError("Valor deve ser um número decimal válido")
    
    if min_value is not None and float_value < min_value:
        raise ValidationError(f"Valor deve ser no mínimo {min_value}")
    
    if max_value is not None and float_value > max_value:
        raise ValidationError(f"Valor deve ser no máximo {max_value}")
    
    if decimal_places is not None:
        # Verifica casas decimais
        str_value = str(float_value)
        if '.' in str_value:
            decimal_part = str_value.split('.')[1]
            if len(decimal_part) > decimal_places:
                raise ValidationError(f"Valor deve ter no máximo {decimal_places} casas decimais")
    
    return float_value


def validate_date(value: Any, allow_none: bool = False, 
                   min_date: date = None, max_date: date = None) -> Optional[date]:
    """
    Valida e converte um valor para date.
    
    Args:
        value: Valor a ser validado (string no formato YYYY-MM-DD ou date object)
        allow_none: Se True, permite None
        min_date: Data mínima permitida
        max_date: Data máxima permitida
    
    Returns:
        Date validado ou None
    
    Raises:
        ValidationError: Se a validação falhar
    """
    if value is None and allow_none:
        return None
    
    if isinstance(value, date):
        date_value = value
    elif isinstance(value, str):
        try:
            date_value = datetime.strptime(value, '%Y-%m-%d').date()
        except ValueError:
            raise ValidationError("Data deve estar no formato YYYY-MM-DD")
    else:
        raise ValidationError("Data deve ser uma string no formato YYYY-MM-DD ou um objeto date")
    
    if min_date and date_value < min_date:
        raise ValidationError(f"Data deve ser no mínimo {min_date}")
    
    if max_date and date_value > max_date:
        raise ValidationError(f"Data deve ser no máximo {max_date}")
    
    return date_value


def validate_choice(value: Any, choices: List[Any], allow_none: bool = False) -> Optional[Any]:
    """
    Valida se um valor está entre as opções permitidas.
    
    Args:
        value: Valor a ser validado
        choices: Lista de valores permitidos
        allow_none: Se True, permite None
    
    Returns:
        Valor validado ou None
    
    Raises:
        ValidationError: Se a validação falhar
    """
    if value is None and allow_none:
        return None
    
    if value not in choices:
        raise ValidationError(f"Valor deve ser um de: {', '.join(map(str, choices))}")
    
    return value


def validate_sql_injection(value: str) -> str:
    """
    Verifica e previne possíveis tentativas de SQL Injection.
    
    Args:
        value: String a ser verificada
    
    Returns:
        String verificada
    
    Raises:
        ValidationError: Se detectar possível SQL injection
    """
    if not isinstance(value, str):
        return value
    
    # Palavras-chave SQL perigosas (case insensitive)
    sql_keywords = [
        'select', 'insert', 'update', 'delete', 'drop', 'create', 'alter',
        'exec', 'execute', 'script', 'declare', 'union', 'where', 'or 1=1',
        '--', '/*', '*/', 'xp_', 'sp_'
    ]
    
    value_lower = value.lower()
    
    # Verifica padrões suspeitos
    for keyword in sql_keywords:
        if keyword in value_lower:
            # Verifica se é parte de uma palavra maior ou comando suspeito
            if re.search(rf'\b{keyword}\b', value_lower):
                raise ValidationError(f"Caracteres inválidos detectados: {keyword}")
    
    # Verifica múltiplos espaços ou quebras de linha suspeitas
    if re.search(r'(\s{2,}|\n|\r)', value):
        raise ValidationError("Caracteres de espaçamento inválidos detectados")
    
    return value


def sanitize_id(value: Any) -> int:
    """
    Sanitiza e valida IDs (para prevenir SQL Injection via IDs).
    
    Args:
        value: Valor a ser validado como ID
    
    Returns:
        ID válido
    
    Raises:
        ValidationError: Se o ID for inválido
    """
    try:
        id_value = int(value)
        if id_value <= 0:
            raise ValidationError("ID deve ser um número positivo")
        return id_value
    except (ValueError, TypeError):
        raise ValidationError("ID inválido")