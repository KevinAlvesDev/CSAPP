"""
Date Helpers - Funções reutilizáveis para cálculos de data
Elimina duplicação de lógica de datas em todo o projeto
"""

from datetime import date, datetime, timedelta


def calculate_days_between(
    start_date: datetime | date | str | None, end_date: datetime | date | str | None = None
) -> int:
    """
    Calcula dias entre duas datas.

    Args:
        start_date: Data inicial
        end_date: Data final (default: hoje)

    Returns:
        Número de dias (sempre positivo)
    """
    if not start_date:
        return 0

    # Converter para date se necessário
    if isinstance(start_date, str):
        try:
            start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        except:
            return 0
    elif isinstance(start_date, datetime):
        start_date = start_date.date()

    # Data final
    if end_date is None:
        end_date = date.today()
    elif isinstance(end_date, str):
        try:
            end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
        except:
            end_date = date.today()
    elif isinstance(end_date, datetime):
        end_date = end_date.date()

    # Calcular diferença
    delta = end_date - start_date
    return abs(delta.days)


def format_relative_time_simple(dt: datetime | date | str | None) -> tuple[str, int, str]:
    """
    Formata tempo relativo de forma simples.

    Args:
        dt: Data/hora para formatar

    Returns:
        (texto, dias, status_cor)
        Exemplo: ("Há 3 dias", 3, "yellow")
    """
    if not dt:
        return ("Sem registro", 0, "gray")

    # Converter para datetime
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt.replace("Z", "+00:00"))
        except:
            return ("Formato inválido", 0, "gray")
    elif isinstance(dt, date) and not isinstance(dt, datetime):
        dt = datetime.combine(dt, datetime.min.time())

    # Calcular diferença
    now = datetime.now(dt.tzinfo) if dt.tzinfo else datetime.now()
    delta = now - dt
    dias = delta.days

    # Formatar texto
    if dias == 0:
        if delta.seconds < 3600:  # Menos de 1 hora
            minutos = delta.seconds // 60
            texto = f"Há {minutos} min" if minutos > 0 else "Agora"
        else:
            horas = delta.seconds // 3600
            texto = f"Há {horas}h"
        status = "green"
    elif dias == 1:
        texto = "Ontem"
        status = "green"
    elif dias <= 3:
        texto = f"Há {dias} dias"
        status = "yellow"
    elif dias <= 7:
        texto = f"Há {dias} dias"
        status = "orange"
    else:
        texto = f"Há {dias} dias"
        status = "red"

    return (texto, dias, status)


def is_date_in_past(dt: datetime | date | str | None) -> bool:
    """
    Verifica se data está no passado.

    Args:
        dt: Data para verificar

    Returns:
        True se está no passado
    """
    if not dt:
        return False

    # Converter para date
    if isinstance(dt, str):
        try:
            dt = datetime.strptime(dt, "%Y-%m-%d").date()
        except:
            return False
    elif isinstance(dt, datetime):
        dt = dt.date()

    return dt < date.today()


def add_business_days(start_date: date, days: int) -> date:
    """
    Adiciona dias úteis a uma data (ignora fins de semana).

    Args:
        start_date: Data inicial
        days: Número de dias úteis para adicionar

    Returns:
        Data resultante
    """
    current = start_date
    added = 0

    while added < days:
        current += timedelta(days=1)
        # 0 = Segunda, 6 = Domingo
        if current.weekday() < 5:  # Segunda a Sexta
            added += 1

    return current


def get_quarter(dt: datetime | date | None = None) -> int:
    """
    Retorna o trimestre de uma data.

    Args:
        dt: Data (default: hoje)

    Returns:
        Trimestre (1-4)
    """
    if dt is None:
        dt = date.today()
    elif isinstance(dt, datetime):
        dt = dt.date()

    return (dt.month - 1) // 3 + 1


def get_month_name_pt(month: int) -> str:
    """
    Retorna nome do mês em português.

    Args:
        month: Número do mês (1-12)

    Returns:
        Nome do mês
    """
    meses = [
        "Janeiro",
        "Fevereiro",
        "Março",
        "Abril",
        "Maio",
        "Junho",
        "Julho",
        "Agosto",
        "Setembro",
        "Outubro",
        "Novembro",
        "Dezembro",
    ]

    if 1 <= month <= 12:
        return meses[month - 1]
    return "Inválido"
