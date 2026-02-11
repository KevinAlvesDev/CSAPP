from ..db import query_db


def listar_tags(tipo: str = "ambos") -> list[dict]:
    sql = """
        SELECT id, nome, icone, cor_badge, ordem, tipo
        FROM tags_sistema
        WHERE ativo = %s
    """
    params = [True]
    if tipo != "ambos":
        sql += " AND (tipo = %s OR tipo = 'ambos')"
        params.append(tipo)
    sql += " ORDER BY ordem ASC"
    rows = query_db(sql, params)
    return [
        {
            "id": r["id"],
            "nome": r["nome"],
            "icone": r["icone"],
            "cor_badge": r["cor_badge"],
            "ordem": r["ordem"],
            "tipo": r["tipo"],
        }
        for r in rows
    ]


def listar_status_implantacao() -> list[dict]:
    sql = """
        SELECT id, codigo, nome, cor, ordem
        FROM status_implantacao
        WHERE ativo = %s
        ORDER BY ordem ASC
    """
    rows = query_db(sql, [True])
    return [
        {
            "id": r["id"],
            "codigo": r["codigo"],
            "nome": r["nome"],
            "cor": r["cor"],
            "ordem": r["ordem"],
        }
        for r in rows
    ]


def listar_niveis_atendimento() -> list[dict]:
    sql = """
        SELECT id, codigo, descricao, ordem
        FROM niveis_atendimento
        WHERE ativo = %s
        ORDER BY ordem ASC
    """
    rows = query_db(sql, [True])
    return [
        {
            "id": r["id"],
            "codigo": r["codigo"],
            "descricao": r["descricao"],
            "ordem": r["ordem"],
        }
        for r in rows
    ]


def listar_tipos_evento() -> list[dict]:
    sql = """
        SELECT id, codigo, nome, icone, cor
        FROM tipos_evento
        WHERE ativo = %s
        ORDER BY id ASC
    """
    rows = query_db(sql, [True])
    return [
        {
            "id": r["id"],
            "codigo": r["codigo"],
            "nome": r["nome"],
            "icone": r["icone"],
            "cor": r["cor"],
        }
        for r in rows
    ]


def listar_motivos_parada() -> list[dict]:
    sql = """
        SELECT id, descricao
        FROM motivos_parada
        WHERE ativo = %s
        ORDER BY id ASC
    """
    rows = query_db(sql, [True])
    return [
        {
            "id": r["id"],
            "descricao": r["descricao"],
        }
        for r in rows
    ]


def listar_motivos_cancelamento() -> list[dict]:
    sql = """
        SELECT id, descricao
        FROM motivos_cancelamento
        WHERE ativo = %s
        ORDER BY id ASC
    """
    rows = query_db(sql, [True])
    return [
        {
            "id": r["id"],
            "descricao": r["descricao"],
        }
        for r in rows
    ]
