"""
Testes unitários para o secrets_validator.

Testa:
- Validação de secrets obrigatórios
- Detecção de valores inseguros
- Comportamento em produção vs desenvolvimento
- Secrets condicionais (features ativas)
"""

import os
from unittest.mock import patch

import pytest

from backend.project.config.secrets_validator import (
    SecretsValidationError,
    _check_insecure_values,
    _check_required_secrets,
    _is_production,
    validate_secrets,
)


class TestIsProduction:
    """Testa a detecção de ambiente de produção."""

    @patch.dict(os.environ, {"USE_SQLITE_LOCALLY": "true"}, clear=False)
    def test_sqlite_is_not_production(self):
        assert _is_production() is False

    @patch.dict(os.environ, {"DEBUG": "true"}, clear=False)
    def test_debug_is_not_production(self):
        assert _is_production() is False

    @patch.dict(
        os.environ,
        {"USE_SQLITE_LOCALLY": "false", "DEBUG": "false", "FLASK_ENV": "production"},
        clear=False,
    )
    def test_production_detected(self):
        assert _is_production() is True


class TestCheckRequiredSecrets:
    """Testa a verificação de secrets obrigatórios."""

    @patch.dict(os.environ, {"SECRET_KEY": "test-key"}, clear=False)
    def test_no_missing_when_present(self):
        result = _check_required_secrets(["SECRET_KEY"])
        assert result == []

    @patch.dict(os.environ, {}, clear=True)
    def test_missing_when_absent(self):
        result = _check_required_secrets(["SECRET_KEY", "DATABASE_URL"])
        assert "SECRET_KEY" in result
        assert "DATABASE_URL" in result


class TestCheckInsecureValues:
    """Testa a detecção de valores inseguros."""

    @patch.dict(
        os.environ,
        {"SECRET_KEY": "your-secret-key-here-change-this"},
        clear=False,
    )
    def test_detects_default_secret_key(self):
        warnings = _check_insecure_values()
        assert len(warnings) > 0
        assert "SECRET_KEY" in warnings[0]

    @patch.dict(
        os.environ,
        {"SECRET_KEY": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6"},
        clear=False,
    )
    def test_accepts_secure_key(self):
        warnings = _check_insecure_values()
        assert len(warnings) == 0


class TestValidateSecrets:
    """Testa a validação completa de secrets."""

    @patch.dict(
        os.environ,
        {
            "SECRET_KEY": "a-secure-key-that-is-not-default",
            "USE_SQLITE_LOCALLY": "true",
            "FLASK_ENV": "development",
            "DEBUG": "true",
        },
        clear=False,
    )
    def test_valid_in_development(self):
        result = validate_secrets()
        assert result["valid"] is True
        assert result["environment"] == "development"

    @patch.dict(
        os.environ,
        {
            "USE_SQLITE_LOCALLY": "false",
            "DEBUG": "false",
            "FLASK_ENV": "production",
        },
        clear=False,
    )
    def test_raises_in_production_without_database_url(self):
        # Remove DATABASE_URL se existir
        env = os.environ.copy()
        env.pop("DATABASE_URL", None)
        with patch.dict(os.environ, env, clear=True), pytest.raises(SecretsValidationError):
            validate_secrets()
