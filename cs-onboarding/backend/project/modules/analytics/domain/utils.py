"""
Módulo de Utilitários para Analytics
Funções auxiliares de formatação de datas e cálculos de tempo.
Princípio SOLID: Single Responsibility
"""

from datetime import date, datetime, timedelta

from flask import current_app

from ....db import query_db


def calculate_time_in_status(impl_id, status_target="parada"):
    """
    Calcula o tempo (em dias) que uma implantação permaneceu em um status específico.
    Usado para calcular a duração da parada atual.
    """
    impl = query_db(
        "SELECT data_criacao, data_finalizacao, status FROM implantacoes WHERE id = %s", (impl_id,), one=True
    )

    if not impl or not impl.get("status"):
        return None

    if impl["status"] == status_target and status_target == "parada" and impl.get("data_finalizacao"):
        data_inicio_parada_obj = impl["data_finalizacao"]

        data_inicio_parada_datetime = None
        if isinstance(data_inicio_parada_obj, str):
            try:
                data_inicio_parada_datetime = datetime.fromisoformat(data_inicio_parada_obj.replace("Z", "+00:00"))
            except ValueError:
                try:
                    if "." in data_inicio_parada_obj:
                        data_inicio_parada_datetime = datetime.strptime(data_inicio_parada_obj, "%Y-%m-%d %H:%M:%S.%f")
                    else:
                        data_inicio_parada_datetime = datetime.strptime(data_inicio_parada_obj, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    return None
        elif isinstance(data_inicio_parada_obj, date) and not isinstance(data_inicio_parada_obj, datetime):
            data_inicio_parada_datetime = datetime.combine(data_inicio_parada_obj, datetime.min.time())
        elif isinstance(data_inicio_parada_obj, datetime):
            data_inicio_parada_datetime = data_inicio_parada_obj

        if data_inicio_parada_datetime:
            agora = datetime.now()
            agora_naive = agora.replace(tzinfo=None) if agora.tzinfo else agora
            parada_naive = (
                data_inicio_parada_datetime.replace(tzinfo=None)
                if data_inicio_parada_datetime.tzinfo
                else data_inicio_parada_datetime
            )
            try:
                delta = agora_naive - parada_naive
                return max(0, int(delta.days))
            except TypeError:
                return None

    return None


def _format_date_for_query(val, is_end_date=False, is_sqlite=False):
    """
    Formata um valor de data para uso em queries SQL.
    """
    if not val:
        return None, None

    if isinstance(val, datetime):
        date_obj = val.date()
        date_str = date_obj.strftime("%Y-%m-%d")
    elif isinstance(val, date):
        date_obj = val
        date_str = val.strftime("%Y-%m-%d")
    else:
        date_str = str(val)
        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            return None, None

    if is_end_date and not is_sqlite:
        return "<", (date_obj + timedelta(days=1)).strftime("%Y-%m-%d")
    return "<=" if is_end_date else ">=", date_str


def date_col_expr(col: str) -> str:
    """Retorna expressão SQL para extrair a porção de data da coluna conforme o banco."""
    is_sqlite = current_app.config.get("USE_SQLITE_LOCALLY", False)
    return f"date({col})" if is_sqlite else f"CAST({col} AS DATE)"


def date_param_expr() -> str:
    """Retorna expressão SQL para parâmetro de data conforme o banco."""
    is_sqlite = current_app.config.get("USE_SQLITE_LOCALLY", False)
    return "date(%s)" if is_sqlite else "CAST(%s AS DATE)"


def _to_datetime(val):
    """
    Converte um valor para datetime (usado internamente).
    """
    if not val:
        return None
    if isinstance(val, datetime):
        return val
    if isinstance(val, date) and not isinstance(val, datetime):
        return datetime.combine(val, datetime.min.time())
    if isinstance(val, str):
        try:
            return datetime.fromisoformat(val.replace("Z", "+00:00"))
        except ValueError:
            try:
                return (
                    datetime.strptime(val, "%Y-%m-%d %H:%M:%S.%f")
                    if "." in val
                    else datetime.strptime(val, "%Y-%m-%d %H:%M:%S")
                )
            except ValueError:
                try:
                    return datetime.strptime(val, "%Y-%m-%d")
                except ValueError:
                    return None
    return None
