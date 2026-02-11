"""
Testes unitários para o módulo de validação (common/validation.py).

Testa:
- Validação de senhas
- Sanitização de strings
- Validação de emails
- Validação de datas
- Validação de inteiros e floats
"""

import pytest

from backend.project.common.validation import (
    ValidationError,
    sanitize_string,
    validate_date,
    validate_email,
    validate_float,
    validate_integer,
    validate_password_strength,
)


class TestValidatePasswordStrength:
    """Testes para validação de força de senha."""

    def test_valid_password(self):
        result = validate_password_strength("Str0ng!P@ssw0rd")
        assert result == "Str0ng!P@ssw0rd"

    def test_too_short(self):
        with pytest.raises(ValidationError, match="mínimo"):
            validate_password_strength("Ab1!")

    def test_too_long(self):
        with pytest.raises(ValidationError, match="máximo"):
            validate_password_strength("A" * 129 + "a1!")

    def test_common_password(self):
        with pytest.raises(ValidationError, match="comum"):
            validate_password_strength("password123")

    def test_no_uppercase(self):
        with pytest.raises(ValidationError, match="maiúscula"):
            validate_password_strength("abcdef1!")

    def test_no_lowercase(self):
        with pytest.raises(ValidationError, match="minúscula"):
            validate_password_strength("ABCDEF1!")

    def test_no_digit(self):
        with pytest.raises(ValidationError, match="número"):
            validate_password_strength("Abcdefgh!")

    def test_no_symbol(self):
        with pytest.raises(ValidationError, match="símbolo"):
            validate_password_strength("Abcdefgh1")

    def test_consecutive_chars(self):
        with pytest.raises(ValidationError, match="consecutivos"):
            validate_password_strength("Aaaa1234!")

    def test_sequential_chars(self):
        with pytest.raises(ValidationError, match="sequências"):
            validate_password_strength("Xabcde12!")


class TestSanitizeString:
    """Testes para sanitização de strings."""

    def test_basic_string(self):
        result = sanitize_string("Hello World")
        assert result == "Hello World"

    def test_strip_whitespace(self):
        result = sanitize_string("  Hello  ")
        assert result == "Hello"

    def test_escape_html(self):
        result = sanitize_string("<script>alert('xss')</script>")
        assert "<script>" not in result
        assert "&lt;script&gt;" in result

    def test_max_length(self):
        with pytest.raises(ValidationError, match="máximo"):
            sanitize_string("a" * 20, max_length=10)

    def test_min_length(self):
        with pytest.raises(ValidationError, match="mínimo"):
            sanitize_string("ab", min_length=5)

    def test_removes_control_chars(self):
        result = sanitize_string("Hello\x00World")
        assert "\x00" not in result

    def test_preserves_newlines(self):
        result = sanitize_string("Hello\nWorld")
        assert "\n" in result

    def test_not_string_raises(self):
        with pytest.raises(ValidationError, match="string"):
            sanitize_string(123)


class TestValidateEmail:
    """Testes para validação de email."""

    def test_valid_email(self):
        assert validate_email("user@example.com") == "user@example.com"

    def test_valid_email_uppercase(self):
        assert validate_email("User@Example.COM") == "user@example.com"

    def test_invalid_email_no_at(self):
        with pytest.raises(ValidationError, match="inválido"):
            validate_email("userexample.com")

    def test_invalid_email_no_domain(self):
        with pytest.raises(ValidationError, match="inválido"):
            validate_email("user@")

    def test_email_too_long(self):
        with pytest.raises(ValidationError, match="longo"):
            validate_email("a" * 250 + "@example.com")


class TestValidateDate:
    """Testes para validação de datas."""

    def test_valid_date(self):
        assert validate_date("2025-01-15") == "2025-01-15"

    def test_invalid_format(self):
        with pytest.raises(ValidationError, match="inválido"):
            validate_date("15/01/2025")

    def test_empty_date(self):
        with pytest.raises(ValidationError, match="vazia"):
            validate_date("")

    def test_not_string(self):
        with pytest.raises(ValidationError, match="string"):
            validate_date(20250115)


class TestValidateInteger:
    """Testes para validação de inteiros."""

    def test_valid_integer(self):
        assert validate_integer(42) == 42

    def test_string_integer(self):
        assert validate_integer("42") == 42

    def test_min_value(self):
        with pytest.raises(ValidationError, match="mínimo"):
            validate_integer(5, min_value=10)

    def test_max_value(self):
        with pytest.raises(ValidationError, match="máximo"):
            validate_integer(100, max_value=50)

    def test_none_allowed(self):
        assert validate_integer(None, allow_none=True) is None

    def test_none_not_allowed(self):
        with pytest.raises(ValidationError):
            validate_integer(None)

    def test_invalid_string(self):
        with pytest.raises(ValidationError, match="inteiro"):
            validate_integer("abc")


class TestValidateFloat:
    """Testes para validação de floats."""

    def test_valid_float(self):
        assert validate_float(3.14) == 3.14

    def test_string_float(self):
        assert validate_float("3.14") == 3.14

    def test_min_value(self):
        with pytest.raises(ValidationError, match="mínimo"):
            validate_float(0.5, min_value=1.0)

    def test_max_value(self):
        with pytest.raises(ValidationError, match="máximo"):
            validate_float(100.5, max_value=50.0)

    def test_none_allowed(self):
        assert validate_float(None, allow_none=True) is None
