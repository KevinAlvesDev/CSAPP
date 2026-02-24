from ....db import query_db


def _build_timeline_filters(
    impl_id: int,
    types_param: str,
    q: str,
    dt_from: str,
    dt_to: str,
) -> tuple[str, list]:
    where = ["tl.implantacao_id = %s"]
    params: list = [impl_id]
    if types_param:
        types = [t.strip() for t in types_param.split(",") if t.strip()]
        if types:
            where.append("tl.tipo_evento = ANY(%s)")
            params.append(types)
    if q:
        where.append("tl.detalhes ILIKE %s")
        params.append(f"%{q}%")
    if dt_from:
        where.append("tl.data_criacao >= %s")
        params.append(dt_from)
    if dt_to:
        where.append("tl.data_criacao <= %s")
        params.append(dt_to)
    return " AND ".join(where), params


def get_timeline_logs(
    impl_id: int,
    page: int,
    per_page: int,
    types_param: str = "",
    q: str = "",
    dt_from: str = "",
    dt_to: str = "",
) -> dict:
    from ....common.utils import format_date_br

    where_clause, params = _build_timeline_filters(
        impl_id=impl_id,
        types_param=types_param,
        q=q,
        dt_from=dt_from,
        dt_to=dt_to,
    )

    if per_page > 200:
        per_page = 200
    if page < 1:
        page = 1

    offset = (page - 1) * per_page

    sql = f"""
        SELECT tl.id, tl.implantacao_id, tl.usuario_cs, tl.tipo_evento, tl.detalhes, tl.data_criacao,
               COALESCE(p.nome, tl.usuario_cs) as usuario_nome
        FROM timeline_log tl
        LEFT JOIN implantacoes i ON tl.implantacao_id = i.id
        LEFT JOIN perfil_usuario p ON tl.usuario_cs = p.usuario
        LEFT JOIN perfil_usuario_contexto puc ON tl.usuario_cs = puc.usuario AND puc.contexto = COALESCE(i.contexto, 'onboarding')
        WHERE {where_clause}
        ORDER BY tl.data_criacao DESC
        LIMIT %s OFFSET %s
    """
    params_with_pagination = [*params, per_page, offset]

    rows = query_db(sql, tuple(params_with_pagination)) or []
    items: list[dict] = []
    for r in rows:
        d = dict(r)
        dt = d.get("data_criacao")
        d["data_criacao"] = format_date_br(dt, include_time=True) if dt else ""
        items.append(d)

    return {
        "logs": items,
        "pagination": {"page": page, "per_page": per_page},
    }


def export_timeline_csv(
    impl_id: int,
    types_param: str = "",
    q: str = "",
    dt_from: str = "",
    dt_to: str = "",
) -> str:
    import csv
    import io

    where_clause, params = _build_timeline_filters(
        impl_id=impl_id,
        types_param=types_param,
        q=q,
        dt_from=dt_from,
        dt_to=dt_to,
    )

    sql = f"""
        SELECT tl.data_criacao, tl.tipo_evento, COALESCE(p.nome, tl.usuario_cs) as usuario_nome, tl.detalhes
        FROM timeline_log tl
        LEFT JOIN implantacoes i ON tl.implantacao_id = i.id
        LEFT JOIN perfil_usuario p ON tl.usuario_cs = p.usuario
        LEFT JOIN perfil_usuario_contexto puc ON tl.usuario_cs = puc.usuario AND puc.contexto = COALESCE(i.contexto, 'onboarding')
        WHERE {where_clause}
        ORDER BY tl.data_criacao DESC
    """
    rows = query_db(sql, tuple(params)) or []

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["data_criacao", "tipo_evento", "usuario", "detalhes"])
    for r in rows:
        dc = r["data_criacao"]
        dc_str = dc.isoformat() if hasattr(dc, "isoformat") else str(dc)
        writer.writerow(
            [
                dc_str,
                r.get("tipo_evento", ""),
                r.get("usuario_nome", ""),
                r.get("detalhes", ""),
            ]
        )

    return output.getvalue()
