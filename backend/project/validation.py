"""
Módulo de validação para sanitização e validação de inputs.
Protege contra SQL Injection, XSS e outros ataques.
"""

import re
import html
from datetime import datetime, date, timezone
from typing import Optional, Union, List, Any


class ValidationError(Exception):
    """Exceção levantada quando uma validação falha."""

    pass


COMMON_PASSWORDS = {
    "123456",
    "123456789",
    "12345678",
    "12345",
    "1234567890",
    "111111",
    "000000",
    "123123",
    "1234567",
    "1234",
    "password",
    "password1",
    "password123",
    "Password1",
    "Password123",
    "qwerty",
    "qwerty123",
    "qwertyuiop",
    "asdfgh",
    "zxcvbn",
    "qwerty1",
    "asdfghjkl",
    "1qaz2wsx",
    "abc123",
    "welcome",
    "monkey",
    "dragon",
    "master",
    "sunshine",
    "princess",
    "letmein",
    "shadow",
    "admin",
    "iloveyou",
    "football",
    "baseball",
    "superman",
    "batman",
    "passw0rd",
    "p@ssw0rd",
    "p@ssword",
    "123qwe",
    "qwe123",
    "admin123",
    "root",
    "toor",
    "test",
    "guest",
    "2024",
    "2023",
    "2022",
    "2021",
    "2020",
}


def validate_password_strength(
    password: str, min_length: int = 8, max_length: int = 128
) -> str:
    """
    Valida critérios de complexidade de senha com requisitos rigorosos.

    Requisitos:
    - Mínimo 8 caracteres (configurável)
    - Máximo 128 caracteres (previne DoS)
    - Pelo menos uma letra maiúscula (A-Z)
    - Pelo menos uma letra minúscula (a-z)
    - Pelo menos um dígito (0-9)
    - Pelo menos um símbolo (!@#$%^&*(),.?":{}|<>)
    - Não pode estar na lista de senhas comuns (Top 50)
    - Não pode ter mais de 3 caracteres repetidos consecutivos
    - Não pode ser sequência simples (123456, abcdef)

    Args:
        password: Senha a ser validada
        min_length: Comprimento mínimo (padrão: 8)
        max_length: Comprimento máximo (padrão: 128)

    Returns:
        Senha validada

    Raises:
        ValidationError: Se a senha não atender aos requisitos

    Exemplo:
        validate_password_strength("Senh@Forte123")  # ✅ Válida
        validate_password_strength("senha123")       # ❌ Sem maiúscula e símbolo
    """
    if not isinstance(password, str):
        raise ValidationError("Senha deve ser uma string")

    if len(password) < min_length:
        raise ValidationError(f"A senha deve ter no mínimo {min_length} caracteres.")

    if len(password) > max_length:
        raise ValidationError(f"A senha deve ter no máximo {max_length} caracteres.")

    if password.lower() in COMMON_PASSWORDS:
        raise ValidationError("Senha muito comum. Escolha uma senha mais segura.")

    if not re.search(r"[A-Z]", password):
        raise ValidationError(
            "A senha deve conter pelo menos uma letra maiúscula (A-Z)."
        )

    if not re.search(r"[a-z]", password):
        raise ValidationError(
            "A senha deve conter pelo menos uma letra minúscula (a-z)."
        )

    if not re.search(r"\d", password):
        raise ValidationError("A senha deve conter pelo menos um número (0-9).")

    if not re.search(r'[!@#$%^&*(),.?":{}|<>\-_+=\[\]\\\/;\'`~]', password):
        raise ValidationError(
            'A senha deve conter pelo menos um símbolo (!@#$%^&*(),.?":{}|<>).'
        )

    if re.search(r"(.)\1{3,}", password):
        raise ValidationError(
            "A senha não pode ter mais de 3 caracteres iguais consecutivos."
        )

    sequences = [
        "0123456789",
        "abcdefghijklmnopqrstuvwxyz",
        "qwertyuiop",
        "asdfghjkl",
        "zxcvbnm",
    ]
    password_lower = password.lower()
    for seq in sequences:
        for i in range(len(seq) - 4):
            if (
                seq[i : i + 5] in password_lower
                or seq[i : i + 5][::-1] in password_lower
            ):
                raise ValidationError(
                    "A senha não pode conter sequências simples (ex: 12345, abcde)."
                )

    return password


def sanitize_string(
    value: str,
    max_length: int = None,
    min_length: int = 0,
    allow_html: bool = False,
    allowed_chars: str = None,
) -> str:
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

    value = value.strip()

    if min_length > 0 and len(value) < min_length:
        raise ValidationError(f"String deve ter no mínimo {min_length} caracteres")

    if max_length and len(value) > max_length:
        raise ValidationError(f"String deve ter no máximo {max_length} caracteres")

    value = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", value)

    if not allow_html:
        value = html.escape(value)
    else:

        allowed_tags = ["<b>", "</b>", "<i>", "</i>", "<u>", "</u>", "<br>", "<br/>"]
        for tag in allowed_tags:
            value = value.replace(tag, tag.lower())
        value = re.sub(r"<[^>]*>", "", value)

    if allowed_chars:
        if not re.match(f"^[a-zA-Z0-9\\s{allowed_chars}]+$", value):
            raise ValidationError(
                f"Caracteres inválidos detectados. Use apenas: {allowed_chars}"
            )

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

    email_regex = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"

    if not re.match(email_regex, email):
        raise ValidationError("Email inválido")

    if len(email) > 254:
        raise ValidationError("Email muito longo")

    return email


def validate_integer(
    value: Any, min_value: int = None, max_value: int = None, allow_none: bool = False
) -> Optional[int]:
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


def validate_float(
    value: Any,
    min_value: float = None,
    max_value: float = None,
    allow_none: bool = False,
    decimal_places: int = None,
) -> Optional[float]:
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

        str_value = str(float_value)
        if "." in str_value:
            decimal_part = str_value.split(".")[1]
            if len(decimal_part) > decimal_places:
                raise ValidationError(
                    f"Valor deve ter no máximo {decimal_places} casas decimais"
                )

    return float_value


def validate_date(
    value: Any, allow_none: bool = False, min_date: date = None, max_date: date = None
) -> Optional[date]:
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

    if isinstance(value, date) and not isinstance(value, datetime):
        date_value = value
    elif isinstance(value, datetime):
        dt = value
        if dt.tzinfo:
            dt = dt.astimezone(timezone.utc)
        date_value = dt.date()
    elif isinstance(value, str):
        v = value.strip()
        try:
            date_value = datetime.strptime(v, "%Y-%m-%d").date()
        except ValueError:
            try:
                if "T" in v or " " in v:
                    v2 = v.replace("Z", "+00:00")
                    dt = datetime.fromisoformat(v2)
                    if dt.tzinfo:
                        dt = dt.astimezone(timezone.utc)
                    date_value = dt.date()
                else:
                    raise ValueError()
            except ValueError:
                m = re.match(r"^(\d{2})\/(\d{2})\/(\d{4})$", v)
                if not m:
                    raise ValidationError(
                        "Data inválida. Formatos aceitos: DD/MM/AAAA, MM/DD/AAAA, AAAA-MM-DD"
                    )
                dd, mm, yyyy = int(m.group(1)), int(m.group(2)), int(m.group(3))
                try:
                    date_value = datetime.strptime(
                        f"{dd:02d}/{mm:02d}/{yyyy}", "%d/%m/%Y"
                    ).date()
                except ValueError:
                    try:
                        date_value = datetime.strptime(
                            f"{mm:02d}/{dd:02d}/{yyyy}", "%m/%d/%Y"
                        ).date()
                    except ValueError:
                        raise ValidationError(
                            "Data inválida. Formatos aceitos: DD/MM/AAAA, MM/DD/AAAA, AAAA-MM-DD"
                        )
    else:
        raise ValidationError(
            "Data inválida. Formatos aceitos: DD/MM/AAAA, MM/DD/AAAA, AAAA-MM-DD"
        )

    if min_date and date_value < min_date:
        raise ValidationError(f"Data deve ser no mínimo {min_date}")

    if max_date and date_value > max_date:
        raise ValidationError(f"Data deve ser no máximo {max_date}")

    return date_value


def validate_choice(
    value: Any, choices: List[Any], allow_none: bool = False
) -> Optional[Any]:
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

    sql_keywords = [
        "select",
        "insert",
        "update",
        "delete",
        "drop",
        "create",
        "alter",
        "exec",
        "execute",
        "script",
        "declare",
        "union",
        "where",
        "or 1=1",
        "--",
        "/*",
        "*/",
        "xp_",
        "sp_",
    ]

    value_lower = value.lower()

    for keyword in sql_keywords:
        if keyword in value_lower:

            if re.search(rf"\b{keyword}\b", value_lower):
                raise ValidationError(f"Caracteres inválidos detectados: {keyword}")

    if re.search(r"(\s{2,}|\n|\r)", value):
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
