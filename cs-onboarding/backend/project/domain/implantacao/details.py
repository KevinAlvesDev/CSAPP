"""
Módulo de Detalhes de Implantação
Funções de formatação e atualização de detalhes.
Princípio SOLID: Single Responsibility
"""

from datetime import datetime, timedelta

from flask import current_app

from ...common.utils import format_date_br, format_date_iso_for_json
from ...constants import (
    PERFIS_COM_GESTAO,
)
from ...db import query_db


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

    # Formatação de novos campos
    # CRITICAL FIX: Sempre definir data_cadastro_iso, usando data_criacao como fallback
    # Isso garante que o modal tenha sempre uma data para exibir
    if implantacao.get("data_cadastro"):
        implantacao["data_cadastro_fmt_d"] = format_date_br(implantacao.get("data_cadastro"), False)
        implantacao["data_cadastro_iso"] = format_date_iso_for_json(implantacao.get("data_cadastro"), only_date=True)
    else:
        # Fallback: usar data_criacao se data_cadastro estiver vazio
        implantacao["data_cadastro_fmt_d"] = format_date_br(implantacao.get("data_criacao"), False)
        implantacao["data_cadastro_iso"] = format_date_iso_for_json(implantacao.get("data_criacao"), only_date=True)

    return implantacao


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
    from ...common.error_messages import format_validation_errors
    from ...common.field_validators import validate_detalhes_empresa

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
                nova_prev = dt_inicio + timedelta(days=dias)

                # Atualizar campo de previsão
                campos["data_previsao_termino"] = nova_prev.strftime("%Y-%m-%d")
                current_app.logger.info(
                    f"Previsão recalculada para {campos['data_previsao_termino']} (Início: {dt_str}, Duração: {dias} dias)"
                )

                # Recalcular previsao_original dos checklist_items desta implantação
                # Para itens com dias_offset: previsao_original = dt_inicio + dias_offset
                # Para itens sem dias_offset: previsao_original = nova data_previsao_termino
                try:
                    from ...db import db_connection as _db_conn

                    with _db_conn() as (_conn, _db_type):
                        _cursor = _conn.cursor()

                        # Atualizar itens COM dias_offset definido
                        if _db_type == "postgres":
                            _cursor.execute(
                                """
                                UPDATE checklist_items
                                SET previsao_original = %s::timestamp + (dias_offset || ' days')::interval,
                                    updated_at = CURRENT_TIMESTAMP
                                WHERE implantacao_id = %s
                                  AND dias_offset IS NOT NULL
                                """,
                                (dt_inicio, implantacao_id),
                            )
                        else:
                            # SQLite: buscar e atualizar individualmente (BUSINESS DAYS)
                            try:
                                from ...common.date_helpers import add_business_days
                                _cursor.execute(
                                    "SELECT id, dias_offset FROM checklist_items WHERE implantacao_id = ? AND dias_offset IS NOT NULL",
                                    (implantacao_id,),
                                )
                                items_com_offset = _cursor.fetchall()
                                for item_row in items_com_offset:
                                    # Handle both tuple (sqlite) and dict (postgres driver sometimes) rows
                                    if isinstance(item_row, (list, tuple)):
                                        item_id = item_row[0]
                                        offset = item_row[1]
                                    else:
                                        item_id = item_row["id"]
                                        offset = item_row["dias_offset"]
                                        
                                    nova_previsao_orig = add_business_days(dt_inicio.date(), int(offset))
                                    _cursor.execute(
                                        "UPDATE checklist_items SET previsao_original = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                                        (nova_previsao_orig.strftime("%Y-%m-%d"), item_id),
                                    )
                            except Exception as e:
                                # Fallback simples
                                current_app.logger.warning(f"Erro ao recalcular datas SQLite (Business Days): {e}. Usando Calendar Days.")
                                _cursor.execute(
                                    "SELECT id, dias_offset FROM checklist_items WHERE implantacao_id = ? AND dias_offset IS NOT NULL",
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
                                    
                                    nova_previsao_orig = dt_inicio + timedelta(days=int(offset))
                                    _cursor.execute(
                                        "UPDATE checklist_items SET previsao_original = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                                        (nova_previsao_orig.strftime("%Y-%m-%d"), item_id),
                                    )

                        # Atualizar itens SEM dias_offset (usam data_previsao_termino geral)
                        if _db_type == "postgres":
                            _cursor.execute(
                                """
                                UPDATE checklist_items
                                SET previsao_original = %s,
                                    updated_at = CURRENT_TIMESTAMP
                                WHERE implantacao_id = %s
                                  AND dias_offset IS NULL
                                  AND previsao_original IS NOT NULL
                                """,
                                (nova_prev, implantacao_id),
                            )
                        else:
                            _cursor.execute(
                                """
                                UPDATE checklist_items
                                SET previsao_original = ?,
                                    updated_at = CURRENT_TIMESTAMP
                                WHERE implantacao_id = ?
                                  AND dias_offset IS NULL
                                  AND previsao_original IS NOT NULL
                                """,
                                (nova_prev, implantacao_id),
                            )

                        _conn.commit()
                        current_app.logger.info(
                            f"Previsão original dos checklist_items recalculada para implantação {implantacao_id} (novo início: {dt_str})"
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
    from ...db import db_connection

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
                from ...config.cache_config import clear_implantacao_cache, clear_user_cache

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
