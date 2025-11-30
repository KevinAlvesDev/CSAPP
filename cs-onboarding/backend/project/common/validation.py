"""
Módulo de validação e sanitização de inputs.
"""
import re
import html
from typing import Optional, Any


class ValidationError(Exception):
    pass


COMMON_PASSWORDS = {
    '123456', '123456789', '12345678', '12345', '1234567890',
    '111111', '000000', '123123', '1234567', '1234',
    'password', 'password1', 'password123', 'Password1', 'Password123',
    'qwerty', 'qwerty123', 'qwertyuiop', 'asdfgh', 'zxcvbn',
    'qwerty1', 'asdfghjkl', '1qaz2wsx',
    'abc123', 'welcome', 'monkey', 'dragon', 'master',
    'sunshine', 'princess', 'letmein', 'shadow', 'admin',
    'iloveyou', 'football', 'baseball', 'superman', 'batman',
    'passw0rd', 'p@ssw0rd', 'p@ssword', '123qwe', 'qwe123',
    'admin123', 'root', 'toor', 'test', 'guest',
    '2024', '2023', '2022', '2021', '2020',
}


def validate_password_strength(password: str, min_length: int = 8, max_length: int = 128) -> str:
    if not isinstance(password, str):
        raise ValidationError('Senha deve ser uma string')
    if len(password) < min_length:
        raise ValidationError(f'A senha deve ter no mínimo {min_length} caracteres.')
    if len(password) > max_length:
        raise ValidationError(f'A senha deve ter no máximo {max_length} caracteres.')
    if password.lower() in COMMON_PASSWORDS:
        raise ValidationError('Senha muito comum. Escolha uma senha mais segura.')
    if not re.search(r'[A-Z]', password):
        raise ValidationError('A senha deve conter pelo menos uma letra maiúscula (A-Z).')
    if not re.search(r'[a-z]', password):
        raise ValidationError('A senha deve conter pelo menos uma letra minúscula (a-z).')
    if not re.search(r'\d', password):
        raise ValidationError('A senha deve conter pelo menos um número (0-9).')
    if not re.search(r'[!@#$%^&*(),.?":{}|<>\-_+=\[\]\\\/:;\'`~]', password):
        raise ValidationError('A senha deve conter pelo menos um símbolo (!@#$%^&*(),.?":{}|<>).')
    if re.search(r'(.)\1{3,}', password):
        raise ValidationError('A senha não pode ter mais de 3 caracteres iguais consecutivos.')
    sequences = ['0123456789', 'abcdefghijklmnopqrstuvwxyz', 'qwertyuiop', 'asdfghjkl', 'zxcvbnm']
    password_lower = password.lower()
    for seq in sequences:
        for i in range(len(seq) - 4):
            if seq[i:i + 5] in password_lower or seq[i:i + 5][::-1] in password_lower:
                raise ValidationError('A senha não pode conter sequências simples (ex: 12345, abcde).')
    return password


def sanitize_string(value: str, max_length: int = None, min_length: int = 0, allow_html: bool = False, allowed_chars: str = None, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise ValidationError("Valor deve ser uma string")
    value = value.strip()
    if allow_empty and len(value) == 0:
        return value
    if min_length > 0 and len(value) < min_length:
        raise ValidationError(f"String deve ter no mínimo {min_length} caracteres")
    if max_length and len(value) > max_length:
        raise ValidationError(f"String deve ter no máximo {max_length} caracteres")
    value = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', value)
    if not allow_html:
        value = html.escape(value)
    else:
        allowed_tags = ['<b>', '</b>', '<i>', '</i>', '<u>', '</u>', '<br>', '<br/>']
        for tag in allowed_tags:
            value = value.replace(tag, tag.lower())
        value = re.sub(r'<[^>]*>', '', value)
    if allowed_chars:
        if not re.match(f'^[a-zA-Z0-9\\s{allowed_chars}]+$', value):
            raise ValidationError(f"Caracteres inválidos detectados. Use apenas: {allowed_chars}")
    return value


def validate_email(email: str) -> str:
    if not isinstance(email, str):
        raise ValidationError("Email deve ser uma string")
    email = email.strip().lower()
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_regex, email):
        raise ValidationError("Email inválido")
    if len(email) > 254:
        raise ValidationError("Email muito longo")
    return email


def validate_date(value: str) -> str:
    if not isinstance(value, str):
        raise ValidationError("Data deve ser string no formato YYYY-MM-DD")
    value = value.strip()
    if not value:
        raise ValidationError("Data vazia")
    import datetime as _dt
    try:
        _dt.datetime.strptime(value, "%Y-%m-%d")
        return value
    except ValueError:
        raise ValidationError("Formato de data inválido. Use YYYY-MM-DD")


def validate_integer(value: Any, min_value: int = None, max_value: int = None, allow_none: bool = False) -> Optional[int]:
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


def validate_float(value: Any, min_value: float = None, max_value: float = None, allow_none: bool = False, decimal_places: int = None) -> Optional[float]:
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
        s = str(float_value)
        if '.' in s and len(s.split('.')[-1]) > decimal_places:
            raise ValidationError(f"Máximo de {decimal_places} casas decimais permitido")
    return float_value
