\
\

from flask import g
from ..db import query_db, execute_db, logar_timeline

\
\
from ..task_definitions import (
    CHECKLIST_OBRIGATORIO_ITEMS, MODULO_OBRIGATORIO,
    TAREFAS_TREINAMENTO_PADRAO, MODULO_PENDENCIAS
)
\
from ..constants import (
    PERFIS_COM_GESTAO, 
    JUSTIFICATIVAS_PARADA, CARGOS_RESPONSAVEL, NIVEIS_RECEITA, 
    SEGUIMENTOS_LIST, TIPOS_PLANOS, MODALIDADES_LIST,
    HORARIOS_FUNCIONAMENTO, FORMAS_PAGAMENTO, SISTEMAS_ANTERIORES,
    RECORRENCIA_USADA, SIM_NAO_OPTIONS
)
\

from ..utils import format_date_iso_for_json, format_date_br
from datetime import datetime
from collections import OrderedDict 

\

def _create_default_tasks(impl_id):
    """Cria as tarefas padrão (Obrigatórias e Treinamento) para uma nova implantação."""
    tasks_added = 0
    \
    for i, tarefa_nome in enumerate(CHECKLIST_OBRIGATORIO_ITEMS, 1):
        execute_db(
            "INSERT INTO tarefas (implantacao_id, tarefa_pai, tarefa_filho, ordem, tag) VALUES (%s, %s, %s, %s, %s)",
            (impl_id, MODULO_OBRIGATORIO, tarefa_nome, i, 'Ação interna')
        )
        tasks_added += 1

    for modulo, tarefas_info in TAREFAS_TREINAMENTO_PADRAO.items():
        for i, tarefa_info in enumerate(tarefas_info, 1):
            execute_db(
                "INSERT INTO tarefas (implantacao_id, tarefa_pai, tarefa_filho, ordem, tag) VALUES (%s, %s, %s, %s, %s)",
                (impl_id, modulo, tarefa_info['nome'], i, tarefa_info.get('tag', ''))
            )
            tasks_added += 1
    return tasks_added

def _get_progress(impl_id):
    """Calcula o progresso de uma implantação (incluindo todas as tarefas)."""
    counts = query_db(
        "SELECT COUNT(*) as total, SUM(CASE WHEN concluida THEN 1 ELSE 0 END) as done "
        "FROM tarefas WHERE implantacao_id = %s",
        (impl_id,),
        one=True
    )
    total = counts.get('total', 0) if counts else 0
    done = counts.get('done', 0) if counts else 0
    done = int(done) if done is not None else 0

    return int(round((done / total) * 100)) if total > 0 else 0, total, done


def auto_finalizar_implantacao(impl_id, usuario_cs_email):
    """
    Verifica se todas as tarefas (exceto pendências) estão concluídas
    e, em caso afirmativo, finaliza a implantação.
    """
    \
    pending_tasks = query_db(
        "SELECT COUNT(*) as total FROM tarefas "
        "WHERE implantacao_id = %s AND concluida = %s AND (tarefa_pai != %s OR tarefa_pai IS NULL)",
        (impl_id, 0, MODULO_PENDENCIAS),
        one=True
    )

    \
    total_nonpend_tasks = query_db(
        "SELECT COUNT(*) as total FROM tarefas "
        "WHERE implantacao_id = %s AND (tarefa_pai != %s OR tarefa_pai IS NULL)",
        (impl_id, MODULO_PENDENCIAS),
        one=True
    )

    total_nonpend = total_nonpend_tasks.get('total', 0) if total_nonpend_tasks else 0
    total_pendentes = pending_tasks.get('total', 0) if pending_tasks else 0

    if total_nonpend > 0 and total_pendentes == 0:
        impl_status = query_db(
            "SELECT status, nome_empresa FROM implantacoes WHERE id = %s",
            (impl_id,),
            one=True
        )
        if impl_status and impl_status.get('status') == 'andamento':
            agora = datetime.now() 
            execute_db(
                "UPDATE implantacoes SET status = 'finalizada', data_finalizacao = %s WHERE id = %s",
                (agora, impl_id)
            )
            detalhe = f'Implantação "{impl_status.get("nome_empresa", "N/A")}" auto-finalizada.'
            logar_timeline(impl_id, usuario_cs_email, 'auto_finalizada', detalhe)

            perfil = query_db("SELECT nome FROM perfil_usuario WHERE usuario = %s", (usuario_cs_email,), one=True)
            nome = perfil.get('nome') if perfil else usuario_cs_email

            log_final = query_db(
                "SELECT *, %s as usuario_nome FROM timeline_log "
                "WHERE implantacao_id = %s AND tipo_evento = 'auto_finalizada' "
                "ORDER BY id DESC LIMIT 1",
                (nome, impl_id),
                one=True
            )
            if log_final:
                if not isinstance(log_final, dict):
                    log_final = dict(log_final)
                log_final['data_criacao'] = format_date_iso_for_json(log_final.get('data_criacao'))
                return True, log_final
            else:
                return True, None
    return False, None


def _get_implantacao_and_validate_access(impl_id, usuario_cs_email, user_perfil):
    user_perfil_acesso = user_perfil.get('perfil_acesso') if user_perfil else None
    implantacao = query_db("SELECT * FROM implantacoes WHERE id = %s", (impl_id,), one=True)
    
    if not implantacao:
        raise ValueError('Implantação não encontrada.')

    is_owner = implantacao.get('usuario_cs') == usuario_cs_email
    is_manager = user_perfil_acesso in PERFIS_COM_GESTAO

    if not is_owner and not is_manager:
        if implantacao.get('status') == 'nova':
             raise ValueError('Esta implantação ainda não foi iniciada.')
        else:
            raise ValueError('Implantação não encontrada ou não pertence a você.')

    if implantacao.get('status') == 'nova' and is_owner and not is_manager:
         raise ValueError('Esta implantação está aguardando início. Use os botões "Iniciar" ou "Início Futuro" no dashboard.')

    return implantacao, is_manager

def _format_implantacao_dates(implantacao):
    implantacao['data_criacao_fmt_dt_hr'] = format_date_br(implantacao.get('data_criacao'), True)
    implantacao['data_criacao_fmt_d'] = format_date_br(implantacao.get('data_criacao'), False)
    implantacao['data_inicio_efetivo_fmt_d'] = format_date_br(implantacao.get('data_inicio_efetivo'), False)
    implantacao['data_finalizacao_fmt_d'] = format_date_br(implantacao.get('data_finalizacao'), False)
    implantacao['data_inicio_producao_fmt_d'] = format_date_br(implantacao.get('data_inicio_producao'), False)
    implantacao['data_final_implantacao_fmt_d'] = format_date_br(implantacao.get('data_final_implantacao'), False)
    implantacao['data_criacao_iso'] = format_date_iso_for_json(implantacao.get('data_criacao'), only_date=True)
    implantacao['data_inicio_efetivo_iso'] = format_date_iso_for_json(implantacao.get('data_inicio_efetivo'), only_date=True)
    implantacao['data_inicio_producao_iso'] = format_date_iso_for_json(implantacao.get('data_inicio_producao'), only_date=True)
    implantacao['data_final_implantacao_iso'] = format_date_iso_for_json(implantacao.get('data_final_implantacao'), only_date=True)
    implantacao['data_inicio_previsto_fmt_d'] = format_date_br(implantacao.get('data_inicio_previsto'), False)
    return implantacao

def get_implantacao_details(impl_id, usuario_cs_email, user_perfil):
    """
    Busca, processa e valida todos os dados para a página de detalhes da implantação.
    Levanta um ValueError se o acesso for negado.
    """
    
    implantacao, is_manager = _get_implantacao_and_validate_access(impl_id, usuario_cs_email, user_perfil)
    implantacao = _format_implantacao_dates(implantacao)

    progresso, _, _ = _get_progress(impl_id)

def _get_tarefas_and_comentarios(impl_id, is_owner=False, is_manager=False):
    tarefas_raw = query_db("SELECT * FROM tarefas WHERE implantacao_id = %s ORDER BY tarefa_pai, ordem", (impl_id,))
    comentarios_raw = query_db(
        """ SELECT c.*, COALESCE(p.nome, c.usuario_cs) as usuario_nome 
            FROM comentarios c LEFT JOIN perfil_usuario p ON c.usuario_cs = p.usuario 
            WHERE c.tarefa_id IN (SELECT id FROM tarefas WHERE implantacao_id = %s) 
            ORDER BY c.data_criacao DESC """, (impl_id,)
    )

    \
    if not (is_owner or is_manager):
        comentarios_raw = [c for c in (comentarios_raw or []) if (c.get('visibilidade') != 'interno')]

    comentarios_por_tarefa = {}
    for c in comentarios_raw:
        c_formatado = {**c, 'data_criacao_fmt_d': format_date_br(c.get('data_criacao'))}
        comentarios_por_tarefa.setdefault(c['tarefa_id'], []).append(c_formatado)

    tarefas_agrupadas_treinamento = OrderedDict()
    tarefas_agrupadas_obrigatorio = OrderedDict()
    tarefas_agrupadas_pendencias = OrderedDict()
    todos_modulos_temp = set()

    for t in tarefas_raw:
        t['comentarios'] = comentarios_por_tarefa.get(t['id'], [])
        modulo = t['tarefa_pai']
        todos_modulos_temp.add(modulo)
        if modulo == MODULO_OBRIGATORIO: tarefas_agrupadas_obrigatorio.setdefault(modulo, []).append(t)
        elif modulo == MODULO_PENDENCIAS: tarefas_agrupadas_pendencias.setdefault(modulo, []).append(t)
        else: tarefas_agrupadas_treinamento.setdefault(modulo, []).append(t)

    ordered_treinamento = OrderedDict()
    for mp in TAREFAS_TREINAMENTO_PADRAO:
        if mp in tarefas_agrupadas_treinamento: ordered_treinamento[mp] = tarefas_agrupadas_treinamento.pop(mp)
    for mr in sorted(tarefas_agrupadas_treinamento.keys()): ordered_treinamento[mr] = tarefas_agrupadas_treinamento[mr]

    \
    if MODULO_OBRIGATORIO in todos_modulos_temp:
        try:
            todos_modulos_temp.remove(MODULO_OBRIGATORIO)
        except Exception:
            pass
    todos_modulos_lista = sorted(list(todos_modulos_temp))
    if MODULO_PENDENCIAS not in todos_modulos_lista:
        todos_modulos_lista.append(MODULO_PENDENCIAS)

    preferred_order = [
        "Definição de carteira",
        "Welcome",
        "Estruturação de BD",
        "Importação de dados",
        "Módulo ADM",
        "Módulo Treino",
        "Módulo CRM",
        "Módulo Financeiro",
        "Conclusão",
        MODULO_PENDENCIAS,
    ]
    seen = set()
    ordered_mods = []
    for name in preferred_order:
        if name in todos_modulos_lista and name not in seen:
            ordered_mods.append(name)
            seen.add(name)
    for name in todos_modulos_lista:
        if name not in seen:
            ordered_mods.append(name)
            seen.add(name)
    todos_modulos_lista = ordered_mods
    
    return tarefas_agrupadas_obrigatorio, ordered_treinamento, tarefas_agrupadas_pendencias, todos_modulos_lista

def _get_timeline_logs(impl_id):
    logs_timeline = query_db(
        """ SELECT tl.*, COALESCE(p.nome, tl.usuario_cs) as usuario_nome 
            FROM timeline_log tl LEFT JOIN perfil_usuario p ON tl.usuario_cs = p.usuario 
            WHERE tl.implantacao_id = %s ORDER BY tl.data_criacao DESC """, (impl_id,)
    )
    for log in logs_timeline:
        log['data_criacao_fmt_dt_hr'] = format_date_br(log.get('data_criacao'), True)
    return logs_timeline

def get_implantacao_details(impl_id, usuario_cs_email, user_perfil):
    """
    Busca, processa e valida todos os dados para a página de detalhes da implantação.
    Levanta um ValueError se o acesso for negado.
    """
    
    implantacao, is_manager = _get_implantacao_and_validate_access(impl_id, usuario_cs_email, user_perfil)
    implantacao = _format_implantacao_dates(implantacao)

    progresso, _, _ = _get_progress(impl_id)

    is_owner = implantacao.get('usuario_cs') == usuario_cs_email
    tarefas_agrupadas_obrigatorio, ordered_treinamento, tarefas_agrupadas_pendencias, todos_modulos_lista = _get_tarefas_and_comentarios(impl_id, is_owner=is_owner, is_manager=is_manager)

    logs_timeline = _get_timeline_logs(impl_id)

    nome_usuario_logado = user_perfil.get('nome', usuario_cs_email)

    all_cs_users = []
    if is_manager:
        all_cs_users = query_db("SELECT usuario, nome FROM perfil_usuario WHERE perfil_acesso IS NOT NULL AND perfil_acesso != '' ORDER BY nome")
        all_cs_users = all_cs_users if all_cs_users is not None else []


    return {
        'user_info': g.user,
        'implantacao': implantacao,
        'tarefas_agrupadas_obrigatorio': tarefas_agrupadas_obrigatorio,
        'tarefas_agrupadas_treinamento': ordered_treinamento,
        'tarefas_agrupadas_pendencias': tarefas_agrupadas_pendencias,
        'todos_modulos': todos_modulos_lista,
        'modulo_pendencias_nome': MODULO_PENDENCIAS,
        'progresso_porcentagem': progresso,
        'nome_usuario_logado': nome_usuario_logado,
        'email_usuario_logado': usuario_cs_email,
        'justificativas_parada': JUSTIFICATIVAS_PARADA,
        'logs_timeline': logs_timeline,
        'cargos_responsavel': CARGOS_RESPONSAVEL,
        'NIVEIS_RECEITA': NIVEIS_RECEITA,
        'SEGUIMENTOS_LIST': SEGUIMENTOS_LIST,
        'TIPOS_PLANOS': TIPOS_PLANOS,
        'MODALIDADES_LIST': MODALIDADES_LIST,
        'HORARIOS_FUNCIONAMENTO': HORARIOS_FUNCIONAMENTO,
        'FORMAS_PAGAMENTO': FORMAS_PAGAMENTO,
        'SISTEMAS_ANTERIORES': SISTEMAS_ANTERIORES,
        'RECORRENCIA_USADA': RECORRENCIA_USADA,
        'SIM_NAO_OPTIONS': SIM_NAO_OPTIONS,
        'all_cs_users': all_cs_users,
        'is_manager': is_manager
    }

    logs_timeline = query_db(
        """ SELECT tl.*, COALESCE(p.nome, tl.usuario_cs) as usuario_nome 
            FROM timeline_log tl LEFT JOIN perfil_usuario p ON tl.usuario_cs = p.usuario 
            WHERE tl.implantacao_id = %s ORDER BY tl.data_criacao DESC """, (impl_id,)
    )
    for log in logs_timeline:
        log['data_criacao_fmt_dt_hr'] = format_date_br(log.get('data_criacao'), True)

    nome_usuario_logado = user_perfil.get('nome', usuario_cs_email)

    all_cs_users = []
    if is_manager:
        all_cs_users = query_db("SELECT usuario, nome FROM perfil_usuario WHERE perfil_acesso IS NOT NULL AND perfil_acesso != '' ORDER BY nome")
        all_cs_users = all_cs_users if all_cs_users is not None else []


    return {
        'user_info': g.user,
        'implantacao': implantacao,
        'tarefas_agrupadas_obrigatorio': tarefas_agrupadas_obrigatorio,
        'tarefas_agrupadas_treinamento': ordered_treinamento,
        'tarefas_agrupadas_pendencias': tarefas_agrupadas_pendencias,
        'todos_modulos': todos_modulos_lista,
        'modulo_pendencias_nome': MODULO_PENDENCIAS,
        'progresso_porcentagem': progresso,
        'nome_usuario_logado': nome_usuario_logado,
        'email_usuario_logado': usuario_cs_email,
        'justificativas_parada': JUSTIFICATIVAS_PARADA,
        'logs_timeline': logs_timeline,
        'cargos_responsavel': CARGOS_RESPONSAVEL,
        'NIVEIS_RECEITA': NIVEIS_RECEITA,
        'SEGUIMENTOS_LIST': SEGUIMENTOS_LIST,
        'TIPOS_PLANOS': TIPOS_PLANOS,
        'MODALIDADES_LIST': MODALIDADES_LIST,
        'HORARIOS_FUNCIONAMENTO': HORARIOS_FUNCIONAMENTO,
        'FORMAS_PAGAMENTO': FORMAS_PAGAMENTO,
        'SISTEMAS_ANTERIORES': SISTEMAS_ANTERIORES,
        'RECORRENCIA_USADA': RECORRENCIA_USADA,
        'SIM_NAO_OPTIONS': SIM_NAO_OPTIONS,
        'all_cs_users': all_cs_users,
        'is_manager': is_manager
    }