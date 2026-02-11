"""
Sanitização de Logs — Remove dados sensíveis de logs.

Implementa um logging.Filter que mascara automaticamente:
- Emails (parcial)
- Tokens e API keys
- Senhas em URLs de banco de dados
- Secrets conhecidos do .env

Uso:
    from backend.project.config.log_sanitizer import SensitiveDataFilter
    handler.addFilter(SensitiveDataFilter())
"""

import logging
import os
import re


class SensitiveDataFilter(logging.Filter):
    """
    Filtro de logging que mascara dados sensíveis em mensagens de log.

    Padrões mascarados:
    - postgresql://user:PASSWORD@host → postgresql://user:***@host
    - Emails: user@domain.com → u***@domain.com
    - Tokens JWT: eyJ... → eyJ***[REDACTED]
    - API keys: sk-xxxx... → sk-***[REDACTED]
    - Variáveis de ambiente sensíveis conhecidas
    """

    # Nomes de variáveis de ambiente que contêm dados sensíveis
    SENSITIVE_ENV_VARS = [
        "SECRET_KEY",
        "FLASK_SECRET_KEY",
        "DATABASE_URL",
        "EXTERNAL_DB_URL",
        "DB_EXT_URL",
        "AUTH0_CLIENT_SECRET",
        "GOOGLE_CLIENT_SECRET",
        "CLOUDFLARE_SECRET_ACCESS_KEY",
        "CLOUDFLARE_ACCESS_KEY_ID",
        "SMTP_PASSWORD",
        "SENDGRID_API_KEY",
        "SENTRY_DSN",
    ]

    def __init__(self, name: str = "", mask_emails: bool = True):
        super().__init__(name)
        self.mask_emails = mask_emails
        self._patterns = self._compile_patterns()
        self._env_values = self._load_sensitive_values()

    def _compile_patterns(self) -> list[tuple[re.Pattern, str]]:
        """Compila padrões regex para mascaramento."""
        return [
            # Database URIs com credenciais: postgresql://user:pass@host
            (
                re.compile(
                    r"((?:postgresql|postgres|mysql|sqlite|redis|mongodb)"
                    r"(?:\+\w+)?://[^:]+:)"
                    r"([^@]+)"
                    r"(@)",
                    re.IGNORECASE,
                ),
                r"\1***\3",
            ),
            # JWT tokens: eyJ... (pelo menos 20 chars)
            (
                re.compile(r"(eyJ[A-Za-z0-9_-]{17,})\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+"),
                r"eyJ***[JWT_REDACTED]",
            ),
            # Bearer tokens
            (
                re.compile(r"(Bearer\s+)[A-Za-z0-9_\-\.]+", re.IGNORECASE),
                r"\1***[TOKEN_REDACTED]",
            ),
            # API Keys genéricos (sk-, pk-, key-, api_)
            (
                re.compile(
                    r"((?:sk|pk|key|api)[_-])"
                    r"([A-Za-z0-9]{8,})",
                    re.IGNORECASE,
                ),
                r"\1***[KEY_REDACTED]",
            ),
            # Senhas em query strings: password=xxx ou senha=xxx
            (
                re.compile(
                    r"((?:password|passwd|pwd|senha|secret|token)"
                    r"\s*[=:]\s*)"
                    r"(\S+)",
                    re.IGNORECASE,
                ),
                r"\1***",
            ),
            # Hashes bcrypt/werkzeug: pbkdf2:sha256:... ou $2b$...
            (
                re.compile(r"(pbkdf2:sha256:\d+\$)[A-Za-z0-9/+$=.]+"),
                r"\1***[HASH_REDACTED]",
            ),
            (
                re.compile(r"(\$2[aby]\$\d+\$)[A-Za-z0-9/+$.]+"),
                r"\1***[HASH_REDACTED]",
            ),
        ]

    def _load_sensitive_values(self) -> list[tuple[str, str]]:
        """Carrega valores sensíveis das variáveis de ambiente."""
        values = []
        for var_name in self.SENSITIVE_ENV_VARS:
            val = os.getenv(var_name)
            if val and len(val) > 6:  # Ignorar valores muito curtos
                # Mascarar mantendo primeiro e último 2 chars
                masked = val[:2] + "***" + val[-2:] + f"[{var_name}]"
                values.append((val, masked))
        return values

    def _mask_email(self, text: str) -> str:
        """Mascara emails parcialmente: user@domain.com → u***@domain.com"""
        if not self.mask_emails:
            return text

        def _replacer(match: re.Match) -> str:
            email = match.group(0)
            local, domain = email.rsplit("@", 1)
            if len(local) <= 1:
                return f"*@{domain}"
            return f"{local[0]}***@{domain}"

        return re.sub(
            r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
            _replacer,
            text,
        )

    def _sanitize(self, message: str) -> str:
        """Aplica todas as regras de sanitização à mensagem."""
        if not isinstance(message, str):
            message = str(message)

        # 1. Substituir valores literais de env vars
        for original_value, masked_value in self._env_values:
            if original_value in message:
                message = message.replace(original_value, masked_value)

        # 2. Aplicar padrões regex
        for pattern, replacement in self._patterns:
            message = pattern.sub(replacement, message)

        # 3. Mascarar emails
        message = self._mask_email(message)

        return message

    def filter(self, record: logging.LogRecord) -> bool:
        """Filtra e sanitiza o registro de log."""
        # Sanitizar mensagem principal
        if record.msg and isinstance(record.msg, str):
            record.msg = self._sanitize(record.msg)

        # Sanitizar args se existirem
        if record.args:
            if isinstance(record.args, dict):
                record.args = {k: self._sanitize(str(v)) if isinstance(v, str) else v for k, v in record.args.items()}
            elif isinstance(record.args, tuple):
                record.args = tuple(self._sanitize(str(a)) if isinstance(a, str) else a for a in record.args)

        # Sanitizar exc_text (stack traces)
        if record.exc_text:
            record.exc_text = self._sanitize(record.exc_text)

        return True


def create_sanitized_handler(
    handler: logging.Handler,
    mask_emails: bool = True,
) -> logging.Handler:
    """
    Wrapper: adiciona o SensitiveDataFilter a um handler existente.

    Args:
        handler: Handler de logging existente
        mask_emails: Se True, mascara emails nas mensagens

    Returns:
        O mesmo handler com o filtro adicionado
    """
    handler.addFilter(SensitiveDataFilter(mask_emails=mask_emails))
    return handler
