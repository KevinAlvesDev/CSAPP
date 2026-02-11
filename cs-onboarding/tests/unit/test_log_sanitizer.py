"""
Testes unitários para o log_sanitizer.

Testa:
- Mascaramento de database URIs
- Mascaramento de emails
- Mascaramento de JWT tokens
- Mascaramento de API keys
- Mascaramento de senhas em query strings
"""

import logging

from backend.project.config.log_sanitizer import SensitiveDataFilter


class TestSensitiveDataFilter:
    """Testes para o filtro de sanitização de logs."""

    def setup_method(self):
        """Setup: cria filtro e logger de teste."""
        self.filter = SensitiveDataFilter()
        self.logger = logging.getLogger("test_sanitizer")
        self.logger.addFilter(self.filter)

    def _make_record(self, msg: str) -> logging.LogRecord:
        """Helper: cria um LogRecord com a mensagem fornecida."""
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg=msg,
            args=None,
            exc_info=None,
        )
        return record

    def test_masks_postgresql_uri(self):
        record = self._make_record("Conectando a postgresql://admin:super_secret_password@db.example.com:5432/mydb")
        self.filter.filter(record)
        assert "super_secret_password" not in record.msg
        assert "***" in record.msg
        assert "postgresql://" in record.msg

    def test_masks_redis_uri(self):
        record = self._make_record("Cache: redis://default:my_redis_pass@redis.host:6379/0")
        self.filter.filter(record)
        assert "my_redis_pass" not in record.msg
        assert "***" in record.msg

    def test_masks_email(self):
        record = self._make_record("Usuário john.doe@example.com fez login")
        self.filter.filter(record)
        assert "john.doe@example.com" not in record.msg
        assert "@example.com" in record.msg
        assert "j***@example.com" in record.msg

    def test_masks_jwt_token(self):
        record = self._make_record("Token: eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.signature")
        self.filter.filter(record)
        assert "eyJzdWIiOiIxMjM0NTY3ODkwIn0" not in record.msg
        assert "JWT_REDACTED" in record.msg

    def test_masks_bearer_token(self):
        record = self._make_record("Authorization: Bearer abc123def456ghi789")
        self.filter.filter(record)
        assert "abc123def456ghi789" not in record.msg
        assert "TOKEN_REDACTED" in record.msg

    def test_masks_password_in_query(self):
        record = self._make_record("Config: password=my_super_secret_pass")
        self.filter.filter(record)
        assert "my_super_secret_pass" not in record.msg
        assert "***" in record.msg

    def test_preserves_non_sensitive_data(self):
        record = self._make_record("Implantação 42 criada com sucesso")
        self.filter.filter(record)
        assert record.msg == "Implantação 42 criada com sucesso"

    def test_masks_api_key(self):
        record = self._make_record("Using API key: sk-1234567890abcdef")
        self.filter.filter(record)
        assert "1234567890abcdef" not in record.msg
        assert "KEY_REDACTED" in record.msg

    def test_email_masking_can_be_disabled(self):
        filter_no_email = SensitiveDataFilter(mask_emails=False)
        record = self._make_record("User john.doe@example.com logged in")
        filter_no_email.filter(record)
        assert "john.doe@example.com" in record.msg

    def test_filters_return_true(self):
        """Filtro deve sempre retornar True (não remove records, apenas sanitiza)."""
        record = self._make_record("Qualquer mensagem")
        result = self.filter.filter(record)
        assert result is True
