from .db import query_db, execute_db 
from .constants import (
    CHECKLIST_OBRIGATORIO_ITEMS, MODULO_OBRIGATORIO, 
    TAREFAS_TREINAMENTO_PADRAO, MODULO_PENDENCIAS,
    PERFIL_ADMIN, PERFIL_GERENTE, PERFIL_COORDENADOR
)
from .utils import format_date_iso_for_json

# NOVO: Importa logar_timeline do DB
from .db import logar_timeline

# --- Camada de Serviço (Business Logic) ---

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
    """Busca e processa todos os dados APENAS para o dashboard do usuário logado."""
    
    # Esta função é para a visão INDIVIDUAL (carteira do CS)
    
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


def get_analytics_data(target_cs_email=None, target_status=None):
    """Busca e processa dados de TODA a carteira (ou filtrada) para o módulo Gerencial."""
    
    query = """
        SELECT i.*, 
               p.nome as cs_nome, p.cargo as cs_cargo, p.perfil_acesso as cs_perfil,
               (CAST(strftime('%J', i.data_finalizacao) AS REAL) - CAST(strftime('%J', i.data_criacao) AS REAL)) AS tma_dias 
        FROM implantacoes i
        LEFT JOIN perfil_usuario p ON i.usuario_cs = p.usuario
        WHERE 1=1 
    """
    args = []
    
    # Aplica filtro por CS
    if target_cs_email:
        query += " AND i.usuario_cs = %s "
        args.append(target_cs_email)
        
    # Aplica filtro por Status
    if target_status and target_status != 'todas':
        # Trata 'atrasadas' como um status que precisa de cálculo adicional
        if target_status == 'atrasadas_status':
            # Filtra por status 'andamento' e dias > 25. É complexo fazer isso 100% no SQLite
            # Mantemos o filtro por status normal para simplicidade na primeira versão
            query += " AND i.status = 'andamento' "
        else:
            query += " AND i.status = %s "
            args.append(target_status)
    
    # Ordem por nome da empresa ou CS
    query += " ORDER BY i.nome_empresa "
    
    # 1. Busca implantações filtradas
    impl_list = query_db(query, tuple(args))
    
    # 2. Busca todas as tarefas para cálculo de progresso
    all_tasks = query_db("SELECT implantacao_id, concluida, tarefa_pai FROM tarefas")
    
    tasks_by_impl = {}
    for task in all_tasks:
        tasks_by_impl.setdefault(task['implantacao_id'], []).append(task)
        
    # 3. Processamento e Agregação
    
    # Lista de todos os CS no sistema (para relatar mesmo aqueles sem implantações)
    all_cs_profiles = query_db("SELECT usuario, nome, cargo, perfil_acesso FROM perfil_usuario")
    cs_metrics = {p['usuario']: {
        'email': p['usuario'], 'nome': p['nome'] or p['usuario'], 'cargo': p['cargo'] or 'N/A', 
        'perfil': p['perfil_acesso'] or 'Nenhum', 'impl_total': 0, 'impl_andamento': 0, 
        'impl_finalizadas': 0, 'impl_paradas': 0, 'tma_sum': 0, 'total_tasks': 0, 
        'done_tasks': 0, 'progresso_medio': 0, 'tma_medio': 'N/A', 'motivos_parada': {}
    } for p in all_cs_profiles}
    
    # Agregações Globais
    total_impl_global = len(impl_list) # Total após filtros
    total_finalizadas = 0
    total_atrasadas_status = 0
    total_paradas = 0
    tma_dias_sum = 0
    
    # Agregação de Motivos de Parada
    motivos_parada_global = {}
    
    for impl in impl_list:
        impl_id = impl['id']
        cs_email = impl['usuario_cs']
        status = impl['status']
        
        # Garante que o CS existe no dicionário (caso a lista de implantações contenha um CS novo)
        if cs_email not in cs_metrics:
             cs_metrics[cs_email] = {'email': cs_email, 'nome': impl.get('cs_nome') or cs_email, 'cargo': impl.get('cs_cargo') or 'N/A', 'perfil': impl.get('cs_perfil') or 'Nenhum', 'impl_total': 0, 'impl_andamento': 0, 'impl_finalizadas': 0, 'impl_paradas': 0, 'tma_sum': 0, 'total_tasks': 0, 'done_tasks': 0, 'progresso_medio': 0, 'tma_medio': 'N/A', 'motivos_parada': {}}

        
        metrics = cs_metrics[cs_email]
        metrics['impl_total'] += 1

        # Cálculo de Progresso
        impl_tasks = tasks_by_impl.get(impl_id, [])
        total_tasks = len(impl_tasks)
        done_tasks = sum(1 for t in impl_tasks if t['concluida'])
        
        metrics['total_tasks'] += total_tasks
        metrics['done_tasks'] += done_tasks
        
        # Classificação e Agregação Global/CS
        if status == 'finalizada':
            total_finalizadas += 1
            metrics['impl_finalizadas'] += 1
            
            if impl['tma_dias'] is not None:
                tma_dias_sum += impl['tma_dias']
                metrics['tma_sum'] += impl['tma_dias']
                
        elif status == 'parada':
            total_paradas += 1
            metrics['impl_paradas'] += 1
            
            # Agregação de Motivos de Parada (Qualidade)
            motivo = impl.get('motivo_parada') or 'Motivo Não Especificado'
            motivos_parada_global[motivo] = motivos_parada_global.get(motivo, 0) + 1
            metrics['motivos_parada'][motivo] = metrics['motivos_parada'].get(motivo, 0) + 1
            
        elif status == 'andamento':
            metrics['impl_andamento'] += 1
            # Lógica de Atraso
            dias_passados = (query_db(
                "SELECT (CAST(strftime('%J', CURRENT_TIMESTAMP) AS REAL) - CAST(strftime('%J', data_criacao) AS REAL)) AS dias FROM implantacoes WHERE id = %s",
                (impl_id,), one=True
            ) or {}).get('dias', 0)
            
            if dias_passados > 25:
                total_atrasadas_status += 1

    # Finalização das Métricas do CS (Removendo CSs sem implantações se houver filtro)
    final_cs_metrics = {}
    for email, metrics in cs_metrics.items():
        if metrics['impl_total'] > 0 or not target_cs_email: # Inclui CSs sem implantação se não houver filtro
            
            if metrics['impl_finalizadas'] > 0:
                metrics['tma_medio'] = round(metrics['tma_sum'] / metrics['impl_finalizadas'], 1)
            else:
                metrics['tma_medio'] = 'N/A'
                
            if metrics['total_tasks'] > 0:
                metrics['progresso_medio'] = int(round((metrics['done_tasks'] / metrics['total_tasks']) * 100))
            else:
                metrics['progresso_medio'] = 0
            
            final_cs_metrics[email] = metrics

    # Finalização das Métricas Globais (Atualiza o total de andamento pós-filtro)
    global_metrics = {
        'total_impl': total_impl_global,
        'total_finalizadas': total_finalizadas,
        'total_andamento': sum(m['impl_andamento'] for m in final_cs_metrics.values()),
        'total_paradas': total_paradas,
        'total_atrasadas_status': total_atrasadas_status,
        'global_tma': round(tma_dias_sum / total_finalizadas, 1) if total_finalizadas > 0 else 'N/A',
        'motivos_parada': motivos_parada_global
    }
    
    return global_metrics, list(final_cs_metrics.values())