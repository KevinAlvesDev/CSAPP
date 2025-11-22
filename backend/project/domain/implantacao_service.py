from flask import g
from ..db import query_db, execute_db, logar_timeline


from ..task_definitions import TAREFAS_TREINAMENTO_PADRAO, MODULO_PENDENCIAS

from ..constants import (
    PERFIS_COM_GESTAO,
    JUSTIFICATIVAS_PARADA,
    CARGOS_RESPONSAVEL,
    NIVEIS_RECEITA,
    SEGUIMENTOS_LIST,
    TIPOS_PLANOS,
    MODALIDADES_LIST,
    HORARIOS_FUNCIONAMENTO,
    FORMAS_PAGAMENTO,
    SISTEMAS_ANTERIORES,
    RECORRENCIA_USADA,
    SIM_NAO_OPTIONS,
)

from ..utils import format_date_iso_for_json, format_date_br
from datetime import datetime
from collections import OrderedDict


def _create_default_tasks(impl_id):
    """Cria as tarefas padrão para uma nova implantação (sem módulo Obrigatório)."""
    tasks_added = 0

    for modulo, tarefas_info in TAREFAS_TREINAMENTO_PADRAO.items():
        for i, tarefa_info in enumerate(tarefas_info, 1):
            execute_db(
                "INSERT INTO tarefas (implantacao_id, tarefa_pai, tarefa_filho, ordem, tag) VALUES (%s, %s, %s, %s, %s)",
                (impl_id, modulo, tarefa_info["nome"], i, tarefa_info.get("tag", "")),
            )
            tasks_added += 1
    return tasks_added


def _get_progress(impl_id):
    try:
        stats = query_db(
            """
            SELECT 
                COUNT(*) as total, 
                SUM(CASE WHEN t.percentual_conclusao = 100 THEN 1 ELSE 0 END) as done 
            FROM tarefas_h t
            JOIN grupos g ON t.grupo_id = g.id
            JOIN fases f ON g.fase_id = f.id
            WHERE f.implantacao_id = %s
            """,
            (impl_id,),
            one=True
        )
        total = stats.get("total", 0) if stats else 0
        done = stats.get("done", 0) if stats else 0
        done = int(done) if done is not None else 0
        return int(round((done / total) * 100)) if total > 0 else 0, total, done
    except Exception:
        stats = query_db(
            """
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN COALESCE(concluida, 0) = 1 THEN 1 ELSE 0 END) as done
            FROM tarefas
            WHERE implantacao_id = %s
            """,
            (impl_id,),
            one=True
        )
        total = stats.get("total", 0) if stats else 0
        done = stats.get("done", 0) if stats else 0
        done = int(done) if done is not None else 0
        return int(round((done / total) * 100)) if total > 0 else 0, total, done


def auto_finalizar_implantacao(impl_id, usuario_cs_email):
    """
    Verifica se todas as tarefas estão concluídas
    e, em caso afirmativo, finaliza a implantação.
    """
    progress, total, done = _get_progress(impl_id)

    if total > 0 and total == done:
        impl_status = query_db(
            "SELECT status, nome_empresa FROM implantacoes WHERE id = %s",
            (impl_id,),
            one=True,
        )
        if impl_status and impl_status.get("status") == "andamento":
            agora = datetime.now()
            execute_db(
                "UPDATE implantacoes SET status = 'finalizada', data_finalizacao = %s WHERE id = %s",
                (agora, impl_id),
            )
            detalhe = f'Implantação "{impl_status.get("nome_empresa", "N/A")}" auto-finalizada.'
            logar_timeline(impl_id, usuario_cs_email, "auto_finalizada", detalhe)

            perfil = query_db(
                "SELECT nome FROM perfil_usuario WHERE usuario = %s",
                (usuario_cs_email,),
                one=True,
            )
            return True, None # Simplified return for now
    return False, None

    return False, None


def _get_implantacao_and_validate_access(impl_id, usuario_cs_email, user_perfil):
    user_perfil_acesso = user_perfil.get("perfil_acesso") if user_perfil else None
    implantacao = query_db(
        "SELECT * FROM implantacoes WHERE id = %s", (impl_id,), one=True
    )

    if not implantacao:
        raise ValueError("Implantação não encontrada.")

    is_owner = implantacao.get("usuario_cs") == usuario_cs_email
    is_manager = user_perfil_acesso in PERFIS_COM_GESTAO

    if not is_owner and not is_manager:
        if implantacao.get("status") == "nova":
            raise ValueError("Esta implantação ainda não foi iniciada.")
        else:
            raise ValueError("Implantação não encontrada ou não pertence a você.")

    return implantacao, is_manager


def _format_implantacao_dates(implantacao):
    implantacao["data_criacao_fmt_dt_hr"] = format_date_br(
        implantacao.get("data_criacao"), True
    )
    implantacao["data_criacao_fmt_d"] = format_date_br(
        implantacao.get("data_criacao"), False
    )
    implantacao["data_inicio_efetivo_fmt_d"] = format_date_br(
        implantacao.get("data_inicio_efetivo"), False
    )
    implantacao["data_finalizacao_fmt_d"] = format_date_br(
        implantacao.get("data_finalizacao"), False
    )
    implantacao["data_inicio_producao_fmt_d"] = format_date_br(
        implantacao.get("data_inicio_producao"), False
    )
    implantacao["data_final_implantacao_fmt_d"] = format_date_br(
        implantacao.get("data_final_implantacao"), False
    )
    implantacao["data_criacao_iso"] = format_date_iso_for_json(
        implantacao.get("data_criacao"), only_date=True
    )
    implantacao["data_inicio_efetivo_iso"] = format_date_iso_for_json(
        implantacao.get("data_inicio_efetivo"), only_date=True
    )
    implantacao["data_inicio_producao_iso"] = format_date_iso_for_json(
        implantacao.get("data_inicio_producao"), only_date=True
    )
    implantacao["data_final_implantacao_iso"] = format_date_iso_for_json(
        implantacao.get("data_final_implantacao"), only_date=True
    )
    implantacao["data_inicio_previsto_fmt_d"] = format_date_br(
        implantacao.get("data_inicio_previsto"), False
    )
    return implantacao


def get_implantacao_details(impl_id, usuario_cs_email, user_perfil):
    """
    Busca, processa e valida todos os dados para a página de detalhes da implantação.
    Levanta um ValueError se o acesso for negado.
    """

    implantacao, is_manager = _get_implantacao_and_validate_access(
        impl_id, usuario_cs_email, user_perfil
    )
    implantacao = _format_implantacao_dates(implantacao)

    try:
        progresso, _, _ = _get_progress(impl_id)
    except Exception:
        progresso = 0


def _get_hierarquia_implantacao(impl_id):
    try:
        fases = query_db(
            "SELECT * FROM fases WHERE implantacao_id = %s ORDER BY ordem", (impl_id,)
        )
        if not fases:
            return []
        for fase in fases:
            grupos = query_db(
                "SELECT * FROM grupos WHERE fase_id = %s ORDER BY ordem", (fase["id"],)
            )
            fase["grupos"] = grupos if grupos else []
            for grupo in fase["grupos"]:
                tarefas = query_db(
                    "SELECT * FROM tarefas_h WHERE grupo_id = %s ORDER BY id", (grupo["id"],)
                )
                grupo["tarefas"] = tarefas if tarefas else []
                for tarefa in grupo["tarefas"]:
                    subtarefas = query_db(
                        "SELECT * FROM subtarefas_h WHERE tarefa_id = %s ORDER BY id",
                        (tarefa["id"],),
                    )
                    tarefa["subtarefas"] = subtarefas if subtarefas else []
        return fases
    except Exception:
        tarefas_flat = query_db(
            "SELECT tarefa_pai, tarefa_filho FROM tarefas WHERE implantacao_id = %s ORDER BY ordem",
            (impl_id,)
        ) or []
        grupos_map = {}
        for t in tarefas_flat:
            pai = t.get("tarefa_pai") or "Treinamento"
            grupos_map.setdefault(pai, []).append({
                "id": None,
                "nome": t.get("tarefa_filho"),
                "percentual_conclusao": None,
            })
        fase = {"id": 1, "nome": "Treinamento", "grupos": []}
        for nome_grupo, tarefas_list in grupos_map.items():
            fase["grupos"].append({
                "id": None,
                "nome": nome_grupo,
                "tarefas": tarefas_list,
            })
        return [fase] if fase["grupos"] else []


def _get_timeline_logs(impl_id):
    logs_timeline = query_db(
        """ SELECT tl.*, COALESCE(p.nome, tl.usuario_cs) as usuario_nome 
            FROM timeline_log tl LEFT JOIN perfil_usuario p ON tl.usuario_cs = p.usuario 
            WHERE tl.implantacao_id = %s ORDER BY tl.data_criacao DESC """,
        (impl_id,),
    )
    for log in logs_timeline:
        log["data_criacao_fmt_dt_hr"] = format_date_br(log.get("data_criacao"), True)
    return logs_timeline


def get_implantacao_details(impl_id, usuario_cs_email, user_perfil):
    """
    Busca, processa e valida todos os dados para a página de detalhes da implantação.
    Levanta um ValueError se o acesso for negado.
    """

    implantacao, is_manager = _get_implantacao_and_validate_access(
        impl_id, usuario_cs_email, user_perfil
    )
    implantacao = _format_implantacao_dates(implantacao)

    progresso, _, _ = _get_progress(impl_id)

    is_owner = implantacao.get("usuario_cs") == usuario_cs_email
    
    # Busca a hierarquia completa (Fases -> Grupos -> Tarefas -> Subtarefas)
    try:
        fases_hierarquia = _get_hierarquia_implantacao(impl_id)
    except Exception:
        fases_hierarquia = []

    try:
        logs_timeline = _get_timeline_logs(impl_id)
    except Exception:
        logs_timeline = []

    nome_usuario_logado = user_perfil.get("nome", usuario_cs_email)

    all_cs_users = []
    if is_manager:
        all_cs_users = query_db(
            "SELECT usuario, nome FROM perfil_usuario WHERE perfil_acesso IS NOT NULL AND perfil_acesso != '' ORDER BY nome"
        )
        all_cs_users = all_cs_users if all_cs_users is not None else []

    return {
        "user_info": g.user,
        "implantacao": implantacao,
        "fases_hierarquia": fases_hierarquia,
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
    }
