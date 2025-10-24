from .db import query_db, execute_db
from .constants import (
    CHECKLIST_OBRIGATORIO_ITEMS, MODULO_OBRIGATORIO, 
    TAREFAS_TREINAMENTO_PADRAO, MODULO_PENDENCIAS
)
from .utils import format_date_iso_for_json

# --- Camada de Serviço (Business Logic) ---

def logar_timeline(implantacao_id, usuario_cs, tipo_evento, detalhes):
    """Registra um evento na timeline de uma implantação."""
    try:
        execute_db(
            "INSERT INTO timeline_log (implantacao_id, usuario_cs, tipo_evento, detalhes) VALUES (%s, %s, %s, %s)",
            (implantacao_id, usuario_cs, tipo_evento, detalhes)
        )
    except Exception as e:
        print(f"AVISO/ERRO: Falha ao logar evento '{tipo_evento}' para implantação {implantacao_id}: {e}")

def _create_default_tasks(impl_id):
    """Cria as tarefas padrão (Obrigatórias e Treinamento) para uma nova implantação."""
    tasks_added = 0
    # Tarefas Obrigatórias
    for i, tarefa_nome in enumerate(CHECKLIST_OBRIGATORIO_ITEMS, 1):
        execute_db(
            "INSERT INTO tarefas (implantacao_id, tarefa_pai, tarefa_filho, ordem, tag) VALUES (%s, %s, %s, %s, %s)",
            (impl_id, MODULO_OBRIGATORIO, tarefa_nome, i, 'Ação interna')
        )
        tasks_added += 1
    
    # Tarefas de Treinamento
    for modulo, tarefas_info in TAREFAS_TREINAMENTO_PADRAO.items():
        for i, tarefa_info in enumerate(tarefas_info, 1):
            execute_db(
                "INSERT INTO tarefas (implantacao_id, tarefa_pai, tarefa_filho, ordem, tag) VALUES (%s, %s, %s, %s, %s)",
                (impl_id, modulo, tarefa_info['nome'], i, tarefa_info.get('tag', ''))
            )
            tasks_added += 1
    return tasks_added

def _get_progress(impl_id):
    """Calcula o progresso de uma implantação (excluindo pendências)."""
    counts = query_db(
        "SELECT COUNT(*) as total, SUM(CASE WHEN concluida THEN 1 ELSE 0 END) as done "
        "FROM tarefas WHERE implantacao_id = %s",
        (impl_id,), 
        one=True
    )
    total, done = (counts.get('total') or 0), (counts.get('done') or 0)
    return int(round((done / total) * 100)) if total > 0 else 0, total, done

def auto_finalizar_implantacao(impl_id, usuario_cs_email):
    """
    Verifica se todas as tarefas (exceto pendências) estão concluídas
    e, em caso afirmativo, finaliza a implantação.
    """
    pending_tasks = query_db(
        "SELECT COUNT(*) as total FROM tarefas "
        "WHERE implantacao_id = %s AND concluida = %s AND tarefa_pai != %s",
        (impl_id, 0, MODULO_PENDENCIAS),
        one=True
    )
    
    if pending_tasks and pending_tasks.get('total', 0) == 0:
        impl_status = query_db(
            "SELECT status, nome_empresa FROM implantacoes WHERE id = %s",
            (impl_id,),
            one=True
        )
        if impl_status and impl_status.get('status') == 'andamento':
            execute_db(
                "UPDATE implantacoes SET status = 'finalizada', data_finalizacao = CURRENT_TIMESTAMP WHERE id = %s",
                (impl_id,)
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
                log_final['data_criacao'] = format_date_iso_for_json(log_final.get('data_criacao'))
                return True, log_final
    return False, None

def get_dashboard_data(user_email):
    """Busca e processa todos os dados para o dashboard do usuário."""
    impl_list = query_db(
        """
        SELECT *, 
               CASE 
                   WHEN status = 'andamento' OR status = 'parada' 
                   THEN (CAST(strftime('%J', CURRENT_TIMESTAMP) AS REAL) - CAST(strftime('%J', data_criacao) AS REAL))
                   ELSE NULL 
               END AS dias_passados 
        FROM implantacoes 
        WHERE usuario_cs = %s 
        ORDER BY data_criacao DESC
        """,
        (user_email,)
    )

    dashboard_data = {
        'andamento': [], 'atrasadas': [], 'futuras': [], 
        'finalizadas': [], 'paradas': []
    }
    metrics = {
        'impl_andamento_total': 0, 'implantacoes_atrasadas': 0, 
        'implantacoes_futuras': 0, 'impl_finalizadas': 0, 'impl_paradas': 0
    }
    
    # Otimização: Buscar todas as tarefas de uma vez
    all_tasks = query_db(
        "SELECT implantacao_id, concluida FROM tarefas "
        "WHERE implantacao_id IN (SELECT id FROM implantacoes WHERE usuario_cs = %s)",
        (user_email,)
    )
    tasks_by_impl = {}
    for task in all_tasks:
        tasks_by_impl.setdefault(task['implantacao_id'], []).append(task)
    
    for impl in impl_list:
        impl_id = impl['id']
        status = impl['status']
        
        # Formata datas para os modais
        impl['data_criacao_iso'] = format_date_iso_for_json(impl.get('data_criacao'), only_date=True)
        impl['data_inicio_producao_iso'] = format_date_iso_for_json(impl.get('data_inicio_producao'), only_date=True)
        impl['data_final_implantacao_iso'] = format_date_iso_for_json(impl.get('data_final_implantacao'), only_date=True)
        
        # Calcula progresso
        impl_tasks = tasks_by_impl.get(impl_id, [])
        total_tasks = len(impl_tasks)
        done_tasks = sum(1 for t in impl_tasks if t['concluida'])
        impl['progresso'] = int(round((done_tasks / total_tasks) * 100)) if total_tasks > 0 else 0
        
        # Classifica a implantação
        if status == 'finalizada':
            dashboard_data['finalizadas'].append(impl)
            metrics['impl_finalizadas'] += 1
        elif status == 'parada':
            dashboard_data['paradas'].append(impl)
            metrics['impl_paradas'] += 1
        elif status == 'futura' or impl['tipo'] == 'futura':
            dashboard_data['futuras'].append(impl)
            metrics['implantacoes_futuras'] += 1
        else: # andamento
            dias_passados = int(float(impl.get('dias_passados', 0) or 0))
            impl['dias_passados'] = dias_passados
            
            if dias_passados > 25:
                dashboard_data['atrasadas'].append(impl)
                metrics['implantacoes_atrasadas'] += 1
            else:
                dashboard_data['andamento'].append(impl)
            
            metrics['impl_andamento_total'] += 1 # Conta 'andamento' e 'atrasadas'

    # Atualiza o perfil com as métricas calculadas
    execute_db(
        """
        UPDATE perfil_usuario 
        SET impl_andamento_total = %s, implantacoes_atrasadas = %s, 
            impl_finalizadas = %s, impl_paradas = %s 
        WHERE usuario = %s
        """,
        (metrics['impl_andamento_total'], metrics['implantacoes_atrasadas'], 
         metrics['impl_finalizadas'], metrics['impl_paradas'], user_email)
    )
    
    return dashboard_data, metrics