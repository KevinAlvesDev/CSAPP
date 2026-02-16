"""
Módulo de Detalhes de Implantação
Funções de formatação e atualização de detalhes.
Princípio SOLID: Single Responsibility
"""

import contextlib
from collections import OrderedDict
from datetime import datetime
from typing import Any

from flask import current_app, g

from ....common.date_helpers import add_business_days, adjust_to_business_day
from ....common.utils import format_date_br, format_date_iso_for_json
from ....constants import (
    CARGOS_RESPONSAVEL,
    FORMAS_PAGAMENTO,
    HORARIOS_FUNCIONAMENTO,
    JUSTIFICATIVAS_PARADA,
    MODALIDADES_LIST,
    NIVEIS_RECEITA,
    PERFIS_COM_GESTAO,
    RECORRENCIA_USADA,
    SEGUIMENTOS_LIST,
    SIM_NAO_OPTIONS,
    SISTEMAS_ANTERIORES,
    TIPOS_PLANOS,
)
from ....db import query_db
from ....modules.hierarquia.domain import get_hierarquia_implantacao
from ....modules.tasks.application.task_definitions import MODULO_OBRIGATORIO, MODULO_PENDENCIAS, TASK_TIPS
from .access import _get_implantacao_and_validate_access
from .progress import _get_progress


def _format_implantacao_dates(implantacao):
    """
    Formata todas as datas de uma implantação para exibição.
    """
    implantacao["data_criacao_fmt_dt_hr"] = format_date_br(implantacao.get("data_criacao"), True)
    implantacao["data_criacao_fmt_d"] = format_date_br(implantacao.get("data_criacao"), False)
    implantacao["data_inicio_efetivo_fmt_d"] = format_date_br(implantacao.get("data_inicio_efetivo"), False)
    implantacao["data_finalizacao_fmt_d"] = format_date_br(implantacao.get("data_finalizacao"), False)
    implantacao["data_inicio_producao_fmt_d"] = format_date_br(implantacao.get("data_inicio_producao"), False)
    implantacao["data_final_implantacao_fmt_d"] = format_date_br(implantacao.get("data_final_implantacao"), False)
    implantacao["data_previsao_termino_fmt_d"] = format_date_br(implantacao.get("data_previsao_termino"), False)
    implantacao["data_criacao_iso"] = format_date_iso_for_json(implantacao.get("data_criacao"), only_date=True)
    implantacao["data_inicio_efetivo_iso"] = format_date_iso_for_json(
        implantacao.get("data_inicio_efetivo"), only_date=True
    )
    implantacao["data_inicio_producao_iso"] = format_date_iso_for_json(
        implantacao.get("data_inicio_producao"), only_date=True
    )
    implantacao["data_final_implantacao_iso"] = format_date_iso_for_json(
        implantacao.get("data_final_implantacao"), only_date=True
    )
    implantacao["data_inicio_previsto_fmt_d"] = format_date_br(implantacao.get("data_inicio_previsto"), False)
    # Sempre definir data_cadastro_iso, usando data_criacao como fallback
    if implantacao.get("data_cadastro"):
        implantacao["data_cadastro_fmt_d"] = format_date_br(implantacao.get("data_cadastro"), False)
        implantacao["data_cadastro_iso"] = format_date_iso_for_json(implantacao.get("data_cadastro"), only_date=True)
    else:
        implantacao["data_cadastro_fmt_d"] = format_date_br(implantacao.get("data_criacao"), False)
        implantacao["data_cadastro_iso"] = format_date_iso_for_json(implantacao.get("data_criacao"), only_date=True)
    return implantacao


def _get_comentarios_bulk(
    impl_id: int, is_owner: bool = False, is_manager: bool = False
) -> dict[str, list[dict[str, Any]]]:
    """
    Busca TODOS os comentários de uma implantação em uma única query (ou poucas queries).
    Retorna dicionário indexado por item_id para acesso rápido.
    """
    comentarios_map = {}

    try:
        comentarios_h_raw = (
            query_db(
                """
            SELECT c.*,
                   COALESCE(p.nome, c.usuario_cs) as usuario_nome,
                   c.data_criacao as data_criacao_raw,
                   c.checklist_item_id
            FROM comentarios_h c
            LEFT JOIN perfil_usuario p ON c.usuario_cs = p.usuario
            WHERE EXISTS (
                SELECT 1 FROM checklist_items ci
                WHERE c.checklist_item_id = ci.id
                AND ci.implantacao_id = %s
            )
            ORDER BY c.data_criacao DESC
            """,
                (impl_id,),
            )
            or []
        )
    except Exception as e:
        from ....config.logging_config import get_logger

        logger = get_logger("implantacao")
        logger.warning(f"Erro ao buscar comentarios_h em bulk para implantação {impl_id}: {e}")
        comentarios_h_raw = []

    for c in comentarios_h_raw:
        if c.get("subtarefa_h_id"):
            item_key = f"subtarefa_h_{c['subtarefa_h_id']}"
        elif c.get("tarefa_h_id"):
            item_key = f"tarefa_h_{c['tarefa_h_id']}"
        else:
            continue

        if not (is_owner or is_manager) and c.get("visibilidade") == "interno":
            continue

        c_formatado = {**c, "data_criacao_fmt_d": format_date_br(c.get("data_criacao_raw"))}
        c_formatado["delete_url"] = f"/api/checklist/comment/{c['id']}"
        c_formatado["email_url"] = f"/api/checklist/comment/{c['id']}/email"

        if item_key not in comentarios_map:
            comentarios_map[item_key] = []
        comentarios_map[item_key].append(c_formatado)

    return comentarios_map


def _get_tarefas_and_comentarios(
    impl_id: int, is_owner: bool = False, is_manager: bool = False
) -> tuple[OrderedDict, OrderedDict, OrderedDict, list[str]]:
    """
    Carrega tarefas e comentários de uma implantação.
    """
    from ....common.dataloader import ChecklistDataLoader

    comentarios_map = _get_comentarios_bulk(impl_id, is_owner, is_manager)

    tarefas_agrupadas_treinamento: OrderedDict[str, list[dict[str, Any]]] = OrderedDict()
    tarefas_agrupadas_obrigatorio: OrderedDict[str, list[dict[str, Any]]] = OrderedDict()
    tarefas_agrupadas_pendencias: OrderedDict[str, list[dict[str, Any]]] = OrderedDict()
    todos_modulos_temp: set[str] = set()

    loader = ChecklistDataLoader(impl_id)

    try:
        fases = loader.get_fases()
    except Exception as e:
        from ....config.logging_config import get_logger

        logger = get_logger("implantacao")
        logger.warning(f"Erro ao carregar fases para implantação {impl_id}: {e}")
        fases = []

    if fases:
        for fase in fases:
            grupos = loader.get_grupos(fase["id"])

            for grupo in grupos:
                modulo_nome = grupo.get("title") or grupo.get("nome") or f"Grupo {grupo.get('id')}"
                todos_modulos_temp.add(modulo_nome)
                tarefas = loader.get_tarefas(grupo["id"])

                ordem_c = 1
                for th in tarefas:
                    subtarefas = loader.get_subtarefas(th["id"])

                    if subtarefas:
                        for sub in subtarefas:
                            comentarios_sub = comentarios_map.get(f"subtarefa_h_{sub['id']}", [])

                            tarefas_agrupadas_treinamento.setdefault(modulo_nome, []).append(
                                {
                                    "id": sub["id"],
                                    "tarefa_filho": sub.get("title") or sub.get("nome"),
                                    "concluida": bool(sub.get("completed")),
                                    "tag": sub.get("tag", ""),
                                    "ordem": sub.get("ordem", ordem_c),
                                    "comentarios": comentarios_sub,
                                    "toggle_url": f"/api/checklist/toggle/{sub['id']}",
                                    "comment_url": f"/api/checklist/comment/{sub['id']}",
                                    "delete_url": f"/api/checklist/delete/{sub['id']}",
                                }
                            )
                            ordem_c += 1
                    else:
                        concl = bool(th.get("completed", False))
                        comentarios_th = comentarios_map.get(f"tarefa_h_{th['id']}", [])

                        tarefas_agrupadas_treinamento.setdefault(modulo_nome, []).append(
                            {
                                "id": th["id"],
                                "tarefa_filho": th.get("title") or th.get("nome"),
                                "concluida": concl,
                                "tag": "",
                                "ordem": th.get("ordem", ordem_c),
                                "comentarios": comentarios_th,
                                "toggle_url": f"/api/checklist/toggle/{th['id']}",
                                "comment_url": f"/api/checklist/comment/{th['id']}",
                                "delete_url": f"/api/checklist/delete/{th['id']}",
                            }
                        )
                        ordem_c += 1

                if modulo_nome in tarefas_agrupadas_treinamento:
                    tarefas_agrupadas_treinamento[modulo_nome].sort(key=lambda x: x.get("ordem", 0))

    ordered_treinamento: OrderedDict[str, list[dict[str, Any]]] = OrderedDict()
    modulo_ordem_map: dict[str, int] = {}
    for modulo, lista in tarefas_agrupadas_treinamento.items():
        try:
            modulo_ordem_map[modulo] = min(t.get("ordem") or 0 for t in (lista or []))
        except Exception:
            modulo_ordem_map[modulo] = 0
    for modulo in [k for k, _ in sorted(modulo_ordem_map.items(), key=lambda x: (x[1], x[0]), reverse=True)]:
        ordered_treinamento[modulo] = tarefas_agrupadas_treinamento.get(modulo, [])

    if MODULO_OBRIGATORIO in todos_modulos_temp:
        todos_modulos_temp.discard(MODULO_OBRIGATORIO)

    todos_modulos_lista: list[str] = sorted(todos_modulos_temp, key=lambda m: modulo_ordem_map.get(m, 0), reverse=True)
    if MODULO_PENDENCIAS not in todos_modulos_lista:
        todos_modulos_lista.append(MODULO_PENDENCIAS)

    return tarefas_agrupadas_obrigatorio, ordered_treinamento, tarefas_agrupadas_pendencias, todos_modulos_lista


def get_implantacao_details(
    impl_id: int, usuario_cs_email: str, user_perfil: dict = None, plano_historico_id: int = None
) -> dict[str, Any]:
    """
    Busca, processa e valida todos os dados para a página de detalhes da implantação.
    """
    from ....config.logging_config import get_logger

    logger = get_logger("implantacao")

    if user_perfil is None:
        user_perfil = {}

    try:
        from ....config.cache_config import clear_implantacao_cache

        clear_implantacao_cache(impl_id)
    except Exception:
        pass

    try:
        implantacao, is_manager = _get_implantacao_and_validate_access(impl_id, usuario_cs_email, user_perfil)
    except ValueError as e:
        logger.warning(f"Acesso negado à implantação {impl_id}: {e!s}")
        raise
    except Exception as e:
        logger.error(f"Erro ao validar acesso à implantação {impl_id}: {e}", exc_info=True)
        raise

    try:
        implantacao = _format_implantacao_dates(implantacao)
    except Exception as e:
        logger.error(f"Erro ao formatar datas da implantação {impl_id}: {e}", exc_info=True)
        raise

    try:
        progresso, _, _ = _get_progress(impl_id)
    except Exception as e:
        logger.error(f"Erro ao calcular progresso da implantação {impl_id}: {e}", exc_info=True)
        raise

    try:
        is_owner = implantacao.get("usuario_cs") == usuario_cs_email
        tarefas_agrupadas_obrigatorio, ordered_treinamento, tarefas_agrupadas_pendencias, todos_modulos_lista = (
            _get_tarefas_and_comentarios(impl_id, is_owner=is_owner, is_manager=is_manager)
        )
    except Exception as e:
        logger.error(f"Erro ao carregar tarefas da implantação {impl_id}: {e}", exc_info=True)
        raise

    try:
        hierarquia = get_hierarquia_implantacao(impl_id)
    except Exception as e:
        import traceback

        error_trace = traceback.format_exc()
        logger.warning(
            f"Erro ao carregar hierarquia da implantação {impl_id}: {e}\n{error_trace}. Usando estrutura vazia."
        )
        hierarquia = {"fases": []}

    try:
        logs_timeline = _get_timeline_logs(impl_id)
    except Exception as e:
        logger.error(f"Erro ao carregar timeline da implantação {impl_id}: {e}", exc_info=True)
        raise

    nome_usuario_logado = user_perfil.get("nome", usuario_cs_email) if user_perfil else usuario_cs_email

    all_cs_users = []
    try:
        all_cs_users = query_db(
            "SELECT usuario, nome FROM perfil_usuario WHERE perfil_acesso IS NOT NULL AND perfil_acesso != '' ORDER BY nome"
        )
        all_cs_users = all_cs_users if all_cs_users is not None else []
    except Exception as e:
        logger.error(f"Erro ao carregar lista de CS users: {e}", exc_info=True)
        all_cs_users = []

    success_plan_id = plano_historico_id or implantacao.get("plano_sucesso_id")

    plano_sucesso_info = None
    try:
        if success_plan_id:
            plano_sucesso_info = query_db("SELECT * FROM planos_sucesso WHERE id = %s", (success_plan_id,), one=True)
            if plano_sucesso_info:
                plano_sucesso_info["data_criacao_fmt"] = format_date_br(plano_sucesso_info.get("data_criacao"), False)
                plano_sucesso_info["data_atualizacao_fmt"] = format_date_br(
                    plano_sucesso_info.get("data_atualizacao"), plano_sucesso_info.get("status") != "concluido"
                )
                plano_sucesso_info["data_conclusao_fmt"] = format_date_br(
                    plano_sucesso_info.get("data_atualizacao"), False
                )
    except Exception as e:
        logger.warning(f"Erro ao buscar plano de sucesso {success_plan_id}: {e}")

    checklist_nested = None
    try:
        from ....modules.checklist.application.checklist_service import build_nested_tree, get_checklist_tree

        if plano_historico_id:
            checklist_flat = get_checklist_tree(plano_id=plano_historico_id, include_progress=True)
        else:
            checklist_flat = get_checklist_tree(implantacao_id=impl_id, include_progress=True)

        if not checklist_flat and implantacao.get("plano_sucesso_id") and plano_sucesso_info and not plano_historico_id:
            logger.warning(
                f"Implantação {impl_id} tem plano {implantacao['plano_sucesso_id']} mas checklist vazio. Tentando auto-reparar..."
            )
            try:
                from datetime import date as datetime_date
                from datetime import datetime as datetime_dt

                from ....db import db_connection
                from ....modules.planos.domain.aplicar import _clonar_plano_para_implantacao_checklist

                plano_id = implantacao["plano_sucesso_id"]
                dias_duracao = plano_sucesso_info.get("dias_duracao") or 0

                data_base = implantacao.get("data_inicio_efetivo") or implantacao.get("data_criacao")
                base_dt = datetime_dt.now()

                if data_base:
                    if isinstance(data_base, str):
                        with contextlib.suppress(ValueError, TypeError):
                            base_dt = datetime_dt.strptime(data_base[:10], "%Y-%m-%d")
                    elif isinstance(data_base, datetime_dt):
                        base_dt = data_base
                    elif isinstance(data_base, datetime_date):
                        base_dt = datetime_dt.combine(data_base, datetime_dt.min.time())

                base_dia_util = adjust_to_business_day(base_dt.date())
                data_previsao = add_business_days(base_dia_util, int(dias_duracao))
                data_previsao = adjust_to_business_day(data_previsao)

                with db_connection() as (conn, db_type):
                    cursor = conn.cursor()
                    responsavel = "sistema"

                    _clonar_plano_para_implantacao_checklist(
                        cursor, db_type, plano_id, impl_id, responsavel, base_dt, int(dias_duracao), data_previsao
                    )
                    conn.commit()

                logger.info("Auto-reparo concluído. Recarregando checklist...")
                try:
                    from ....config.cache_config import clear_implantacao_cache

                    clear_implantacao_cache(impl_id)
                except Exception:
                    pass

                checklist_flat = get_checklist_tree(implantacao_id=impl_id, include_progress=True)
            except Exception as e:
                logger.error(f"Falha no auto-reparo do checklist: {e}", exc_info=True)

        if checklist_flat:
            checklist_nested = build_nested_tree(checklist_flat)
    except Exception as e:
        import traceback

        error_trace = traceback.format_exc()
        logger.warning(
            f"Erro ao carregar checklist da implantação {impl_id}: {e}\n{error_trace}. Usando checklist vazio."
        )
        checklist_nested = []

    try:
        user_info = getattr(g, "user", None) or {
            "email": usuario_cs_email,
            "nome": user_perfil.get("nome", usuario_cs_email) if user_perfil else usuario_cs_email,
        }
    except Exception:
        user_info = {
            "email": usuario_cs_email,
            "nome": user_perfil.get("nome", usuario_cs_email) if user_perfil else usuario_cs_email,
        }

    planos_lista = []
    plano_ativo_instancia = None
    try:
        planos_lista = (
            query_db(
                "SELECT * FROM planos_sucesso WHERE processo_id = %s ORDER BY data_criacao DESC", (impl_id,)
            )
            or []
        )

        if plano_historico_id:
            plano_ativo_instancia = query_db("SELECT * FROM planos_sucesso WHERE id = %s", (plano_historico_id,), one=True)
        else:
            plano_ativo_instancia = next((p for p in planos_lista if p.get("status") == "em_andamento"), None)

            if not plano_ativo_instancia and implantacao.get("plano_sucesso_id"):
                temp_p = query_db(
                    "SELECT * FROM planos_sucesso WHERE id = %s", (implantacao["plano_sucesso_id"],), one=True
                )
                if temp_p and temp_p.get("status") == "em_andamento":
                    plano_ativo_instancia = temp_p

        for p in planos_lista:
            p["data_criacao_fmt"] = format_date_br(p.get("data_criacao"), False)
            p["data_atualizacao_fmt"] = format_date_br(p.get("data_atualizacao"), p.get("status") != "concluido")
            p["data_conclusao_fmt"] = format_date_br(p.get("data_atualizacao"), False)

        if plano_ativo_instancia:
            plano_ativo_instancia["data_criacao_fmt"] = format_date_br(plano_ativo_instancia.get("data_criacao"), False)
            plano_ativo_instancia["data_atualizacao_fmt"] = format_date_br(
                plano_ativo_instancia.get("data_atualizacao"), plano_ativo_instancia.get("status") != "concluido"
            )
    except Exception as e:
        logger.warning(f"Erro ao buscar lista de planos da implantação {impl_id}: {e}")

    return {
        "user_info": user_info,
        "implantacao": implantacao,
        "hierarquia": hierarquia,
        "tarefas_agrupadas_obrigatorio": tarefas_agrupadas_obrigatorio,
        "tarefas_agrupadas_treinamento": ordered_treinamento,
        "tarefas_agrupadas_pendencias": tarefas_agrupadas_pendencias,
        "todos_modulos": todos_modulos_lista,
        "modulo_pendencias_nome": MODULO_PENDENCIAS,
        "progresso_porcentagem": progresso,
        "nome_usuario_logado": nome_usuario_logado,
        "email_usuario_logado": usuario_cs_email,
        "justificativas_parada": JUSTIFICATIVAS_PARADA,
        "logs_timeline": logs_timeline,
        "cargos_responsavel": CARGOS_RESPONSAVEL,
        "NIVEIS_RECEITA": NIVEIS_RECEITA,
        "SEGUIMENTOS_LIST": SEGUIMENTOS_LIST,
        "TIPOS_PLANOS": TIPOS_PLANOS,
        "MODALIDADES_LIST": MODALIDADES_LIST,
        "HORARIOS_FUNCIONAMENTO": HORARIOS_FUNCIONAMENTO,
        "FORMAS_PAGAMENTO": FORMAS_PAGAMENTO,
        "SISTEMAS_ANTERIORES": SISTEMAS_ANTERIORES,
        "RECORRENCIA_USADA": RECORRENCIA_USADA,
        "SIM_NAO_OPTIONS": SIM_NAO_OPTIONS,
        "all_cs_users": all_cs_users,
        "is_manager": is_manager,
        "is_owner": implantacao.get("usuario_cs") == usuario_cs_email,
        "tt": TASK_TIPS,
        "plano_sucesso": plano_sucesso_info,
        "checklist_tree": checklist_nested,
        "planos_lista": planos_lista,
        "plano_ativo_instancia": plano_ativo_instancia,
        "is_historico_view": bool(plano_historico_id),
        "plano_historico_id": plano_historico_id,
    }

def _get_timeline_logs(impl_id):
    """
    Busca os logs de timeline de uma implantação.
    """
    import re

    logs_timeline = query_db(
        """ SELECT tl.*, COALESCE(p.nome, tl.usuario_cs) as usuario_nome
            FROM timeline_log tl LEFT JOIN perfil_usuario p ON tl.usuario_cs = p.usuario
            WHERE tl.implantacao_id = %s ORDER BY tl.data_criacao DESC """,
        (impl_id,),
    )
    for log in logs_timeline:
        log["data_criacao_fmt_dt_hr"] = format_date_br(log.get("data_criacao"), True)
        try:
            detalhes = log.get("detalhes") or ""
            m = re.search(r"(Item|Subtarefa|TarefaH)\s+(\d+)", detalhes)
            if not m:
                m = re.search(r'data-item-id="(\d+)"', detalhes)
            log["related_item_id"] = (
                int(m.group(2) if m and m.groups() and len(m.groups()) > 1 else (m.group(1) if m else 0)) or None
            )
        except Exception:
            log["related_item_id"] = None
    return logs_timeline


def atualizar_detalhes_empresa_service(implantacao_id, usuario_cs_email, user_perfil_acesso, campos):
    """
    Atualiza os detalhes da empresa de uma implantação.
    """
    from ....common.error_messages import format_validation_errors
    from ....common.field_validators import validate_detalhes_empresa

    impl = query_db("SELECT id, usuario_cs FROM implantacoes WHERE id = %s", (implantacao_id,), one=True)

    if not impl:
        raise ValueError("Implantação não encontrada.")

    is_owner = impl.get("usuario_cs") == usuario_cs_email
    is_manager = user_perfil_acesso in PERFIS_COM_GESTAO

    if not (is_owner or is_manager):
        raise ValueError("Permissão negada.")

    # CRITICAL: Validate all fields before saving
    is_valid, validation_errors = validate_detalhes_empresa(campos)
    if not is_valid:
        error_message = format_validation_errors(validation_errors)
        raise ValueError(error_message)

    allowed_fields = {
        "email_responsavel",
        "responsavel_cliente",
        "cargo_responsavel",
        "telefone_responsavel",
        "data_inicio_producao",
        "data_final_implantacao",
        "data_inicio_efetivo",
        "data_previsao_termino",
        "id_favorecido",
        "nivel_receita",
        "valor_atribuido",  # Nível de Receita (MRR)
        "chave_oamd",
        "tela_apoio_link",
        "informacao_infra",
        "seguimento",
        "tipos_planos",
        "modalidades",
        "horarios_func",
        "formas_pagamento",
        "diaria",
        "freepass",
        "alunos_ativos",
        "sistema_anterior",
        "importacao",
        "recorrencia_usa",
        "boleto",
        "nota_fiscal",
        "catraca",
        "modelo_catraca",
        "facial",
        "modelo_facial",
        "wellhub",
        "totalpass",
        "cnpj",
        "status_implantacao_oamd",
        "nivel_atendimento",
        "valor_monetario",
        "data_cadastro",
        "resp_estrategico_nome",
        "resp_onb_nome",
        "resp_estrategico_obs",
        "contatos",
    }

    # Recalcular previsão se data_inicio_efetivo mudou
    if campos.get("data_inicio_efetivo"):
        try:
            # Buscar info do plano atual
            info_plano = query_db(
                """
                SELECT p.dias_duracao
                FROM implantacoes i
                JOIN planos_sucesso p ON i.plano_sucesso_id = p.id
                WHERE i.id = %s
                """,
                (implantacao_id,),
                one=True,
            )

            if info_plano and info_plano.get("dias_duracao"):
                dias = int(info_plano["dias_duracao"])
                dt_str = str(campos["data_inicio_efetivo"])[:10]
                dt_inicio = datetime.strptime(dt_str, "%Y-%m-%d")
                dt_inicio_util = adjust_to_business_day(dt_inicio.date())
                nova_prev = add_business_days(dt_inicio_util, dias)
                nova_prev = adjust_to_business_day(nova_prev)

                # Atualizar campo de previs?o
                campos["data_previsao_termino"] = nova_prev.strftime("%Y-%m-%d")
                current_app.logger.info(
                    f"Previs?o recalculada para {campos['data_previsao_termino']} (In?cio: {dt_str}, Dura??o: {dias} dias ?teis)"
                )

                # Recalcular previsao_original dos checklist_items desta implanta??o
                # Para itens com dias_offset: previsao_original = dt_inicio + dias_offset (dias ?teis)
                # Para itens sem dias_offset: previsao_original = nova data_previsao_termino
                try:
                    from ....db import db_connection as _db_conn

                    with _db_conn() as (_conn, _db_type):
                        _cursor = _conn.cursor()
                        placeholder = "%s" if _db_type == "postgres" else "?"

                        _cursor.execute(
                            f"SELECT id, dias_offset FROM checklist_items WHERE implantacao_id = {placeholder} AND dias_offset IS NOT NULL",
                            (implantacao_id,),
                        )
                        items_com_offset = _cursor.fetchall()

                        for item_row in items_com_offset:
                            if isinstance(item_row, (list, tuple)):
                                item_id = item_row[0]
                                offset = item_row[1]
                            else:
                                item_id = item_row["id"]
                                offset = item_row["dias_offset"]

                            nova_previsao_orig = add_business_days(dt_inicio_util, int(offset))
                            nova_previsao_orig = adjust_to_business_day(nova_previsao_orig)
                            _cursor.execute(
                                f"UPDATE checklist_items SET previsao_original = {placeholder}, updated_at = CURRENT_TIMESTAMP WHERE id = {placeholder}",
                                (nova_previsao_orig.strftime("%Y-%m-%d"), item_id),
                            )

                        _cursor.execute(
                            f"""
                            UPDATE checklist_items
                            SET previsao_original = {placeholder},
                                updated_at = CURRENT_TIMESTAMP
                            WHERE implantacao_id = {placeholder}
                              AND dias_offset IS NULL
                              AND previsao_original IS NOT NULL
                            """,
                            (nova_prev.strftime("%Y-%m-%d"), implantacao_id),
                        )

                        _conn.commit()
                        current_app.logger.info(
                            f"Previs?o original dos checklist_items recalculada para implanta??o {implantacao_id} (novo in?cio: {dt_str})"
                        )
                except Exception as recalc_err:
                    current_app.logger.warning(
                        f"Erro ao recalcular previsao_original dos checklist_items: {recalc_err}"
                    )

        except Exception as e:
            current_app.logger.warning(f"Erro ao recalcular previsão de término: {e}")

    set_clauses = []
    values = []
    for k, v in campos.items():
        if k in allowed_fields:
            set_clauses.append(f"{k} = %s")
            values.append(v)
    if not set_clauses:
        return False
    values.append(implantacao_id)
    query = f"UPDATE implantacoes SET {', '.join(set_clauses)} WHERE id = %s"

    # ATOMIC TRANSACTION: UPDATE + timeline logging
    from ....db import db_connection

    with db_connection() as (conn, db_type):
        cursor = conn.cursor()

        try:
            # Operation 1: UPDATE implantacoes
            update_query = query
            if db_type == "sqlite":
                update_query = update_query.replace("%s", "?")
            cursor.execute(update_query, tuple(values))

            # Operation 2: INSERT timeline log
            timeline_query = "INSERT INTO timeline_log (implantacao_id, usuario_cs, tipo_evento, detalhes, data_criacao) VALUES (%s, %s, %s, %s, %s)"
            if db_type == "sqlite":
                timeline_query = timeline_query.replace("%s", "?")
            cursor.execute(
                timeline_query,
                (
                    implantacao_id,
                    usuario_cs_email,
                    "detalhes_alterados",
                    "Detalhes da empresa foram atualizados",
                    datetime.now(),
                ),
            )

            # COMMIT only if both operations succeed
            conn.commit()

            # Cache Invalidation
            try:
                from ....config.cache_config import clear_implantacao_cache, clear_user_cache

                clear_implantacao_cache(implantacao_id)
                # Limpar cache do dono da implantação
                clear_user_cache(usuario_cs_email)  # Se for o dono, limpa o dele
                if not is_owner:
                    # Se quem editou foi um gestor, limpa o cache do dono original também
                    impl_owner = impl.get("usuario_cs")
                    if impl_owner and impl_owner != usuario_cs_email:
                        clear_user_cache(impl_owner)
            except Exception as cache_err:
                current_app.logger.warning(f"Cache clearing failed: {cache_err}")

            current_app.logger.info(f"Transaction committed: updated implantacao {implantacao_id} + logged timeline")
            return True

        except Exception as e:
            # ROLLBACK automatically by context manager
            conn.rollback()
            current_app.logger.error(f"Transaction failed and rolled back for implantacao {implantacao_id}: {e}")
            raise
