"""


Analytics Dashboard Otimizado - Versão SEM N+1


Elimina queries individuais nos loops





ANTES: 3 queries principais + (N × 3) queries no loop


DEPOIS: 6 queries totais





Ganho: 10-50x mais rápido


"""





from datetime import date, datetime, timezone
import re





from ....common.context_profiles import resolve_context


from ....constants import (
    FORMAS_PAGAMENTO,
    HORARIOS_FUNCIONAMENTO,
    MODALIDADES_LIST,
    NAO_DEFINIDO_BOOL,
    NIVEIS_RECEITA,
    RECORRENCIA_USADA,
    SEGUIMENTOS_LIST,
    SIM_NAO_OPTIONS,
    SISTEMAS_ANTERIORES,
    TIPOS_PLANOS,
)


from ....db import query_db
from ....modules.time.application.time_calculator import calculate_days_bulk


from .utils import _format_date_for_query, date_col_expr, date_param_expr








def calculate_all_days_batch(impl_ids: list[int]) -> dict[int, dict[str, int]]:


    """


    Calcula dias passados e dias parada para TODAS as implantações de uma vez.





    Returns:


        {impl_id: {'dias_passados': X, 'dias_parada': Y}}


    """


    if not impl_ids:


        return {}





    return calculate_days_bulk(impl_ids)


def _parse_mrr_value(raw):
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return float(raw)
    s = str(raw).strip()
    if not s:
        return None
    s_clean = re.sub(r"[^0-9,\\.]", "", s)
    if not s_clean:
        return None
    if s_clean.count(",") == 1 and s_clean.count(".") >= 1:
        s_clean = s_clean.replace(".", "").replace(",", ".")
    elif s_clean.count(",") == 1 and s_clean.count(".") == 0:
        s_clean = s_clean.replace(",", ".")
    elif s_clean.count(".") > 1:
        s_clean = s_clean.replace(".", "")
    try:
        return float(s_clean)
    except Exception:
        return None


def _normalize_nivel_receita(raw):
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    s_lower = s.lower()

    # Try numeric bucketization first.
    mrr_val = _parse_mrr_value(s)
    if mrr_val is not None:
        if mrr_val < 700:
            return NIVEIS_RECEITA[0]
        if mrr_val < 1000:
            return NIVEIS_RECEITA[1]
        if mrr_val < 2000:
            return NIVEIS_RECEITA[2]
        return NIVEIS_RECEITA[3]

    # Textual matching (full labels or shorthand).
    if s in NIVEIS_RECEITA:
        return s

    if "grande" in s_lower:
        return NIVEIS_RECEITA[4]
    if "prata" in s_lower:
        return NIVEIS_RECEITA[0]
    if "ouro" in s_lower or "gold" in s_lower:
        return NIVEIS_RECEITA[1]
    if "platina" in s_lower or "platinum" in s_lower:
        return NIVEIS_RECEITA[2]
    if "diamante" in s_lower or "diamond" in s_lower:
        return NIVEIS_RECEITA[3]

    return None


def _normalize_label(raw, default_label: str = NAO_DEFINIDO_BOOL) -> str:
    if raw is None:
        return default_label
    s = str(raw).strip()
    return s if s else default_label


def _split_multi_value(raw) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, (list, tuple)):
        values = raw
    else:
        values = str(raw).split(",")
    cleaned = []
    for val in values:
        if val is None:
            continue
        s = str(val).strip()
        if s:
            cleaned.append(s)
    return cleaned


def _normalize_sim_nao(raw) -> str:
    if raw is None:
        return NAO_DEFINIDO_BOOL
    s = str(raw).strip()
    if not s:
        return NAO_DEFINIDO_BOOL
    if s in SIM_NAO_OPTIONS:
        return s
    s_lower = s.lower()
    if s_lower in {"sim", "s", "yes", "y", "true", "1"}:
        return "Sim"
    if s_lower in {"nao", "não", "n", "no", "false", "0"}:
        return "Não"
    if "nao definido" in s_lower or "não definido" in s_lower:
        return NAO_DEFINIDO_BOOL
    return NAO_DEFINIDO_BOOL


def _init_counts(labels: list[str], include_nao_definido: bool = True, extra_label: str | None = None) -> dict[str, int]:
    counts = {label: 0 for label in labels}
    if include_nao_definido and NAO_DEFINIDO_BOOL not in counts:
        counts[NAO_DEFINIDO_BOOL] = 0
    if extra_label and extra_label not in counts:
        counts[extra_label] = 0
    return counts


def _accumulate_multi(counts: dict[str, int], values: list[str], fallback_label: str, unknown_label: str | None = None):
    if not values:
        counts[fallback_label] = counts.get(fallback_label, 0) + 1
        return
    for val in values:
        if val in counts:
            counts[val] = counts.get(val, 0) + 1
        elif unknown_label:
            counts[unknown_label] = counts.get(unknown_label, 0) + 1
        else:
            counts[val] = counts.get(val, 0) + 1


def _chart_from_counts(counts: dict[str, int], order: list[str] | None = None) -> dict:
    if order:
        labels = [label for label in order if label in counts]
        for label in counts:
            if label not in labels:
                labels.append(label)
    else:
        labels = list(counts.keys())
    return {"labels": labels, "data": [counts.get(label, 0) for label in labels]}


def _top_n_chart(counts: dict[str, int], top_n: int, other_label: str = "Outros") -> dict:
    items = sorted(counts.items(), key=lambda item: item[1], reverse=True)
    if len(items) <= top_n:
        return {"labels": [k for k, _ in items], "data": [v for _, v in items]}
    top_items = items[:top_n]
    other_value = sum(val for _, val in items[top_n:])
    labels = [k for k, _ in top_items]
    data = [v for _, v in top_items]
    if other_value > 0:
        labels.append(other_label)
        data.append(other_value)
    return {"labels": labels, "data": data}


def _display_tipo_implantacao(raw_tipo):
    if raw_tipo == "modulo":
        return "Modulo"
    return "Sistema"


def _fallback_dias_parada(impl, dias_info):
    dias_parada = (dias_info or {}).get("dias_parada") or 0
    if dias_parada > 0:
        return dias_parada

    current_status = impl.get("status")
    if current_status != "parada":
        return 0

    referencia = impl.get("data_parada") or impl.get("data_finalizacao") or impl.get("data_criacao")
    if not referencia:
        return 0

    try:
        inicio = referencia
        if isinstance(referencia, str):
            inicio = datetime.fromisoformat(referencia.replace("Z", "+00:00"))
        elif isinstance(referencia, date) and not isinstance(referencia, datetime):
            inicio = datetime.combine(referencia, datetime.min.time())
        if isinstance(inicio, datetime) and inicio.tzinfo:
            inicio = inicio.replace(tzinfo=None)
        agora = datetime.now(timezone.utc).replace(tzinfo=None)
        return max(0, (agora - inicio).days)
    except Exception:
        return 0


def _tempo_parado_lista(impl, dias_info):
    dias_andamento = (dias_info or {}).get("dias_passados") or 0
    dias_parada = _fallback_dias_parada(impl, dias_info)
    total = dias_andamento + dias_parada
    return total if total > 0 else dias_parada


def _resolve_status_date_field(target_status):
    if target_status == "andamento":
        return "i.data_inicio_efetivo"
    if target_status == "futura":
        return "i.data_inicio_efetivo"
    if target_status == "finalizada":
        return "i.data_finalizacao"
    if target_status == "parada":
        return "i.data_parada"
    if target_status == "cancelada":
        return "i.data_cancelamento"
    if target_status == "sem_previsao":
        return None
    return "i.data_criacao"








def get_analytics_data_v2(


    target_cs_email=None,


    target_status=None,


    start_date=None,


    end_date=None,


    target_tag=None,


    task_cs_email=None,


    task_start_date=None,


    task_end_date=None,


    sort_impl_date=None,

    module_cs_email=None,
    module_status_filter=None,
    module_days_min=None,
    module_days_max=None,
    module_days_sort=None,


    context=None,


):


    """


    Versão otimizada que elimina N+1.





    ANTES: 3 + (N × 3) queries


    DEPOIS: 6 queries totais


    """





    ctx = resolve_context(context)


    agora = datetime.now(timezone.utc)


    ano_corrente = agora.year


    dt_finalizacao_datetime: datetime | None = None





    # QUERY 1: Buscar implantações


    query_impl = """


        SELECT i.*,


               p.nome as cs_nome, p.cargo as cs_cargo,


               COALESCE(puc.perfil_acesso, p.cargo) as cs_perfil
        FROM implantacoes i


        LEFT JOIN perfil_usuario p ON i.usuario_cs = p.usuario


        LEFT JOIN perfil_usuario_contexto puc ON i.usuario_cs = puc.usuario AND puc.contexto = %s


        WHERE 1=1


    """


    args_impl = [ctx]





    if context:


        if context == "onboarding":


            query_impl += " AND (i.contexto IS NULL OR i.contexto = 'onboarding') "


        else:


            query_impl += " AND i.contexto = %s "


            args_impl.append(context)





    if target_cs_email:


        query_impl += " AND i.usuario_cs = %s "


        args_impl.append(target_cs_email)





    if target_status and target_status != "todas":


        if target_status in ["nova", "futura", "cancelada"]:


            query_impl += f" AND i.status = '{target_status}' "


        else:


            query_impl += " AND i.status = %s "


            args_impl.append(target_status)





    date_field_to_filter = _resolve_status_date_field(target_status)





    start_op, start_date_val = _format_date_for_query(start_date)


    if start_op and date_field_to_filter:


        query_impl += f" AND {date_col_expr(date_field_to_filter)} {start_op} {date_param_expr()} "


        args_impl.append(start_date_val)





    end_op, end_date_val = _format_date_for_query(end_date, is_end_date=True)


    if end_op and date_field_to_filter:


        query_impl += f" AND {date_col_expr(date_field_to_filter)} {end_op} {date_param_expr()} "


        args_impl.append(end_date_val)





    if sort_impl_date in ["asc", "desc"]:


        order_dir = "ASC" if sort_impl_date == "asc" else "DESC"


        query_impl += f" ORDER BY {date_col_expr('i.data_criacao')} {order_dir}, i.nome_empresa "


    else:


        query_impl += " ORDER BY i.nome_empresa "





    impl_list = query_db(query_impl, tuple(args_impl)) or []


    impl_completas = [impl for impl in impl_list if isinstance(impl, dict) and impl.get("tipo") == "completa"]





    # QUERY 2: Buscar módulos


    query_modules = """


        SELECT i.*, p.nome as cs_nome, p.cargo as cs_cargo,


               COALESCE(puc.perfil_acesso, p.cargo) as cs_perfil
        FROM implantacoes i


        LEFT JOIN perfil_usuario p ON i.usuario_cs = p.usuario


        LEFT JOIN perfil_usuario_contexto puc ON i.usuario_cs = puc.usuario AND puc.contexto = %s


        WHERE i.tipo = 'modulo'


    """


    args_modules = [ctx]

    effective_module_cs = module_cs_email or target_cs_email





    if context:


        if context == "onboarding":


            query_modules += " AND (i.contexto IS NULL OR i.contexto = 'onboarding') "


        else:


            query_modules += " AND i.contexto = %s "


            args_modules.append(context)

    if effective_module_cs:
        query_modules += " AND i.usuario_cs = %s "
        args_modules.append(effective_module_cs)

    if module_status_filter and module_status_filter != "todas":
        query_modules += " AND i.status = %s "
        args_modules.append(module_status_filter)


    modules_rows = query_db(query_modules, tuple(args_modules)) or []

    # OTIMIZACAO: calcular dias de todos os modulos de uma vez
    module_ids = [m["id"] for m in modules_rows if isinstance(m, dict)]
    dias_map = calculate_all_days_batch(module_ids)

    modules_implantacao_lista = []
    modules_paradas_detalhadas = []

    for impl in modules_rows:
        if not isinstance(impl, dict):
            continue

        impl_id_raw = impl.get("id")
        if impl_id_raw is None:
            continue

        impl_id = int(impl_id_raw)
        status = impl.get("status")

        dias_info = dias_map.get(impl_id, {"dias_passados": 0, "dias_parada": 0})
        if status == "parada":
            # Na lista detalhada de módulos, "DIAS" representa o tempo total
            # acumulado da implantação, incluindo o período em parada.
            dias = (dias_info.get("dias_passados") or 0) + (dias_info.get("dias_parada") or 0)
            modules_paradas_detalhadas.append(
                {
                    "id": impl_id,
                    "nome_empresa": impl.get("nome_empresa"),
                    "usuario_cs": impl.get("usuario_cs"),
                    "tipo": _display_tipo_implantacao(impl.get("tipo")),
                    "motivo_parada": impl.get("motivo_parada") or "Motivo NÃ£o Especificado",
                    "dias_parada": _tempo_parado_lista(impl, dias_info),
                    "cs_nome": impl.get("cs_nome", impl.get("usuario_cs")),
                }
            )
        else:
            dias = dias_info["dias_passados"]

        modules_implantacao_lista.append(


            {


                "impl_id": impl_id,


                "id": impl_id,


                "nome_empresa": impl.get("nome_empresa"),


                "cs_nome": impl.get("cs_nome", impl.get("usuario_cs")),


                "status": status,


                "modulo": impl.get("modulo"),


                "dias": dias,


            }


        )
    if module_days_min is not None:
        modules_implantacao_lista = [m for m in modules_implantacao_lista if (m.get("dias") or 0) >= module_days_min]
    if module_days_max is not None:
        modules_implantacao_lista = [m for m in modules_implantacao_lista if (m.get("dias") or 0) <= module_days_max]
    if module_days_sort == "oldest_first":
        modules_implantacao_lista = sorted(modules_implantacao_lista, key=lambda m: (m.get("dias") or 0), reverse=True)
    else:
        modules_implantacao_lista = sorted(modules_implantacao_lista, key=lambda m: (m.get("dias") or 0))



    # QUERY 3: Tarefas


    primeiro_dia_mes = agora.replace(day=1)


    default_task_start_date_str = primeiro_dia_mes.strftime("%Y-%m-%d")


    default_task_end_date_str = agora.strftime("%Y-%m-%d")





    task_start_date_to_query = (


        task_start_date.strftime("%Y-%m-%d") if isinstance(task_start_date, (date, datetime)) else task_start_date


    ) or default_task_start_date_str


    task_end_date_to_query = (


        task_end_date.strftime("%Y-%m-%d") if isinstance(task_end_date, (date, datetime)) else task_end_date


    ) or default_task_end_date_str





    query_tasks = """


        SELECT


            i.usuario_cs,


            COALESCE(p.nome, i.usuario_cs) as cs_nome,


            COALESCE(ci.tag, 'Ação interna') as tag,


            COUNT(DISTINCT ci.id) as total_concluido


        FROM checklist_items ci


        JOIN implantacoes i ON ci.implantacao_id = i.id


        LEFT JOIN perfil_usuario p ON i.usuario_cs = p.usuario


        LEFT JOIN perfil_usuario_contexto puc ON i.usuario_cs = puc.usuario AND puc.contexto = %s


        WHERE


            ci.tipo_item = 'subtarefa'


            AND ci.completed = TRUE


            AND ci.tag IN ('Ação interna', 'Reunião')


            AND ci.data_conclusao IS NOT NULL


    """


    args_tasks = [ctx]





    if context:


        if context == "onboarding":


            query_tasks += " AND (i.contexto IS NULL OR i.contexto = 'onboarding') "


        else:


            query_tasks += " AND i.contexto = %s "


            args_tasks.append(context)





    if task_cs_email:


        query_tasks += " AND i.usuario_cs = %s "


        args_tasks.append(task_cs_email)





    task_start_op, task_start_date_val = _format_date_for_query(task_start_date_to_query)


    if task_start_op:


        query_tasks += f" AND {date_col_expr('ci.data_conclusao')} {task_start_op} {date_param_expr()} "


        args_tasks.append(task_start_date_val)





    task_end_op, task_end_date_val = _format_date_for_query(task_end_date_to_query, is_end_date=True)


    if task_end_op:


        query_tasks += f" AND {date_col_expr('ci.data_conclusao')} {task_end_op} {date_param_expr()} "


        args_tasks.append(task_end_date_val)





    query_tasks += " GROUP BY i.usuario_cs, p.nome, ci.tag ORDER BY cs_nome, ci.tag "





    tasks_summary_raw = query_db(query_tasks, tuple(args_tasks)) or []





    task_summary_processed = {}


    for row in tasks_summary_raw:


        if not row or not isinstance(row, dict):


            continue


        email = row.get("usuario_cs")


        if not email:


            continue





        if email not in task_summary_processed:


            task_summary_processed[email] = {


                "usuario_cs": email,


                "cs_nome": row.get("cs_nome", email),


                "Ação interna": 0,


                "Reunião": 0,


            }





        tag = row.get("tag")


        total = row.get("total_concluido", 0)


        if tag == "Ação interna":


            task_summary_processed[email]["Ação interna"] = total


        elif tag == "Reunião":


            task_summary_processed[email]["Reunião"] = total





    task_summary_list = list(task_summary_processed.values())





    # QUERY 4: Implantações finalizadas no ano


    query_impl_ano = """


        SELECT i.usuario_cs, i.data_finalizacao, i.data_criacao


        FROM implantacoes i


        WHERE i.status = 'finalizada' AND i.tipo = 'completa'


    """


    args_impl_ano = []





    if context:


        if context == "onboarding":


            query_impl_ano += " AND (i.contexto IS NULL OR i.contexto = 'onboarding') "


        else:


            query_impl_ano += " AND i.contexto = %s "


            args_impl_ano.append(context)





    query_impl_ano += " AND EXTRACT(YEAR FROM i.data_finalizacao) = %s "


    args_impl_ano.append(ano_corrente)





    if target_cs_email:


        query_impl_ano += " AND i.usuario_cs = %s "


        args_impl_ano.append(target_cs_email)





    impl_finalizadas_ano_corrente = query_db(query_impl_ano, tuple(args_impl_ano)) or []





    chart_data_ranking_periodo = dict.fromkeys(range(1, 13), 0)





    for impl in impl_finalizadas_ano_corrente:


        if not impl or not isinstance(impl, dict):


            continue


        dt_finalizacao = impl.get("data_finalizacao")





        if isinstance(dt_finalizacao, str):


            try:


                dt_finalizacao_datetime = datetime.fromisoformat(dt_finalizacao.replace("Z", "+00:00"))


            except ValueError:


                continue


        elif isinstance(dt_finalizacao, date):


            dt_finalizacao_datetime = (


                datetime.combine(dt_finalizacao, datetime.min.time())


                if not isinstance(dt_finalizacao, datetime)


                else dt_finalizacao


            )


        else:


            continue





        if dt_finalizacao_datetime and dt_finalizacao_datetime.year == ano_corrente:


            chart_data_ranking_periodo[dt_finalizacao_datetime.month] += 1





    # OTIMIZAÇÃO: Calcular dias de TODAS as implantações completas de uma vez


    completas_ids = [impl["id"] for impl in impl_completas if isinstance(impl, dict)]


    dias_completas_map = calculate_all_days_batch(completas_ids)





    # Processar métricas SEM queries individuais


    # chart_data_ranking_colab e chart_data_ranking_periodo já definidos anteriormente


    # chart_data_ranking_colab: dict[str, int] = {}


    # chart_data_ranking_periodo: dict[int, int] = {}


    chart_data_nivel_receita = dict.fromkeys(NIVEIS_RECEITA, 0)
    chart_data_nivel_receita["Nao Definido"] = 0

    # Detalhes operacionais (novos gráficos)
    segmento_counts = _init_counts(SEGUIMENTOS_LIST, include_nao_definido=True, extra_label="Outro")
    planos_counts = _init_counts(TIPOS_PLANOS, include_nao_definido=True, extra_label="Outro")
    modalidades_counts = _init_counts(MODALIDADES_LIST, include_nao_definido=True, extra_label="Outros")
    horarios_counts = _init_counts(HORARIOS_FUNCIONAMENTO, include_nao_definido=True, extra_label="Outro")
    pagamento_counts = _init_counts(FORMAS_PAGAMENTO, include_nao_definido=True, extra_label="Outra")
    sistema_counts = _init_counts(SISTEMAS_ANTERIORES, include_nao_definido=True, extra_label="Outros")
    recorrencia_counts = _init_counts(RECORRENCIA_USADA, include_nao_definido=True, extra_label="Outros")

    recursos_fields = ["diaria", "freepass", "importacao", "boleto", "nota_fiscal", "catraca", "facial", "wellhub", "totalpass"]
    recursos_counts = {field: {opt: 0 for opt in SIM_NAO_OPTIONS} for field in recursos_fields}

    alunos_buckets = {NAO_DEFINIDO_BOOL: 0, "0": 0, "1-50": 0, "51-100": 0, "101-300": 0, "301+": 0}



    # Novas estruturas para os gráficos otimizados


    gargalos_parada: dict[str, int] = {}  # {motivo: count}


    velocidade_entrega = {"0-30": 0, "31-60": 0, "61-90": 0, "90+": 0}


    previsao_receita: dict[str, int] = {}  # {mes_ano: count}





    total_impl_global = 0


    total_finalizadas = 0


    total_andamento_global = 0


    total_paradas = 0


    total_novas_global = 0


    total_futuras_global = 0


    total_canceladas_global = 0
    total_sem_previsao = 0


    tma_dias_sum = 0


    implantacoes_paradas_detalhadas = []


    implantacoes_canceladas_detalhadas = []





    chart_data_ranking_colab: dict[str, int] = {}





    for impl in impl_completas:


        if not impl or not isinstance(impl, dict):


            continue





        impl_id_raw = impl.get("id")


        if impl_id_raw is None:


            continue


        impl_id = int(impl_id_raw)


        cs_email_impl = impl.get("usuario_cs")


        cs_nome_impl = impl.get("cs_nome", cs_email_impl)


        status = impl.get("status")





        nivel_selecionado = _normalize_nivel_receita(impl.get("nivel_receita"))


        if nivel_selecionado and nivel_selecionado in chart_data_nivel_receita:


            chart_data_nivel_receita[nivel_selecionado] += 1


        else:
            chart_data_nivel_receita["Nao Definido"] += 1



        if cs_nome_impl:


            chart_data_ranking_colab[cs_nome_impl] = chart_data_ranking_colab.get(cs_nome_impl, 0) + 1





        total_impl_global += 1

        # Detalhes operacionais
        _accumulate_multi(segmento_counts, _split_multi_value(impl.get("seguimento")), NAO_DEFINIDO_BOOL, "Outro")
        _accumulate_multi(planos_counts, _split_multi_value(impl.get("tipos_planos")), NAO_DEFINIDO_BOOL, "Outro")
        _accumulate_multi(modalidades_counts, _split_multi_value(impl.get("modalidades")), NAO_DEFINIDO_BOOL, "Outros")
        _accumulate_multi(horarios_counts, _split_multi_value(impl.get("horarios_func")), NAO_DEFINIDO_BOOL, "Outro")
        _accumulate_multi(pagamento_counts, _split_multi_value(impl.get("formas_pagamento")), NAO_DEFINIDO_BOOL, "Outra")

        sistema_val = _normalize_label(impl.get("sistema_anterior"))
        if sistema_val in sistema_counts:
            sistema_counts[sistema_val] = sistema_counts.get(sistema_val, 0) + 1
        else:
            sistema_counts["Outros"] = sistema_counts.get("Outros", 0) + 1

        recorrencia_val = _normalize_label(impl.get("recorrencia_usa"))
        if recorrencia_val in recorrencia_counts:
            recorrencia_counts[recorrencia_val] = recorrencia_counts.get(recorrencia_val, 0) + 1
        else:
            recorrencia_counts["Outros"] = recorrencia_counts.get("Outros", 0) + 1

        for field in recursos_fields:
            recurso_val = _normalize_sim_nao(impl.get(field))
            if recurso_val in recursos_counts[field]:
                recursos_counts[field][recurso_val] = recursos_counts[field].get(recurso_val, 0) + 1
            else:
                recursos_counts[field][NAO_DEFINIDO_BOOL] = recursos_counts[field].get(NAO_DEFINIDO_BOOL, 0) + 1

        alunos_val = impl.get("alunos_ativos")
        if alunos_val is None or alunos_val == "":
            alunos_buckets[NAO_DEFINIDO_BOOL] += 1
        else:
            try:
                alunos_num = int(alunos_val)
            except (TypeError, ValueError):
                alunos_buckets[NAO_DEFINIDO_BOOL] += 1
            else:
                if alunos_num <= 0:
                    alunos_buckets["0"] += 1
                elif alunos_num <= 50:
                    alunos_buckets["1-50"] += 1
                elif alunos_num <= 100:
                    alunos_buckets["51-100"] += 1
                elif alunos_num <= 300:
                    alunos_buckets["101-300"] += 1
                else:
                    alunos_buckets["301+"] += 1





        if status == "finalizada":


            dt_criacao = impl.get("data_criacao")


            dt_finalizacao = impl.get("data_finalizacao")





            if isinstance(dt_criacao, str):


                try:


                    dt_criacao_datetime = datetime.fromisoformat(dt_criacao.replace("Z", "+00:00"))


                except:


                    dt_criacao_datetime = None


            elif isinstance(dt_criacao, (date, datetime)):


                dt_criacao_datetime = (


                    datetime.combine(dt_criacao, datetime.min.time())


                    if isinstance(dt_criacao, date) and not isinstance(dt_criacao, datetime)


                    else dt_criacao


                )


            else:


                dt_criacao_datetime = None





            # Usar variavel ja declarada no topo


            if isinstance(dt_finalizacao, str):


                try:


                    dt_finalizacao_datetime = datetime.fromisoformat(dt_finalizacao.replace("Z", "+00:00"))


                except:


                    dt_finalizacao_datetime = None


            elif isinstance(dt_finalizacao, (date, datetime)):


                if isinstance(dt_finalizacao, datetime):


                    dt_finalizacao_datetime = dt_finalizacao


                else:


                    dt_finalizacao_datetime = datetime.combine(dt_finalizacao, datetime.min.time())


            else:


                dt_finalizacao_datetime = None





            tma_dias = None


            if dt_criacao_datetime and dt_finalizacao_datetime:


                try:


                    delta = dt_finalizacao_datetime - dt_criacao_datetime


                    tma_dias = max(0, delta.days)


                except:


                    pass





            total_finalizadas += 1


            if tma_dias is not None:


                tma_dias_sum += tma_dias





                # Velocidade de Entrega


                if tma_dias <= 30:


                    velocidade_entrega["0-30"] += 1


                elif tma_dias <= 60:


                    velocidade_entrega["31-60"] += 1


                elif tma_dias <= 90:


                    velocidade_entrega["61-90"] += 1


                else:


                    velocidade_entrega["90+"] += 1





        elif status == "parada":


            total_paradas += 1


            # Usar dias do map (SEM query individual)


            dias_info = dias_completas_map.get(impl_id, {"dias_parada": 0})


            parada_dias = _tempo_parado_lista(impl, dias_info)





            motivo = impl.get("motivo_parada") or "Motivo Não Especificado"


            implantacoes_paradas_detalhadas.append(


                {


                    "id": impl_id,


                    "nome_empresa": impl.get("nome_empresa"),


                    "usuario_cs": impl.get("usuario_cs"),


                    "tipo": _display_tipo_implantacao(impl.get("tipo")),


                    "motivo_parada": motivo,


                    "dias_parada": parada_dias,


                    "cs_nome": cs_nome_impl,


                }


            )





            # Gargalos (Motivos de Parada)


            motivo_key = motivo.strip()


            gargalos_parada[motivo_key] = gargalos_parada.get(motivo_key, 0) + 1





        elif status == "nova":


            total_novas_global += 1





        elif status == "futura":


            total_futuras_global += 1





        elif status == "cancelada":


            total_canceladas_global += 1


            implantacoes_canceladas_detalhadas.append(


                {


                    "id": impl_id,


                    "nome_empresa": impl.get("nome_empresa"),


                    "usuario_cs": impl.get("usuario_cs"),

                    "cs_nome": cs_nome_impl,


                    "data_cancelamento": impl.get("data_cancelamento"),


                }


            )





        elif status == "sem_previsao":

            total_sem_previsao += 1


        elif status == "andamento":


            total_andamento_global += 1





            # Previsão Financeira (usando 'data_previsao_termino' ou similar se existir)


            # Como fallback, usamos data_criacao + 30 dias se nao tiver previsao explicita,


            # ou apenas marcamos como 'Sem Previsão'


            data_prev = impl.get("data_previsao_termino")


            if data_prev:


                try:


                    if isinstance(data_prev, str):


                        dt_obj = datetime.strptime(data_prev, "%Y-%m-%d").date()


                    else:


                        dt_obj = data_prev


                    mes_chave = dt_obj.strftime("%Y-%m")


                    previsao_receita[mes_chave] = previsao_receita.get(mes_chave, 0) + 1


                except:


                    previsao_receita["Indefinido"] = previsao_receita.get("Indefinido", 0) + 1


            else:


                previsao_receita["Indefinido"] = previsao_receita.get("Indefinido", 0) + 1





    include_module_paradas = target_status in (None, "", "todas", "parada")

    for parada_modulo in (modules_paradas_detalhadas if include_module_paradas else []):

        implantacoes_paradas_detalhadas.append(parada_modulo)

        total_paradas += 1

        motivo_key = (parada_modulo.get("motivo_parada") or "Motivo NÃ£o Especificado").strip()

        gargalos_parada[motivo_key] = gargalos_parada.get(motivo_key, 0) + 1

    global_metrics = {


        "total_clientes": total_impl_global,


        "total_finalizadas": total_finalizadas,


        "total_andamento": total_andamento_global,


        "total_paradas": total_paradas,


        "total_novas": total_novas_global,


        "total_futuras": total_futuras_global,


        "total_canceladas": total_canceladas_global,


        "total_sem_previsao": total_sem_previsao,


        "media_tma": round(tma_dias_sum / total_finalizadas, 1) if total_finalizadas > 0 else 0,


    }





    status_data = {
        "Novas": total_novas_global,
        "Em Andamento": total_andamento_global,
        "Paradas": total_paradas,
        "Futuras": total_futuras_global,
        "Sem Previsão": total_sem_previsao,
        "Concluídas": total_finalizadas,
        "Canceladas": total_canceladas_global,
    }





    ranking_colab_data = sorted(chart_data_ranking_colab.items(), key=lambda item: item[1], reverse=True)





    meses_nomes = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]





    chart_data = {


        "status_clientes": {"labels": list(status_data.keys()), "data": list(status_data.values())},


        "nivel_receita": {


            "labels": list(chart_data_nivel_receita.keys()),


            "data": list(chart_data_nivel_receita.values()),


        },


        "ranking_colaborador": {


            "labels": [item[0] for item in ranking_colab_data],


            "data": [item[1] for item in ranking_colab_data],


        },


        "ranking_periodo": {


            "labels": meses_nomes,


            "data": [chart_data_ranking_periodo.get(i, 0) for i in range(1, 13)],


        },


        "gargalos_parada": {"labels": list(gargalos_parada.keys()), "data": list(gargalos_parada.values())},


        "velocidade_entrega": {"labels": list(velocidade_entrega.keys()), "data": list(velocidade_entrega.values())},


        "previsao_receita": {


            "labels": sorted(previsao_receita.keys()),


            "data": [previsao_receita[k] for k in sorted(previsao_receita.keys())],


        },


        "detalhes_operacionais": {


            "segmento": _chart_from_counts(segmento_counts, SEGUIMENTOS_LIST + [NAO_DEFINIDO_BOOL, "Outro"]),


            "tipos_planos": _chart_from_counts(planos_counts, TIPOS_PLANOS + [NAO_DEFINIDO_BOOL, "Outro"]),


            "modalidades": _chart_from_counts(modalidades_counts, MODALIDADES_LIST + [NAO_DEFINIDO_BOOL, "Outros"]),


            "horarios": _chart_from_counts(horarios_counts, HORARIOS_FUNCIONAMENTO + [NAO_DEFINIDO_BOOL, "Outro"]),


            "pagamento": _chart_from_counts(pagamento_counts, FORMAS_PAGAMENTO + [NAO_DEFINIDO_BOOL, "Outra"]),


            "sistema_anterior": _top_n_chart(sistema_counts, 10, "Outros"),


            "recorrencia": _chart_from_counts(recorrencia_counts, RECORRENCIA_USADA + [NAO_DEFINIDO_BOOL, "Outros"]),


        },


        "recursos": {


            "diaria": _chart_from_counts(recursos_counts["diaria"], SIM_NAO_OPTIONS),


            "freepass": _chart_from_counts(recursos_counts["freepass"], SIM_NAO_OPTIONS),


            "importacao": _chart_from_counts(recursos_counts["importacao"], SIM_NAO_OPTIONS),


            "boleto": _chart_from_counts(recursos_counts["boleto"], SIM_NAO_OPTIONS),


            "nota_fiscal": _chart_from_counts(recursos_counts["nota_fiscal"], SIM_NAO_OPTIONS),


            "catraca": _chart_from_counts(recursos_counts["catraca"], SIM_NAO_OPTIONS),


            "facial": _chart_from_counts(recursos_counts["facial"], SIM_NAO_OPTIONS),


            "wellhub": _chart_from_counts(recursos_counts["wellhub"], SIM_NAO_OPTIONS),


            "totalpass": _chart_from_counts(recursos_counts["totalpass"], SIM_NAO_OPTIONS),


        },


        "alunos_ativos": _chart_from_counts(


            alunos_buckets, [NAO_DEFINIDO_BOOL, "0", "1-50", "51-100", "101-300", "301+"]


        ),


    }





    # Get tags by user chart data


    from ..application.tags_analytics import get_tags_by_user_chart_data





    tags_chart_data = get_tags_by_user_chart_data(


        cs_email=task_cs_email,


        start_date=task_start_date_to_query,


        end_date=task_end_date_to_query,


        context=context,


    )





    return {


        "kpi_cards": global_metrics,


        "implantacoes_lista_detalhada": impl_completas,


        "modules_implantacao_lista": modules_implantacao_lista,


        "chart_data": chart_data,


        "tags_chart_data": tags_chart_data,


        "implantacoes_paradas_lista": implantacoes_paradas_detalhadas,


        "implantacoes_canceladas_lista": implantacoes_canceladas_detalhadas,


        "task_summary_data": task_summary_list,


        "default_task_start_date": default_task_start_date_str,


        "default_task_end_date": default_task_end_date_str,


    }
