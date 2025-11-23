

from flask import g
from ..db import query_db, execute_db, logar_timeline


from ..task_definitions import (
    CHECKLIST_OBRIGATORIO_ITEMS, MODULO_OBRIGATORIO,
    TAREFAS_TREINAMENTO_PADRAO, MODULO_PENDENCIAS, TASK_TIPS
)

from ..dominio.hierarquia_service import get_hierarquia_implantacao
from ..constants import (
    PERFIS_COM_GESTAO, 
    JUSTIFICATIVAS_PARADA, CARGOS_RESPONSAVEL, NIVEIS_RECEITA, 
    SEGUIMENTOS_LIST, TIPOS_PLANOS, MODALIDADES_LIST,
    HORARIOS_FUNCIONAMENTO, FORMAS_PAGAMENTO, SISTEMAS_ANTERIORES,
    RECORRENCIA_USADA, SIM_NAO_OPTIONS
)

from ..utils import format_date_iso_for_json, format_date_br
from datetime import datetime
from collections import OrderedDict 

def _create_default_tasks(impl_id):
    """Cria as tarefas padrão (Obrigatórias e Treinamento) para uma nova implantação."""
    tasks_added = 0

    for i, tarefa_nome in enumerate(CHECKLIST_OBRIGATORIO_ITEMS, 1):
        execute_db(
            "INSERT INTO tarefas (implantacao_id, tarefa_pai, tarefa_filho, ordem, tag) VALUES (%s, %s, %s, %s, %s)",
            (impl_id, MODULO_OBRIGATORIO, tarefa_nome, i, 'Ação interna')
        )
        tasks_added += 1

    for modulo, tarefas_info in TAREFAS_TREINAMENTO_PADRAO.items():
        if tarefas_info:
            for i, tarefa_info in enumerate(tarefas_info, 1):
                execute_db(
                    "INSERT INTO tarefas (implantacao_id, tarefa_pai, tarefa_filho, ordem, tag) VALUES (%s, %s, %s, %s, %s)",
                    (impl_id, modulo, tarefa_info['nome'], i, tarefa_info.get('tag', ''))
                )
                tasks_added += 1
        else:
            execute_db(
                "INSERT INTO tarefas (implantacao_id, tarefa_pai, tarefa_filho, ordem, tag, concluida) VALUES (%s, %s, %s, %s, %s, %s)",
                (impl_id, modulo, '(Módulo sem tarefas definidas)', 1, 'Informação', True)
            )
            tasks_added += 1
    return tasks_added

def _get_progress(impl_id):
    try:
        fases_exist = query_db("SELECT id FROM fases WHERE implantacao_id = %s LIMIT 1", (impl_id,), one=True)
    except Exception:
        fases_exist = None
    if fases_exist:
        leg = query_db(
            """
            SELECT COUNT(*) as total, SUM(CASE WHEN concluida THEN 1 ELSE 0 END) as done
            FROM tarefas WHERE implantacao_id = %s AND (tarefa_pai IS NULL OR tarefa_pai NOT IN (%s, %s))
            """,
            (impl_id, MODULO_OBRIGATORIO, MODULO_PENDENCIAS), one=True
        ) or {}
        sub = query_db(
            """
            SELECT COUNT(s.id) as total, SUM(CASE WHEN s.concluido THEN 1 ELSE 0 END) as done
            FROM subtarefas_h s
            JOIN tarefas_h th ON s.tarefa_id = th.id
            JOIN grupos g ON th.grupo_id = g.id
            JOIN fases f ON g.fase_id = f.id
            WHERE f.implantacao_id = %s
            """,
            (impl_id,), one=True
        ) or {}
        th_no = query_db(
            """
            SELECT COUNT(th.id) as total,
                   SUM(CASE WHEN LOWER(COALESCE(th.status,'')) = 'concluida' THEN 1 ELSE 0 END) as done
            FROM tarefas_h th
            LEFT JOIN subtarefas_h s ON s.tarefa_id = th.id
            JOIN grupos g ON th.grupo_id = g.id
            JOIN fases f ON g.fase_id = f.id
            WHERE f.implantacao_id = %s AND s.id IS NULL
            """,
            (impl_id,), one=True
        ) or {}
        total = int(leg.get('total', 0) or 0) + int(sub.get('total', 0) or 0) + int(th_no.get('total', 0) or 0)
        done = int(leg.get('done', 0) or 0) + int(sub.get('done', 0) or 0) + int(th_no.get('done', 0) or 0)
        return int(round((done / total) * 100)) if total > 0 else 100, total, done
    counts = query_db(
        "SELECT COUNT(*) as total, SUM(CASE WHEN concluida THEN 1 ELSE 0 END) as done FROM tarefas WHERE implantacao_id = %s AND (tarefa_pai IS NULL OR tarefa_pai NOT IN (%s, %s))",
        (impl_id, MODULO_OBRIGATORIO, MODULO_PENDENCIAS), one=True
    )
    total = counts.get('total', 0) if counts else 0
    done = counts.get('done', 0) if counts else 0
    done = int(done) if done is not None else 0
    return int(round((done / total) * 100)) if total > 0 else 100, total, done


def auto_finalizar_implantacao(impl_id, usuario_cs_email):
    """
    Verifica se todas as tarefas (exceto pendências) estão concluídas
    e, em caso afirmativo, finaliza a implantação.
    """

    pending_tasks = query_db(
        "SELECT COUNT(*) as total FROM tarefas "
        "WHERE implantacao_id = %s AND concluida = %s AND (tarefa_pai != %s OR tarefa_pai IS NULL)",
        (impl_id, 0, MODULO_PENDENCIAS),
        one=True
    )

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

def _get_tarefas_and_comentarios(impl_id, is_owner=False, is_manager=False):
    tarefas_raw = query_db("SELECT * FROM tarefas WHERE implantacao_id = %s ORDER BY tarefa_pai, ordem", (impl_id,))
    comentarios_raw = query_db(
        """ SELECT c.*, COALESCE(p.nome, c.usuario_cs) as usuario_nome 
            FROM comentarios c LEFT JOIN perfil_usuario p ON c.usuario_cs = p.usuario 
            WHERE c.tarefa_id IN (SELECT id FROM tarefas WHERE implantacao_id = %s) 
            ORDER BY c.data_criacao DESC """, (impl_id,)
    )

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
        if modulo == MODULO_OBRIGATORIO:
            tarefas_agrupadas_obrigatorio.setdefault(modulo, []).append(t)
        elif modulo == MODULO_PENDENCIAS:
            tarefas_agrupadas_pendencias.setdefault(modulo, []).append(t)
        else:
            tarefas_agrupadas_treinamento.setdefault(modulo, []).append(t)

    try:
        fases_raw = query_db("SELECT id, nome, ordem FROM fases WHERE implantacao_id = %s ORDER BY ordem DESC", (impl_id,)) or []
    except Exception:
        fases_raw = []
    if fases_raw:
        tarefas_agrupadas_treinamento = OrderedDict()
        todos_modulos_temp = set()
        for fase in fases_raw:
            grupos_raw = query_db("SELECT id, nome FROM grupos WHERE fase_id = %s", (fase['id'],)) or []
            for grupo in grupos_raw:
                modulo_nome = grupo.get('nome') or f"Grupo {grupo.get('id')}"
                todos_modulos_temp.add(modulo_nome)
                tarefas_h_raw = query_db("SELECT * FROM tarefas_h WHERE grupo_id = %s", (grupo['id'],)) or []
                ordem_c = 1
                for th in tarefas_h_raw:
                    subs_raw = query_db("SELECT * FROM subtarefas_h WHERE tarefa_id = %s", (th['id'],)) or []
                    if subs_raw:
                        for sub in subs_raw:
                            tarefas_agrupadas_treinamento.setdefault(modulo_nome, []).append({
                                'id': sub['id'],
                                'tarefa_filho': sub.get('nome'),
                                'concluida': bool(sub.get('concluido')), 
                                'tag': '',
                                'ordem': sub.get('ordem', ordem_c),
                                'comentarios': [],
                                'toggle_url': f"/api/toggle_subtarefa_h/{sub['id']}"
                            })
                            tarefas_agrupadas_treinamento[modulo_nome].sort(key=lambda x: x.get('ordem', 0))
                            tarefas_agrupadas_treinamento[modulo_nome][-1]['delete_url'] = f"/api/excluir_subtarefa_h/{sub['id']}"
                            ordem_c += 1
                    else:
                        concl = True if (th.get('status') or '').lower() == 'concluida' else False
                        tarefas_agrupadas_treinamento.setdefault(modulo_nome, []).append({
                            'id': th['id'],
                            'tarefa_filho': th.get('nome'),
                            'concluida': concl,
                            'tag': '',
                            'ordem': th.get('ordem', ordem_c),
                            'comentarios': [],
                            'toggle_url': f"/api/toggle_tarefa_h/{th['id']}"
                        })
                        tarefas_agrupadas_treinamento[modulo_nome].sort(key=lambda x: x.get('ordem', 0))
                        tarefas_agrupadas_treinamento[modulo_nome][-1]['delete_url'] = f"/api/excluir_tarefa_h/{th['id']}"
                        ordem_c += 1

    ordered_treinamento = OrderedDict()
    modulo_ordem_map = {}
    for modulo, lista in tarefas_agrupadas_treinamento.items():
        try:
            modulo_ordem_map[modulo] = min([t.get('ordem') or 0 for t in (lista or [])])
        except Exception:
            modulo_ordem_map[modulo] = 0
    for modulo in [k for k,  _ in sorted(modulo_ordem_map.items(), key=lambda x: (x[1], x[0]), reverse=True)]:
        ordered_treinamento[modulo] = tarefas_agrupadas_treinamento.get(modulo, [])

    if MODULO_OBRIGATORIO in todos_modulos_temp:
        try:
            todos_modulos_temp.remove(MODULO_OBRIGATORIO)
        except Exception:
            pass
    todos_modulos_lista = sorted(list(todos_modulos_temp))
    if MODULO_PENDENCIAS not in todos_modulos_lista:
        todos_modulos_lista.append(MODULO_PENDENCIAS)

    # Ordenação de módulos visíveis também segue a ordem derivada das tarefas (maior primeiro)
    todos_modulos_lista = sorted(list(todos_modulos_temp), key=lambda m: modulo_ordem_map.get(m, 0), reverse=True)
    if MODULO_PENDENCIAS not in todos_modulos_lista:
        todos_modulos_lista.append(MODULO_PENDENCIAS)
    
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
    
    # Buscar hierarquia completa (novo modelo)
    hierarquia = get_hierarquia_implantacao(impl_id)

    logs_timeline = _get_timeline_logs(impl_id)

    nome_usuario_logado = user_perfil.get('nome', usuario_cs_email)

    all_cs_users = []
    if is_manager:
        all_cs_users = query_db("SELECT usuario, nome FROM perfil_usuario WHERE perfil_acesso IS NOT NULL AND perfil_acesso != '' ORDER BY nome")
        all_cs_users = all_cs_users if all_cs_users is not None else []


    return {
        'user_info': g.user,
        'implantacao': implantacao,
        'hierarquia': hierarquia,
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
        'is_manager': is_manager,
        'tt': TASK_TIPS
    }
