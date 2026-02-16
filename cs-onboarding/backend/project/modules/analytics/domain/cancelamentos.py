"""
Módulo de Análise de Cancelamentos
Dados e métricas de cancelamentos.
Princípio SOLID: Single Responsibility
"""

from datetime import date, datetime, timedelta

from flask import current_app

from ....db import query_db
from .utils import date_col_expr, date_param_expr


def get_cancelamentos_data(cs_email=None, start_date=None, end_date=None, context=None):
    """
    Retorna dados detalhados de cancelamentos com métricas e gráficos.
    """
    is_sqlite = current_app.config.get("USE_SQLITE_LOCALLY", False)
    args = []
    query = """
            SELECT i.id, i.nome_empresa, i.usuario_cs, i.data_criacao, i.data_cancelamento,
                   i.motivo_cancelamento, i.seguimento, i.tipos_planos, i.alunos_ativos,
                   i.nivel_receita, i.valor_atribuido, i.contexto
            FROM implantacoes i
            WHERE i.status = 'cancelada'
        """
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
        op, val = _fmt(start_date, False)
        if op:
            query += f" AND {date_col_expr('i.data_cancelamento')} {op} {date_param_expr()}"
            args.append(val)
    if end_date:
        op, val = _fmt(end_date, True)
        if op:
            query += f" AND {date_col_expr('i.data_cancelamento')} {op} {date_param_expr()}"
            args.append(val)

    query += " ORDER BY i.data_cancelamento DESC"
    rows = query_db(query, tuple(args)) or []

    def _to_dt(val):
        if not val:
            return None
        if isinstance(val, datetime):
            return val
        if isinstance(val, date):
            return datetime.combine(val, datetime.min.time())
        if isinstance(val, str):
            for fmt in ["%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"]:
                try:
                    return datetime.strptime(val, fmt)
                except ValueError:
                    pass
        return None

    # Calcular tempo de permanência
    for r in rows:
        dc = _to_dt(r.get("data_cancelamento"))
        cri = _to_dt(r.get("data_criacao"))
        if dc and cri:
            try:
                r["tempo_permanencia_dias"] = max(0, (dc.date() - cri.date()).days)
            except Exception:
                r["tempo_permanencia_dias"] = max(0, (dc - cri).days)
        else:
            r["tempo_permanencia_dias"] = None

    # Categorização de motivos
    motivos = {}
    for r in rows:
        m = (r.get("motivo_cancelamento") or "").strip().lower()
        if not m:
            m = "não informado"
        cat = (
            "preço"
            if ("preço" in m or "valor" in m)
            else (
                "produto"
                if ("funcional" in m or "bug" in m or "suporte" in m)
                else ("processo" if ("processo" in m or "implant" in m) else "outros")
            )
        )
        motivos[cat] = motivos.get(cat, 0) + 1

    total_cancel = sum(motivos.values()) if motivos else 0
    motivo_labels = list(motivos.keys())
    motivo_counts = [motivos[k] for k in motivo_labels]
    motivo_perc = [(c / total_cancel * 100) if total_cancel > 0 else 0 for c in motivo_counts]

    # Série temporal
    series = {}
    for r in rows:
        dc = _to_dt(r.get("data_cancelamento"))
        if not dc:
            continue
        key = dc.strftime("%Y-%m")
        series[key] = series.get(key, 0) + 1

    labels = sorted(series.keys())
    data_ts = [series[k] for k in labels]

    # Média móvel 3 meses
    ma3 = []
    for i in range(len(data_ts)):
        window = data_ts[max(0, i - 2) : i + 1]
        ma3.append(round(sum(window) / len(window), 2))

    # Contagens por segmento, plano, tamanho
    seg_counts = {}
    planos_counts = {}
    tamanho_counts = {"micro": 0, "pequena": 0, "media": 0, "grande": 0}
    for r in rows:
        seg = r.get("seguimento") or "não informado"
        seg_counts[seg] = seg_counts.get(seg, 0) + 1
        plano = r.get("tipos_planos") or "não informado"
        planos_counts[plano] = planos_counts.get(plano, 0) + 1
        alunos = r.get("alunos_ativos") or 0
        if alunos < 100:
            tamanho_counts["micro"] += 1
        elif alunos < 500:
            tamanho_counts["pequena"] += 1
        elif alunos < 2000:
            tamanho_counts["media"] += 1
        else:
            tamanho_counts["grande"] += 1

    # Distribuição de tempo de permanência
    tempos = [r["tempo_permanencia_dias"] for r in rows if r.get("tempo_permanencia_dias") is not None]
    tempos_sorted = sorted(tempos)

    def pct(p):
        if not tempos_sorted:
            return None
        idx = max(0, min(len(tempos_sorted) - 1, round(p * (len(tempos_sorted) - 1))))
        return tempos_sorted[idx]

    dist = {"p50": pct(0.5), "p75": pct(0.75), "p90": pct(0.9)}

    # Valores perdidos
    def parse_val(v):
        if not v:
            return 0.0
        s = str(v).replace("R$", "").replace(".", "").replace(",", ".")
        try:
            return float(s)
        except:
            return 0.0

    valores = [parse_val(r.get("valor_atribuido")) for r in rows]
    valor_medio = round(sum(valores) / len(valores), 2) if valores else 0.0
    perda_anual = round(sum(valores) * 12 / max(1, len(labels)), 2) if labels else 0.0

    # Nível de receita
    nivel_counts = {}
    for r in rows:
        nv = r.get("nivel_receita") or "não informado"
        nivel_counts[nv] = nivel_counts.get(nv, 0) + 1

    # Buckets de valor
    valor_buckets = {"<300": 0, "300-500": 0, "500-800": 0, "800-1200": 0, ">1200": 0}
    for v in valores:
        if v < 300:
            valor_buckets["<300"] += 1
        elif v < 500:
            valor_buckets["300-500"] += 1
        elif v < 800:
            valor_buckets["500-800"] += 1
        elif v < 1200:
            valor_buckets["800-1200"] += 1
        else:
            valor_buckets[">1200"] += 1

    # Bins de tempo
    tempo_bins = {"0-30d": 0, "31-90d": 0, "91-180d": 0, "181-365d": 0, ">365d": 0}
    for d in tempos:
        if d <= 30:
            tempo_bins["0-30d"] += 1
        elif d <= 90:
            tempo_bins["31-90d"] += 1
        elif d <= 180:
            tempo_bins["91-180d"] += 1
        elif d <= 365:
            tempo_bins["181-365d"] += 1
        else:
            tempo_bins[">365d"] += 1

    chart_data = {
        "motivos": {"labels": motivo_labels, "data": motivo_counts, "perc": motivo_perc},
        "segmento": {"labels": list(seg_counts.keys()), "data": list(seg_counts.values())},
        "nivel_receita": {"labels": list(nivel_counts.keys()), "data": list(nivel_counts.values())},
        "valor_atribuido_buckets": {"labels": list(valor_buckets.keys()), "data": list(valor_buckets.values())},
        "tempo_dias_hist": {"labels": list(tempo_bins.keys()), "data": list(tempo_bins.values())},
    }

    metrics = {
        "total_cancelamentos": total_cancel,
        "valor_medio_perdido": valor_medio,
        "perda_anual_estimada": perda_anual,
        "distribuicao_tempo": dist,
        "perda_estim_6m": round(sum(valores) * 6, 2),
    }

    return {"dataset": rows, "chart_data": chart_data, "metrics": metrics}
