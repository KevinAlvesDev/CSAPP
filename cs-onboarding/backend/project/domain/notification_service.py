"""
Serviço de Notificações
Sistema completo de notificações para o implantador.
Inclui 9 tipos de notificações com regras de frequência específicas.
"""
from datetime import datetime, timedelta

from ..db import query_db
from ..config.logging_config import api_logger


def get_user_notifications(user_email):
    """
    Busca todas as notificações para um usuário.
    
    Args:
        user_email: Email do usuário
        
    Returns:
        dict: {
            'ok': bool,
            'notifications': list,
            'total': int,
            'timestamp': str
        }
    """
    notifications = []
    
    try:
        hoje = datetime.now()
        inicio_semana = hoje - timedelta(days=hoje.weekday())
        inicio_semana = inicio_semana.replace(hour=0, minute=0, second=0, microsecond=0)
        fim_hoje = hoje.replace(hour=23, minute=59, second=59)
        
        # 1. TAREFAS CRÍTICAS (atrasadas + vence hoje)
        notifications.extend(_get_critical_tasks(user_email, hoje, fim_hoje))
        
        # 2. IMPLANTAÇÕES PARADAS (a cada 7 dias)
        notifications.extend(_get_stopped_implementations(user_email, hoje))
        
        # 3. TAREFAS URGENTES (vence em 1-2 dias)
        notifications.extend(_get_urgent_tasks(user_email, hoje, fim_hoje))
        
        # 4. Implantações futuras (7 dias)
        notifications.extend(_get_upcoming_future(user_email, hoje))
        
        # 5. Largada Falsa (NOVO)
        notifications.extend(_get_false_start(user_email, hoje))
        
        # 6. Estagnação Silenciosa (NOVO)
        notifications.extend(_get_silent_stagnation(user_email, hoje))
        
        # 7. Ritmo Lento (NOVO)
        notifications.extend(_get_slow_pace(user_email, hoje))
        
        # 8. Sem previsão
        notifications.extend(_get_no_forecast(user_email, hoje))
        
        # 9. Reta Final / Sprint (NOVO)
        notifications.extend(_get_final_sprint(user_email))
        
        # 10. Tarefas próximas
        notifications.extend(_get_upcoming_tasks(user_email, hoje))
        
        # 11. Novas aguardando
        notifications.extend(_get_new_waiting(user_email))
        
        # 12. Resumo Semanal
        notifications.extend(_get_weekly_summary(user_email, hoje))
        
        # 13. Concluídas na semana
        notifications.extend(_get_completed_this_week(user_email, inicio_semana))
        
        # Ordenar por prioridade e limitar
        notifications.sort(key=lambda x: x['priority'])
        
        return {
            'ok': True,
            'notifications': notifications[:20],  # Aumentei limite para 20
            'total': len(notifications),
            'timestamp': hoje.isoformat()
        }
        
    except Exception as e:
        api_logger.error(f"Erro ao buscar notificações: {e}", exc_info=True)
        return {'ok': False, 'error': 'Erro ao buscar notificações', 'notifications': []}


def _get_false_start(user_email, hoje):
    """
    Largada Falsa: Implantação criada há mais de 5 dias, ainda 'nova' ou sem progresso.
    Priority: 2 (Alto Risco)
    """
    notifications = []
    limite_criacao = hoje - timedelta(days=5)
    
    sql = """
        SELECT id, nome_empresa, data_criacao 
        FROM implantacoes 
        WHERE usuario_cs = %s 
        AND status IN ('nova', 'andamento')
        AND data_criacao < %s
        AND (
            SELECT COUNT(*) FROM checklist_items 
            WHERE implantacao_id = implantacoes.id 
            AND completed = TRUE
        ) = 0
    """
    results = query_db(sql, (user_email, limite_criacao)) or []
    
    for row in results:
        if isinstance(row, dict):
            dias_criacao = (hoje - _parse_datetime(row['data_criacao'])).days
            notifications.append({
                'type': 'danger',
                'priority': 2,
                'title': f"🚦 {row['nome_empresa']}",
                'message': f"Criada há {dias_criacao} dias e nenhuma tarefa concluída. Engajamento necessário!",
                'action_url': f"/implantacao/{row['id']}"
            })
    return notifications


def _get_silent_stagnation(user_email, hoje):
    """
    Estagnação Silenciosa: Em andamento, mas sem registros na timeline há 4+ dias.
    Priority: 3 (Risco Médio)
    """
    notifications = []
    limite = hoje - timedelta(days=4)
    
    sql = """
        SELECT i.id, i.nome_empresa, MAX(tl.data_criacao) as ultima_interacao
        FROM implantacoes i
        LEFT JOIN timeline_log tl ON tl.implantacao_id = i.id
        WHERE i.usuario_cs = %s
        AND i.status = 'andamento'
        GROUP BY i.id
        HAVING MAX(tl.data_criacao) < %s OR MAX(tl.data_criacao) IS NULL
    """
    results = query_db(sql, (user_email, limite)) or []
    
    for row in results:
        if isinstance(row, dict):
            ultima_interacao = row.get('ultima_interacao')
            if ultima_interacao:
                dias = (hoje - _parse_datetime(ultima_interacao)).days
            else:
                dias = "vários"
                
            notifications.append({
                'type': 'warning',
                'priority': 3,
                'title': f"👻 {row['nome_empresa']}",
                'message': f"Sem nenhuma atividade registrada há {dias} dias. O cliente sumiu?",
                'action_url': f"/implantacao/{row['id']}"
            })
    return notifications


def _get_slow_pace(user_email, hoje):
    """
    Ritmo Lento: Implantação ativa onde a última tarefa concluída foi há mais de 15 dias.
    Priority: 4
    """
    notifications = []
    limite = hoje - timedelta(days=15)
    
    sql = """
        SELECT i.id, i.nome_empresa, MAX(ci.data_conclusao) as ultima_conclusao
        FROM implantacoes i
        JOIN checklist_items ci ON ci.implantacao_id = i.id
        WHERE i.usuario_cs = %s
        AND i.status = 'andamento'
        AND ci.completed = TRUE
        GROUP BY i.id
        HAVING MAX(ci.data_conclusao) < %s
    """
    results = query_db(sql, (user_email, limite)) or []
    
    for row in results:
        if isinstance(row, dict):
            ultima = _parse_datetime(row.get('ultima_conclusao'))
            dias_sem_progresso = (hoje - ultima).days if ultima else 15
            notifications.append({
                'type': 'info',
                'priority': 4,
                'title': f"🐢 Ritmo Lento: {row['nome_empresa']}",
                'message': f"Nenhuma tarefa concluída nos últimos {dias_sem_progresso} dias. Precisa de ajuda?",
                'action_url': f"/implantacao/{row['id']}"
            })
    return notifications


def _get_final_sprint(user_email):
    """
    Reta Final: Progresso > 80% mas ainda não finalizada.
    Priority: 5 (Oportunidade)
    """
    notifications = []
    
    # Esta query depende de como calculamos progresso. 
    # Vou fazer uma aproximação contando items.
    # Garante que só notifica se progresso >= 80% (0.8)
    sql = """
        SELECT i.id, i.nome_empresa,
               CAST(SUM(CASE WHEN ci.completed THEN 1 ELSE 0 END) AS FLOAT) / COUNT(*) * 100 as progresso
        FROM implantacoes i
        JOIN checklist_items ci ON ci.implantacao_id = i.id
        WHERE i.usuario_cs = %s
        AND i.status = 'andamento'
        AND ci.tipo_item = 'subtarefa'
        GROUP BY i.id
        HAVING (CAST(SUM(CASE WHEN ci.completed THEN 1 ELSE 0 END) AS FLOAT) / COUNT(*)) >= 0.8
    """
    results = query_db(sql, (user_email,)) or []
    
    for row in results:
        if isinstance(row, dict):
            prog = int(row['progresso'])
            notifications.append({
                'type': 'success', # Verde para incentivar
                'priority': 5,
                'title': f"🏁 {row['nome_empresa']}",
                'message': f"Progresso em {prog}%. Falta pouco para fechar essa implantação!",
                'action_url': f"/implantacao/{row['id']}"
            })
    return notifications


def _get_critical_tasks(user_email, hoje, fim_hoje):
    """Busca tarefas críticas (atrasadas + vence hoje)."""
    notifications = []
    
    sql_criticas = """
        SELECT 
            i.id, 
            i.nome_empresa,
            COUNT(CASE WHEN ci.previsao_original < %s THEN 1 END) as atrasadas,
            COUNT(CASE WHEN DATE(ci.previsao_original) = DATE(%s) THEN 1 END) as vence_hoje
        FROM implantacoes i
        JOIN checklist_items ci ON ci.implantacao_id = i.id
        WHERE i.usuario_cs = %s
        AND i.status IN ('andamento', 'nova', 'futura')
        AND ci.tipo_item = 'subtarefa'
        AND ci.completed = FALSE
        AND ci.previsao_original IS NOT NULL
        AND ci.previsao_original <= %s
        GROUP BY i.id, i.nome_empresa
        HAVING COUNT(ci.id) > 0
        ORDER BY COUNT(CASE WHEN ci.previsao_original < %s THEN 1 END) DESC
        LIMIT 5
    """
    criticas = query_db(sql_criticas, (hoje, hoje, user_email, fim_hoje, hoje)) or []
    
    for row in criticas:
        if isinstance(row, dict):
            atrasadas = row.get('atrasadas', 0) or 0
            vence_hoje = row.get('vence_hoje', 0) or 0
            total = atrasadas + vence_hoje
            nome = row.get('nome_empresa', 'Empresa')
            impl_id = row.get('id')
            
            if total > 0:
                partes = []
                if atrasadas > 0:
                    partes.append(f"{atrasadas} atrasada{'s' if atrasadas > 1 else ''}")
                if vence_hoje > 0:
                    partes.append(f"{vence_hoje} vence{'m' if vence_hoje > 1 else ''} hoje")
                
                notifications.append({
                    'type': 'danger',
                    'priority': 1,
                    'title': f"🔥 {nome[:30]}{'...' if len(nome) > 30 else ''}",
                    'message': f"{total} tarefas críticas: {', '.join(partes)}",
                    'action_url': f"/implantacao/{impl_id}"
                })
    
    return notifications


def _get_stopped_implementations(user_email, hoje):
    """Busca implantações paradas (notifica a cada 7 dias)."""
    notifications = []
    
    sql_paradas = """
        SELECT 
            i.id,
            i.nome_empresa,
            i.motivo_parada,
            tl.data_criacao as data_parada
        FROM implantacoes i
        LEFT JOIN (
            SELECT implantacao_id, MAX(data_criacao) as data_criacao
            FROM timeline_log
            WHERE tipo_evento = 'status_alterado'
            AND detalhes LIKE '%%parada%%'
            GROUP BY implantacao_id
        ) tl ON tl.implantacao_id = i.id
        WHERE i.usuario_cs = %s
        AND i.status = 'parada'
    """
    paradas = query_db(sql_paradas, (user_email,)) or []
    
    for row in paradas:
        if isinstance(row, dict):
            nome = row.get('nome_empresa', 'Empresa')
            motivo = row.get('motivo_parada', 'Sem motivo informado')
            data_parada = row.get('data_parada')
            impl_id = row.get('id')
            
            if data_parada:
                data_parada = _parse_datetime(data_parada)
                
                if data_parada:
                    dias_parada = (hoje - data_parada).days
                    
                    # Notifica a cada 7 dias (7, 14, 21, 28...)
                    if dias_parada >= 7 and dias_parada % 7 == 0:
                        notifications.append({
                            'type': 'danger',
                            'priority': 2,
                            'title': f"⏸️ {nome[:30]}{'...' if len(nome) > 30 else ''}",
                            'message': f"Parada há {dias_parada} dias. Motivo: {motivo[:40]}...",
                            'action_url': f"/implantacao/{impl_id}"
                        })
    
    return notifications


def _get_urgent_tasks(user_email, hoje, fim_hoje):
    """Busca tarefas urgentes (vence em 1-2 dias)."""
    notifications = []
    depois_amanha = hoje + timedelta(days=2)
    
    sql_urgentes = """
        SELECT 
            i.id,
            i.nome_empresa,
            COUNT(ci.id) as total
        FROM implantacoes i
        JOIN checklist_items ci ON ci.implantacao_id = i.id
        WHERE i.usuario_cs = %s
        AND i.status IN ('andamento', 'nova', 'futura')
        AND ci.tipo_item = 'subtarefa'
        AND ci.completed = FALSE
        AND ci.previsao_original IS NOT NULL
        AND ci.previsao_original > %s
        AND ci.previsao_original <= %s
        GROUP BY i.id, i.nome_empresa
        HAVING COUNT(ci.id) > 0
        ORDER BY COUNT(ci.id) DESC
        LIMIT 5
    """
    urgentes = query_db(sql_urgentes, (user_email, fim_hoje, depois_amanha)) or []
    
    for row in urgentes:
        if isinstance(row, dict):
            total = row.get('total', 0)
            nome = row.get('nome_empresa', 'Empresa')
            impl_id = row.get('id')
            
            notifications.append({
                'type': 'warning',
                'priority': 3,
                'title': f"⏰ {nome[:30]}{'...' if len(nome) > 30 else ''}",
                'message': f"{total} tarefas vencem em breve (1-2 dias)",
                'action_url': f"/implantacao/{impl_id}?tab=plano"
            })
    
    return notifications


def _get_upcoming_future(user_email, hoje):
    """Busca implantações futuras próximas (faltando 7 dias para início)."""
    notifications = []
    daqui_7_dias = hoje + timedelta(days=7)
    
    sql_futuras = """
        SELECT 
            id,
            nome_empresa,
            data_inicio_previsto
        FROM implantacoes
        WHERE usuario_cs = %s
        AND status = 'futura'
        AND data_inicio_previsto IS NOT NULL
        AND DATE(data_inicio_previsto) = DATE(%s)
    """
    futuras = query_db(sql_futuras, (user_email, daqui_7_dias)) or []
    
    for row in futuras:
        if isinstance(row, dict):
            nome = row.get('nome_empresa', 'Empresa')
            impl_id = row.get('id')
            
            notifications.append({
                'type': 'warning',
                'priority': 4,
                'title': f"📅 Previsão de Início",
                'message': f"{nome} está agendada para iniciar em 7 dias",
                'action_url': f"/implantacao/{impl_id}"
            })
    
    return notifications


def _get_no_forecast(user_email, hoje):
    """Busca implantações sem previsão (30 dias, depois a cada 7 dias)."""
    notifications = []
    
    sql_sem_previsao = """
        SELECT 
            id,
            nome_empresa,
            data_criacao
        FROM implantacoes
        WHERE usuario_cs = %s
        AND status = 'sem_previsao'
        AND data_inicio_previsto IS NULL
    """
    sem_previsao = query_db(sql_sem_previsao, (user_email,)) or []
    
    for row in sem_previsao:
        if isinstance(row, dict):
            nome = row.get('nome_empresa', 'Empresa')
            data_criacao = row.get('data_criacao')
            impl_id = row.get('id')
            
            if data_criacao:
                data_criacao = _parse_datetime(data_criacao)
                
                if data_criacao:
                    dias_sem_previsao = (hoje - data_criacao).days
                    
                    # Notifica aos 30 dias, depois a cada 7 dias
                    if dias_sem_previsao >= 30 and (dias_sem_previsao == 30 or (dias_sem_previsao - 30) % 7 == 0):
                        notifications.append({
                            'type': 'warning',
                            'priority': 5,
                            'title': f"⏳ Sem Previsão",
                            'message': f"{nome} aguarda definição há {dias_sem_previsao} dias",
                            'action_url': f"/implantacao/{impl_id}"
                        })
    
    return notifications


def _get_upcoming_tasks(user_email, hoje):
    """Busca tarefas próximas (vence em 3-7 dias)."""
    notifications = []
    depois_amanha = hoje + timedelta(days=2)
    daqui_7_dias = hoje + timedelta(days=7)
    
    sql_proximas = """
        SELECT 
            i.id,
            i.nome_empresa,
            COUNT(ci.id) as total
        FROM implantacoes i
        JOIN checklist_items ci ON ci.implantacao_id = i.id
        WHERE i.usuario_cs = %s
        AND i.status IN ('andamento', 'nova', 'futura')
        AND ci.tipo_item = 'subtarefa'
        AND ci.completed = FALSE
        AND ci.previsao_original IS NOT NULL
        AND ci.previsao_original > %s
        AND ci.previsao_original <= %s
        GROUP BY i.id, i.nome_empresa
        HAVING COUNT(ci.id) > 0
        ORDER BY COUNT(ci.id) DESC
        LIMIT 5
    """
    proximas = query_db(sql_proximas, (user_email, depois_amanha, daqui_7_dias)) or []
    
    for row in proximas:
        if isinstance(row, dict):
            total = row.get('total', 0)
            nome = row.get('nome_empresa', 'Empresa')
            impl_id = row.get('id')
            
            notifications.append({
                'type': 'info',
                'priority': 6,
                'title': f"⚠️ Tarefas Próximas",
                'message': f"{nome}: {total} tarefas vencem nesta semana",
                'action_url': f"/implantacao/{impl_id}?tab=plano"
            })
    
    return notifications


def _get_new_waiting(user_email):
    """Busca implantações novas aguardando início."""
    notifications = []
    
    sql_novas = """
        SELECT COUNT(*) as total
        FROM implantacoes
        WHERE usuario_cs = %s
        AND status = 'nova'
    """
    novas = query_db(sql_novas, (user_email,), one=True)
    total_novas = novas.get('total', 0) if novas else 0
    
    if total_novas > 0:
        notifications.append({
            'type': 'info',
            'priority': 7,
            'title': f"📋 Implantações Novas",
            'message': f"Você tem {total_novas} nova(s) implantação(ões) aguardando.",
            'action_url': "/dashboard"
        })
    
    return notifications


def _get_weekly_summary(user_email, hoje):
    """Busca resumo semanal (apenas segundas-feiras)."""
    notifications = []
    
    if hoje.weekday() == 0:
        sql_pendentes = """
            SELECT 
                COUNT(DISTINCT i.id) as implantacoes,
                COUNT(ci.id) as tarefas
            FROM checklist_items ci
            JOIN implantacoes i ON ci.implantacao_id = i.id
            WHERE i.usuario_cs = %s
            AND i.status = 'andamento'
            AND ci.tipo_item = 'subtarefa'
            AND ci.completed = FALSE
        """
        pendentes = query_db(sql_pendentes, (user_email,), one=True)
        
        if pendentes:
            total_tarefas = pendentes.get('tarefas', 0) or 0
            total_impl = pendentes.get('implantacoes', 0) or 0
            
            if total_tarefas > 0:
                notifications.append({
                    'type': 'info',
                    'priority': 8,
                    'title': f"📊 Resumo da Semana",
                    'message': f"{total_tarefas} pendências em {total_impl} implantações ativas.",
                    'action_url': "/dashboard"
                })
    
    return notifications


def _get_completed_this_week(user_email, inicio_semana):
    """Busca implantações concluídas esta semana."""
    notifications = []
    
    sql_concluidas = """
        SELECT COUNT(*) as total
        FROM implantacoes
        WHERE usuario_cs = %s
        AND status = 'finalizada'
        AND data_finalizacao >= %s
    """
    concluidas = query_db(sql_concluidas, (user_email, inicio_semana), one=True)
    total_concluidas = concluidas.get('total', 0) if concluidas else 0
    
    if total_concluidas > 0:
        notifications.append({
            'type': 'success',
            'priority': 9,
            'title': f"✅ Sucesso da Semana",
            'message': f"Incrível! {total_concluidas} implantação(ões) concluída(s).",
            'action_url': "/dashboard"
        })
    
    return notifications


def _parse_datetime(value):
    """Converte string para datetime se necessário."""
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace('Z', '+00:00'))
        except:
            return None
    return value


def get_test_notifications():
    """
    Gera notificações de teste para visualização.
    """
    return {
        'ok': True,
        'notifications': [
            {'type': 'danger', 'title': '🔥 Crítico', 'message': 'Cliente X está muito descontente', 'action_url': '#'},
            {'type': 'warning', 'title': '⏰ Prazo Vencendo', 'message': 'Treinamento Financeiro - Academia Y', 'action_url': '#'},
            {'type': 'info', 'title': '📋 Novo Processo', 'message': 'Reunião de alinhamento agendada', 'action_url': '#'},
            {'type': 'success', 'title': '✅ Concluído', 'message': 'Implantação da Academia Z finalizada', 'action_url': '#'},
        ],
        'total': 4,
        'test_mode': True
    }
