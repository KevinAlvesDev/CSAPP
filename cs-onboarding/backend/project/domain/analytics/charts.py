"""
Módulo de Gráficos de Analytics
Gráficos de implantações por dia e funil de status.
Princípio SOLID: Single Responsibility
"""

from datetime import date, datetime, timedelta

from flask import current_app

from ...db import query_db
from .utils import date_col_expr, date_param_expr


def get_implants_by_day(start_date=None, end_date=None, cs_email=None, context=None):
    """Contagem de implantações finalizadas por dia, com filtros opcionais."""
    is_sqlite = current_app.config.get("USE_SQLITE_LOCALLY", False)

    query = f"""
        SELECT {date_col_expr("i.data_finalizacao")} AS dia, COUNT(*) AS total
        FROM implantacoes i
        WHERE i.status = 'finalizada'
    """
    args = []

    if context:
        if context == "onboarding":
            query += " AND (i.contexto IS NULL OR i.contexto = 'onboarding') "
        else:
            query += " AND i.contexto = %s "
            args.append(context)

    if cs_email:
        query += " AND i.usuario_cs = %s"
        args.append(cs_email)

    def _fmt(val, is_end=False):
        if not val:
            return None, None
        if isinstance(val, datetime):
            dt = val.date()
            ds = dt.strftime("%Y-%m-%d")
        elif isinstance(val, date):
            dt = val
            ds = val.strftime("%Y-%m-%d")
        else:
            ds = str(val)
            try:
                dt = datetime.strptime(ds, "%Y-%m-%d").date()
            except ValueError:
                return None, None
        if is_end and not is_sqlite:
            return "<", (dt + timedelta(days=1)).strftime("%Y-%m-%d")
        return "<=" if is_end else ">=", ds

    if start_date:
        op, val = _fmt(start_date, is_end=False)
        if op:
            query += f" AND {date_col_expr('i.data_finalizacao')} {op} {date_param_expr()}"
            args.append(val)

    if end_date:
        op, val = _fmt(end_date, is_end=True)
        if op:
            query += f" AND {date_col_expr('i.data_finalizacao')} {op} {date_param_expr()}"
            args.append(val)

    query += f" GROUP BY {date_col_expr('i.data_finalizacao')} ORDER BY {date_col_expr('i.data_finalizacao')}"
    rows = query_db(query, tuple(args)) or []
    labels = [r.get("dia") for r in rows]
    data = [r.get("total", 0) for r in rows]
    return {"labels": labels, "data": data}


def get_funnel_counts(start_date=None, end_date=None, cs_email=None, context=None):
    """Contagem de implantações por status, com período opcional (data_criacao)."""
    is_sqlite = current_app.config.get("USE_SQLITE_LOCALLY", False)

    query = """
        SELECT i.status, COUNT(*) AS total
        FROM implantacoes i
        WHERE 1=1
    """
    args = []

    if context:
        if context == "onboarding":
            query += " AND (i.contexto IS NULL OR i.contexto = 'onboarding') "
        else:
            query += " AND i.contexto = %s "
            args.append(context)

    if cs_email:
        query += " AND i.usuario_cs = %s"
        args.append(cs_email)

    def _fmt(val, is_end=False):
        if not val:
            return None, None
        if isinstance(val, datetime):
            dt = val.date()
            ds = dt.strftime("%Y-%m-%d")
        elif isinstance(val, date):
            dt = val
            ds = val.strftime("%Y-%m-%d")
        else:
            ds = str(val)
            try:
                dt = datetime.strptime(ds, "%Y-%m-%d").date()
            except ValueError:
                return None, None
        if is_end and not is_sqlite:
            return "<", (dt + timedelta(days=1)).strftime("%Y-%m-%d")
        return "<=" if is_end else ">=", ds

    if start_date:
        op, val = _fmt(start_date, is_end=False)
        if op:
            query += f" AND {date_col_expr('i.data_criacao')} {op} {date_param_expr()}"
            args.append(val)

    if end_date:
        op, val = _fmt(end_date, is_end=True)
        if op:
            query += f" AND {date_col_expr('i.data_criacao')} {op} {date_param_expr()}"
            args.append(val)

    query += " GROUP BY i.status"
    rows = query_db(query, tuple(args)) or []
    mapping = {r.get("status"): r.get("total", 0) for r in rows}
    ordered_labels = ["nova", "futura", "andamento", "parada", "finalizada", "cancelada"]
    labels_pt = ["Novas", "Futuras", "Em Andamento", "Paradas", "Finalizadas", "Canceladas"]
    data = [mapping.get(k, 0) for k in ordered_labels]
    return {"labels": labels_pt, "data": data}
