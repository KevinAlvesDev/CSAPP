"""
Módulo de Utilitários do Dashboard
Funções auxiliares de formatação de tempo.
Princípio SOLID: Single Responsibility
"""

from datetime import UTC, date, datetime, timezone

_DT_FORMATS = [
    "%Y-%m-%d %H:%M:%S.%f",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d",
]


def _parse_dt_string(dt_str: str) -> datetime | None:
    """Converte string para datetime tentando múltiplos formatos. Retorna None se falhar."""
    dt_str = dt_str.strip()
    for fmt in _DT_FORMATS:
        try:
            return datetime.strptime(dt_str, fmt)
        except ValueError:
            continue
    return None


def _normalize_to_datetime(dt) -> datetime | None:
    """Normaliza qualquer entrada (str, date, datetime) para datetime. Retorna None se inválido."""
    if isinstance(dt, str):
        return _parse_dt_string(dt)
    if isinstance(dt, date) and not isinstance(dt, datetime):
        return datetime.combine(dt, datetime.min.time())
    if isinstance(dt, datetime):
        return dt
    return None


def _format_time_text(days: int, hours: int, minutes: int) -> str:
    """Converte diferença de tempo em texto legível em português."""
    if days == 0:
        if hours == 0:
            return "agora mesmo" if minutes < 5 else f"há {minutes} min"
        return "há 1 hora" if hours == 1 else f"há {hours} horas"
    if days == 1:
        return "há 1 dia"
    if days < 7:
        return f"há {days} dias"
    if days < 30:
        weeks = days // 7
        return f"há {weeks} semana{'s' if weeks > 1 else ''}"
    months = days // 30
    return f"há {months} {'meses' if months > 1 else 'mês'}"


def _status_color(days: int) -> str:
    """Determina a cor do indicador baseada nos dias de diferença."""
    if days == 0:
        return "green"
    if days <= 3:
        return "yellow"
    return "red"


def format_relative_time(dt):
    """
    Formata uma data/hora em tempo relativo (ex: 'há 2 horas', 'há 3 dias')
    Retorna também um indicador de status: 'green', 'yellow', 'red'

    Returns:
        tuple: (text, days, status) ou (None, None, 'gray') em caso de erro
    """
    if dt is None or (isinstance(dt, str) and not dt.strip()):
        return None, None, "gray"

    try:
        dt = _normalize_to_datetime(dt)
        if dt is None:
            return None, None, "gray"

        if dt.tzinfo is not None:
            now = datetime.now(UTC)
        else:
            now = datetime.now(timezone.utc).replace(tzinfo=None)

        if dt > now:
            return "agora mesmo", 0, "green"

        diff = now - dt
        total_seconds = int(diff.total_seconds())
        days = diff.days
        hours = (total_seconds % 86400) // 3600
        minutes = (total_seconds % 3600) // 60

        text = _format_time_text(days, hours, minutes)
        status = _status_color(days)
        return text, days, status

    except Exception as e:
        from flask import current_app
        if current_app:
            current_app.logger.warning(f"Erro em format_relative_time: {e}, input: {dt}", exc_info=True)
        return None, None, "gray"
