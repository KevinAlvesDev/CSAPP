"""
Módulo de Utilitários do Dashboard
Funções auxiliares de formatação de tempo.
Princípio SOLID: Single Responsibility
"""

from datetime import UTC, date, datetime


def format_relative_time(dt):
    """
    Formata uma data/hora em tempo relativo (ex: 'há 2 horas', 'há 3 dias')
    Retorna também um indicador de status: 'green', 'yellow', 'red'

    Returns:
        tuple: (text, days, status) ou (None, None, 'gray') em caso de erro
    """
    # Validação de entrada
    if dt is None or (isinstance(dt, str) and not dt.strip()):
        return None, None, "gray"

    try:
        # Converter string para datetime se necessário
        if isinstance(dt, str):
            dt = dt.strip()
            # Tenta parsear a string com múltiplos formatos
            for fmt in ["%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"]:
                try:
                    dt = datetime.strptime(dt, fmt)
                    break
                except ValueError:
                    continue
            else:
                # Nenhum formato funcionou
                return None, None, "gray"

        # Validar que dt é um datetime válido
        if not isinstance(dt, (datetime, date)):
            return None, None, "gray"

        # Converter date para datetime se necessário
        if isinstance(dt, date) and not isinstance(dt, datetime):
            dt = datetime.combine(dt, datetime.min.time())

        # Usar UTC para comparação se o datetime tiver timezone
        now = datetime.now(UTC) if dt.tzinfo is not None else datetime.now()

        # Validar que a data não é futura
        if dt > now:
            return "agora mesmo", 0, "green"

        diff = now - dt

        # DEBUG: Log para investigar
        from flask import current_app

        if current_app:
            current_app.logger.debug(
                f"format_relative_time: dt={dt}, now={now}, diff={diff}, diff.days={diff.days}, diff.total_seconds={diff.total_seconds()}"
            )

        # Calcular total de horas e minutos (não apenas do dia atual)
        total_seconds = int(diff.total_seconds())
        days = diff.days
        hours = (total_seconds % 86400) // 3600  # 86400 = segundos em um dia
        minutes = (total_seconds % 3600) // 60

        # Formatar texto
        if days == 0:
            if hours == 0:
                text = "agora mesmo" if minutes < 5 else f"há {minutes} min"
            elif hours == 1:
                text = "há 1 hora"
            else:
                text = f"há {hours} horas"
        elif days == 1:
            text = "há 1 dia"
        elif days < 7:
            text = f"há {days} dias"
        elif days < 30:
            weeks = days // 7
            text = f"há {weeks} semana{'s' if weeks > 1 else ''}"
        else:
            months = days // 30
            text = f"há {months} mês{'es' if months > 1 else ''}"

        # Determinar cor do indicador
        if days == 0:
            status = "green"
        elif days <= 3:
            status = "yellow"
        else:
            status = "red"

        return text, days, status

    except Exception as e:
        # Log do erro para debugging
        from flask import current_app

        if current_app:
            current_app.logger.warning(f"Erro em format_relative_time: {e}, input: {dt}")
        return None, None, "gray"
