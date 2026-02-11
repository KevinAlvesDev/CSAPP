"""
Validação de Secrets em Runtime.

Verifica todas as variáveis de ambiente críticas no startup da aplicação.
Falha fast se secrets obrigatórios estiverem ausentes em produção.

Uso:
    from backend.project.config.secrets_validator import validate_secrets
    validate_secrets(app)
"""

import logging
import os
import re

logger = logging.getLogger("security")

# ──────────────────────────────────────────────
# Secrets obrigatórios em TODOS os ambientes
# ──────────────────────────────────────────────
ALWAYS_REQUIRED = [
    "SECRET_KEY",
]

# ──────────────────────────────────────────────
# Secrets obrigatórios APENAS em produção
# ──────────────────────────────────────────────
PRODUCTION_REQUIRED = [
    "DATABASE_URL",
]

# ──────────────────────────────────────────────
# Secrets condicionais (obrigatórios se feature ativa)
# ──────────────────────────────────────────────
CONDITIONAL_SECRETS = {
    "AUTH0_ENABLED": {
        "condition_values": ("true", "1", "yes"),
        "required_secrets": ["AUTH0_DOMAIN", "AUTH0_CLIENT_ID", "AUTH0_CLIENT_SECRET"],
        "feature_name": "Auth0 Authentication",
    },
    "GOOGLE_OAUTH_ENABLED_FLAG": {
        "condition_check": lambda: all(
            [
                os.getenv("GOOGLE_CLIENT_ID"),
                os.getenv("GOOGLE_CLIENT_SECRET"),
                os.getenv("GOOGLE_REDIRECT_URI"),
            ]
        ),
        "required_secrets": ["GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GOOGLE_REDIRECT_URI"],
        "feature_name": "Google OAuth",
    },
    "EMAIL_DRIVER_SMTP": {
        "condition_check": lambda: os.getenv("EMAIL_DRIVER", "smtp").lower() == "smtp"
        and any([os.getenv("SMTP_HOST"), os.getenv("SMTP_USER")]),
        "required_secrets": ["SMTP_HOST", "SMTP_FROM"],
        "feature_name": "SMTP Email",
    },
    "EMAIL_DRIVER_SENDGRID": {
        "condition_check": lambda: os.getenv("EMAIL_DRIVER", "").lower() == "sendgrid",
        "required_secrets": ["SENDGRID_API_KEY"],
        "feature_name": "SendGrid Email",
    },
    "R2_STORAGE": {
        "condition_check": lambda: any(
            [
                os.getenv("CLOUDFLARE_ENDPOINT_URL"),
                os.getenv("CLOUDFLARE_ACCESS_KEY_ID"),
            ]
        ),
        "required_secrets": [
            "CLOUDFLARE_ENDPOINT_URL",
            "CLOUDFLARE_ACCESS_KEY_ID",
            "CLOUDFLARE_SECRET_ACCESS_KEY",
            "CLOUDFLARE_BUCKET_NAME",
            "CLOUDFLARE_PUBLIC_URL",
        ],
        "feature_name": "Cloudflare R2 Storage",
    },
}

# ──────────────────────────────────────────────
# Valores inseguros conhecidos (padrões de .env.example)
# ──────────────────────────────────────────────
INSECURE_VALUES = {
    "SECRET_KEY": [
        "your-secret-key-here-change-this",
        "changeme",
        "secret",
        "dev-secret",
        "test",
    ],
}

# ──────────────────────────────────────────────
# Padrões de valores que indicam credenciais em plaintext
# ──────────────────────────────────────────────
CREDENTIAL_PATTERNS = [
    re.compile(r"password\s*=\s*.+", re.IGNORECASE),
    re.compile(r"://[^:]+:[^@]+@", re.IGNORECASE),  # URLs com credenciais
]


class SecretsValidationError(Exception):
    """Erro crítico: secrets obrigatórios ausentes ou inseguros."""

    pass


def _is_production() -> bool:
    """Detecta se estamos em ambiente de produção."""
    use_sqlite = os.getenv("USE_SQLITE_LOCALLY", "").lower() in ("true", "1", "yes")
    flask_env = os.getenv("FLASK_ENV", "production")
    flask_debug = os.getenv("DEBUG", "").lower() in ("true", "1", "yes")

    # É produção se: não usa SQLite, não está em debug, e env é production
    return not use_sqlite and not flask_debug and flask_env == "production"


def _check_insecure_values() -> list[str]:
    """Verifica se algum secret usa valor inseguro padrão."""
    warnings = []
    for var_name, insecure_list in INSECURE_VALUES.items():
        value = os.getenv(var_name, "")
        if value.lower().strip() in [v.lower() for v in insecure_list]:
            warnings.append(
                f"⚠️  {var_name} está usando um valor inseguro padrão. "
                f'Gere um novo com: python -c "import secrets; print(secrets.token_hex(32))"'
            )
    return warnings


def _check_required_secrets(required: list[str]) -> list[str]:
    """Retorna lista de secrets ausentes."""
    return [s for s in required if not os.getenv(s)]


def _check_conditional_secrets() -> tuple[list[str], list[str]]:
    """Verifica secrets condicionais baseados em features ativas."""
    errors = []
    warnings = []

    for key, config in CONDITIONAL_SECRETS.items():
        feature_active = False

        if "condition_values" in config:
            env_value = os.getenv(key, "").lower()
            feature_active = env_value in config["condition_values"]
        elif "condition_check" in config:
            try:
                feature_active = config["condition_check"]()
            except Exception:
                feature_active = False

        if feature_active:
            missing = _check_required_secrets(config["required_secrets"])
            if missing:
                feature_name = config["feature_name"]
                msg = f"Feature '{feature_name}' está ativa mas faltam secrets: {', '.join(missing)}"
                if _is_production():
                    errors.append(f"❌ {msg}")
                else:
                    warnings.append(f"⚠️  {msg}")

    return errors, warnings


def validate_secrets(app: object | None = None) -> dict:
    """
    Valida todos os secrets do sistema.

    Em produção: falha se secrets críticos estiverem ausentes.
    Em desenvolvimento: emite warnings mas permite inicializar.

    Args:
        app: Instância Flask (opcional, para logging via app.logger)

    Returns:
        dict com 'errors', 'warnings' e 'valid' (bool)

    Raises:
        SecretsValidationError: Se secrets críticos estiverem ausentes em produção
    """
    is_prod = _is_production()
    errors: list[str] = []
    warnings: list[str] = []

    # 1. Verificar secrets sempre obrigatórios
    missing_always = _check_required_secrets(ALWAYS_REQUIRED)
    if missing_always:
        errors.append(f"❌ Secrets obrigatórios ausentes: {', '.join(missing_always)}")

    # 2. Verificar secrets de produção
    if is_prod:
        missing_prod = _check_required_secrets(PRODUCTION_REQUIRED)
        if missing_prod:
            errors.append(f"❌ Secrets de produção ausentes: {', '.join(missing_prod)}")

    # 3. Verificar valores inseguros
    insecure = _check_insecure_values()
    if is_prod and insecure:
        errors.extend(insecure)
    else:
        warnings.extend(insecure)

    # 4. Verificar secrets condicionais
    cond_errors, cond_warnings = _check_conditional_secrets()
    errors.extend(cond_errors)
    warnings.extend(cond_warnings)

    # 5. Log dos resultados
    _log = app.logger if app and hasattr(app, "logger") else logger

    if warnings:
        for w in warnings:
            _log.warning(w)

    if errors:
        for e in errors:
            _log.error(e)

        if is_prod:
            error_msg = "Validação de secrets falhou em PRODUÇÃO!\n" + "\n".join(errors)
            _log.critical(error_msg)
            raise SecretsValidationError(error_msg)
        else:
            _log.warning("⚠️  Erros de secrets detectados em desenvolvimento. Verifique antes de fazer deploy.")

    if not errors and not warnings:
        _log.info("✅ Validação de secrets concluída: tudo OK")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "environment": "production" if is_prod else "development",
    }
