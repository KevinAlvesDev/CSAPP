"""
Módulo de Métricas de Gamificação
Buscar e salvar métricas mensais de gamificação.
Princípio SOLID: Single Responsibility
"""

from datetime import date, datetime

from ....db import execute_db, query_db


def _parse_date_safe(date_str):
    """Auxiliar para parsear datas de strings sujas/variadas."""
    if not date_str:
        return None
    try:
        return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except ValueError:
        try:
            if "." in date_str:
                return datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S.%f")
            else:
                return datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return None


def _get_gamification_automatic_data_bulk(
    mes, ano, primeiro_dia_str, fim_ultimo_dia_str, target_cs_email=None, context=None
):
    """Busca todos os dados automáticos de todos os usuários de uma vez.

    Args:
        mes: Mês de referência
        ano: Ano de referência
        primeiro_dia_str: Data inicial no formato ISO
        fim_ultimo_dia_str: Data final no formato ISO
        target_cs_email: Email específico de um CS (opcional)
        context: Contexto para filtrar (onboarding, ongoing, grandes_contas) (opcional)
    """

    # Construir filtro de contexto
    context_filter = ""
    if context:
        if context == "onboarding":
            context_filter = " AND (contexto IS NULL OR contexto = 'onboarding')"
        else:
            context_filter = " AND contexto = %s"

    sql_finalizadas = f"""
        SELECT usuario_cs, data_criacao, data_finalizacao FROM implantacoes
        WHERE status = 'finalizada'
        AND data_finalizacao >= %s AND data_finalizacao <= %s
        {context_filter}
    """
    args_finalizadas = [primeiro_dia_str, fim_ultimo_dia_str]
    if context and context != "onboarding":
        args_finalizadas.append(context)
    if target_cs_email:
        sql_finalizadas += " AND usuario_cs = %s"
        args_finalizadas.append(target_cs_email)

    impl_finalizadas_raw = query_db(sql_finalizadas, tuple(args_finalizadas))
    impl_finalizadas_raw = impl_finalizadas_raw if impl_finalizadas_raw is not None else []

    tma_data_map = {}
    for impl in impl_finalizadas_raw:
        if not isinstance(impl, dict):
            continue
        email = impl.get("usuario_cs")
        dt_criacao = impl.get("data_criacao")
        dt_finalizacao = impl.get("data_finalizacao")
        if not email or not dt_criacao or not dt_finalizacao:
            continue

        if email not in tma_data_map:
            tma_data_map[email] = {"total_dias": 0, "count": 0}

        dt_criacao_datetime = None
        dt_finalizacao_datetime = None
        if isinstance(dt_criacao, str):
            dt_criacao_datetime = _parse_date_safe(dt_criacao)
        elif isinstance(dt_criacao, date) and not isinstance(dt_criacao, datetime):
            dt_criacao_datetime = datetime.combine(dt_criacao, datetime.min.time())
        elif isinstance(dt_criacao, datetime):
            dt_criacao_datetime = dt_criacao

        if isinstance(dt_finalizacao, str):
            dt_finalizacao_datetime = _parse_date_safe(dt_finalizacao)
        elif isinstance(dt_finalizacao, date) and not isinstance(dt_finalizacao, datetime):
            dt_finalizacao_datetime = datetime.combine(dt_finalizacao, datetime.min.time())
        elif isinstance(dt_finalizacao, datetime):
            dt_finalizacao_datetime = dt_finalizacao

        if dt_criacao_datetime and dt_finalizacao_datetime:
            criacao_naive = (
                dt_criacao_datetime.replace(tzinfo=None) if dt_criacao_datetime.tzinfo else dt_criacao_datetime
            )
            final_naive = (
                dt_finalizacao_datetime.replace(tzinfo=None)
                if dt_finalizacao_datetime.tzinfo
                else dt_finalizacao_datetime
            )
            try:
                delta = final_naive - criacao_naive
                tma_data_map[email]["total_dias"] += max(0, delta.days)
                tma_data_map[email]["count"] += 1
            except TypeError:
                pass

    sql_iniciadas = f"SELECT usuario_cs, COUNT(*) as total FROM implantacoes WHERE data_inicio_efetivo >= %s AND data_inicio_efetivo <= %s {context_filter}"
    args_iniciadas = [primeiro_dia_str, fim_ultimo_dia_str]
    if context and context != "onboarding":
        args_iniciadas.append(context)
    if target_cs_email:
        sql_iniciadas += " AND usuario_cs = %s"
        args_iniciadas.append(target_cs_email)
    sql_iniciadas += " GROUP BY usuario_cs"

    impl_iniciadas_raw = query_db(sql_iniciadas, tuple(args_iniciadas))
    impl_iniciadas_raw = impl_iniciadas_raw if impl_iniciadas_raw is not None else []
    iniciadas_map = {row["usuario_cs"]: row["total"] for row in impl_iniciadas_raw if isinstance(row, dict)}

    # Construir filtro de contexto para checklist_items (via implantacoes)
    context_filter_items = ""
    if context:
        if context == "onboarding":
            context_filter_items = " AND (i.contexto IS NULL OR i.contexto = 'onboarding')"
        else:
            context_filter_items = " AND i.contexto = %s"

    sql_tarefas = f"""
        SELECT i.usuario_cs, COALESCE(ci.tag, 'Ação interna') as tag, COUNT(DISTINCT ci.id) as total
        FROM checklist_items ci
        JOIN implantacoes i ON ci.implantacao_id = i.id
        WHERE ci.tipo_item = 'subtarefa'
        AND ci.completed = TRUE
        AND ci.tag IN ('Ação interna', 'Reunião')
        AND ci.data_conclusao >= %s AND ci.data_conclusao <= %s
        {context_filter_items}
    """
    args_tarefas = [primeiro_dia_str, fim_ultimo_dia_str]
    if context and context != "onboarding":
        args_tarefas.append(context)
    if target_cs_email:
        sql_tarefas += " AND i.usuario_cs = %s"
        args_tarefas.append(target_cs_email)
    sql_tarefas += " GROUP BY i.usuario_cs, ci.tag"

    tarefas_concluidas_raw = query_db(sql_tarefas, tuple(args_tarefas))
    tarefas_concluidas_raw = tarefas_concluidas_raw if tarefas_concluidas_raw is not None else []

    tarefas_map = {}
    for row in tarefas_concluidas_raw:
        if not isinstance(row, dict):
            continue
        email = row.get("usuario_cs")
        tag = row.get("tag")
        total = row.get("total", 0)
        if not email or not tag:
            continue

        if email not in tarefas_map:
            tarefas_map[email] = {"Ação interna": 0, "Reunião": 0}

        if tag == "Ação interna":
            tarefas_map[email]["Ação interna"] = total
        elif tag == "Reunião":
            tarefas_map[email]["Reunião"] = total

    return tma_data_map, iniciadas_map, tarefas_map


def obter_metricas_mensais(usuario_cs, mes, ano):
    """Busca as métricas mensais de um usuário específico."""
    return query_db(
        "SELECT * FROM gamificacao_metricas_mensais WHERE usuario_cs = %s AND mes = %s AND ano = %s",
        (usuario_cs, mes, ano),
        one=True,
    )


def salvar_metricas_mensais(data_to_save, existing_record_id=None):
    """
    Salva ou atualiza métricas mensais de gamificação.

    Args:
        data_to_save: Dicionário com os dados a salvar
        existing_record_id: ID do registro existente (None para inserir novo)

    Returns:
        bool: True se sucesso
    """
    if existing_record_id:
        # Atualizar registro existente
        # Removendo chaves que não devem ser atualizadas/duplicadas no SET
        keys_to_exclude = {"usuario_cs", "mes", "ano"}
        update_data = {k: v for k, v in data_to_save.items() if k not in keys_to_exclude}

        if not update_data:
            return True  # Nada para atualizar

        set_clauses = [f"{key} = %s" for key in update_data]
        sql_update = f"""
            UPDATE gamificacao_metricas_mensais
            SET {", ".join(set_clauses)}
            WHERE id = %s
        """
        # Garante que os valores correspondem à ordem das chaves em set_clauses + ID no final
        args = [*list(update_data.values()), existing_record_id]
        execute_db(sql_update, tuple(args))
    else:
        # Inserir novo registro
        columns = list(data_to_save.keys())
        values_placeholders = ["%s"] * len(columns)
        sql_insert = (
            f"INSERT INTO gamificacao_metricas_mensais ({', '.join(columns)}) VALUES ({', '.join(values_placeholders)})"
        )
        # Garante a ordem dos valores alinhada com as colunas
        args = [data_to_save[col] for col in columns]
        execute_db(sql_insert, tuple(args))

    return True
