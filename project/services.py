# project/services.py

from flask import current_app
from .db import query_db, execute_db
from .constants import (
    CHECKLIST_OBRIGATORIO_ITEMS, MODULO_OBRIGATORIO,
    TAREFAS_TREINAMENTO_PADRAO, MODULO_PENDENCIAS,
    PERFIL_ADMIN, PERFIL_COORDENADOR # PERFIL_GERENTE REMOVIDO
)
from .utils import format_date_iso_for_json

# Importa logar_timeline do DB (para uso interno)
from .db import logar_timeline
# Importa timedelta, datetime e date para cálculo de data
from datetime import datetime, timedelta, date
import calendar # Adicionado para cálculo de gamificação

# --- FUNÇÃO AUXILIAR PARA CORREÇÃO DE TIMEZONE ---
def _to_naive_datetime(dt):
    """
    CORREÇÃO: Converte um objeto date/datetime para um datetime naive (sem tzinfo).
    Garante que a subtração de datas seja sempre entre objetos do mesmo tipo (naive).
    Retorna None se a entrada não for um tipo de data válido.
    """
    # 1. Se for apenas date (não datetime), converte para datetime no início do dia
    if isinstance(dt, date) and not isinstance(dt, datetime):
        return datetime.combine(dt, datetime.min.time())
    # 2. Se for datetime (aware ou naive), remove o tzinfo, forçando naive
    if isinstance(dt, datetime):
        return dt.replace(tzinfo=None)
    return None

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
    """
    Calcula o progresso de uma implantação (incluindo todas as tarefas, exceto pendências).
    CORREÇÃO DE BUG: Exclui MODULO_PENDENCIAS para que o progresso vá a 100% na finalização.
    """
    counts = query_db(
        "SELECT COUNT(*) as total, SUM(CASE WHEN concluida THEN 1 ELSE 0 END) as done "
        "FROM tarefas WHERE implantacao_id = %s AND tarefa_pai != %s", 
        (impl_id, MODULO_PENDENCIAS),
        one=True
    )
    # Garante que counts não seja None antes de acessar 'total' ou 'done'
    total = counts.get('total', 0) if counts else 0
    done = counts.get('done', 0) if counts else 0
    # Converte done para int se vier como Decimal ou outro tipo numérico (comum em alguns DBs)
    done = int(done) if done is not None else 0

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

    # Garante que pending_tasks não seja None
    total_pendentes = pending_tasks.get('total', 0) if pending_tasks else 0

    if total_pendentes == 0:
        impl_status = query_db(
            "SELECT status, nome_empresa FROM implantacoes WHERE id = %s",
            (impl_id,),
            one=True
        )
        if impl_status and impl_status.get('status') == 'andamento':
            agora = datetime.now() # Captura timestamp para consistência
            execute_db(
                "UPDATE implantacoes SET status = 'finalizada', data_finalizacao = %s WHERE id = %s",
                (agora, impl_id)
            )
            detalhe = f'Implantação "{impl_status.get("nome_empresa", "N/A")}" auto-finalizada.'
            logar_timeline(impl_id, usuario_cs_email, 'auto_finalizada', detalhe)

            # Busca o log recém-criado para retornar formatado
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
                # Garante que log_final seja um dict antes de modificar
                if not isinstance(log_final, dict):
                    log_final = dict(log_final)
                log_final['data_criacao'] = format_date_iso_for_json(log_final.get('data_criacao'))
                return True, log_final
            else:
                 # Mesmo que o log não seja encontrado (improvável), a finalização ocorreu
                 return True, None
    return False, None

# --- FUNÇÃO ATUALIZADA: get_dashboard_data ---
def get_dashboard_data(user_email, user_perfil_acesso, target_user_email=None):
    """
    Busca e processa dados do dashboard.
    Para Administrador/Coordenador, busca todas as implantações ou filtra por target_user_email.
    Para outros perfis, busca apenas as implantações do user_email.
    """

    # 1. Determinar o filtro de usuário na query
    # PERFIS_COM_GESTAO agora é [PERFIL_ADMIN, PERFIL_COORDENADOR]
    is_manager = user_perfil_acesso in [PERFIL_ADMIN, PERFIL_COORDENADOR] 
    
    # Se for gestor e o filtro estiver vazio (ou 'todos'), buscar TUDO.
    # Se não for gestor, ou se for gestor filtrando um usuário específico, aplicar o filtro.
    if is_manager and not target_user_email:
        # Administrador/Coordenador sem filtro: buscar TUDO
        where_clause = "1=1"
        args = []
    else:
        # Usuário normal: buscar APENAS o seu.
        # OU Administrador/Coordenador com filtro
        user_to_filter = target_user_email if target_user_email else user_email
        where_clause = "usuario_cs = %s"
        args = [user_to_filter]

    # Query principal de implantações
    impl_list = query_db(
        f"""
        SELECT *
        FROM implantacoes
        WHERE {where_clause}
        ORDER BY CASE status
                    WHEN 'andamento' THEN 1
                    WHEN 'parada' THEN 2
                    WHEN 'futura' THEN 3
                    WHEN 'finalizada' THEN 4
                    ELSE 5
                 END, data_criacao DESC
        """,
        tuple(args)
    )
    # Garante que impl_list seja sempre uma lista
    impl_list = impl_list if impl_list is not None else []


    dashboard_data = {
        'andamento': [], 'atrasadas': [], 'futuras': [],
        'finalizadas': [], 'paradas': []
    }
    metrics = {
        'impl_andamento_total': 0, 'implantacoes_atrasadas': 0,
        'implantacoes_futuras': 0, 'impl_finalizadas': 0, 'impl_paradas': 0,
        'impl_finalizadas_mes_atual': 0, # NOVO: Métrica para alinhar com gamificação (mensal)
        # INICIO MODULO CARDS
        'impl_modulo_andamento': 0,
        'impl_modulo_finalizado': 0,
        # FIM MODULO CARDS
    }

    # Otimização: Buscar todas as tarefas de uma vez
    impl_ids = [impl['id'] for impl in impl_list if impl and 'id' in impl] # Garante que impl e id existam
    tasks_by_impl = {}
    if impl_ids:
        # --- CORREÇÃO AQUI ---
        # Corrigido para usar IN:
        placeholders = ','.join(['%s'] * len(impl_ids)) # Cria ?,?,?,... ou %s,%s,%s,...
        sql = f"SELECT implantacao_id, concluida FROM tarefas WHERE implantacao_id IN ({placeholders})"
        # query_db lida com %s -> ? para SQLite. Passamos os IDs como argumentos separados.
        all_tasks = query_db(sql, tuple(impl_ids))
        # --- FIM DA CORREÇÃO ---

        if all_tasks: # Verifica se a consulta retornou algo
             for task in all_tasks:
                 # Garante que a chave exista antes de anexar
                 impl_id_key = task.get('implantacao_id')
                 if impl_id_key is not None: # Verifica se a chave existe e não é None
                     if impl_id_key not in tasks_by_impl:
                          tasks_by_impl[impl_id_key] = []
                     tasks_by_impl[impl_id_key].append(task)


    agora = datetime.now() # Obter a hora atual uma vez
    primeiro_dia_mes_atual = datetime(agora.year, agora.month, 1) # NOVO: Início do mês atual

    for impl in impl_list:
        # Pula se 'impl' for None ou não for um dicionário (segurança extra)
        if not impl or not isinstance(impl, dict):
            continue

        impl_id = impl.get('id')
        # Pula se não houver ID (improvável, mas seguro)
        if impl_id is None:
             continue

        status = impl.get('status')
        impl_type = impl.get('tipo') # Obtém o tipo

        # Formata datas para os modais
        impl['data_criacao_iso'] = format_date_iso_for_json(impl.get('data_criacao'), only_date=True)
        impl['data_inicio_producao_iso'] = format_date_iso_for_json(impl.get('data_inicio_producao'), only_date=True)
        impl['data_final_implantacao_iso'] = format_date_iso_for_json(impl.get('data_final_implantacao'), only_date=True)

        # Novo: Chamada para a função _get_progress corrigida
        impl['progresso'], total_tasks, done_tasks = _get_progress(impl_id)

        # Classifica a implantação
        if status == 'finalizada':
            
            # Conta todas as finalizadas (All-Time) - Mantém a métrica original do perfil para o Total Histórico
            metrics['impl_finalizadas'] += 1 

            # --- CORREÇÃO DE BUG CRÍTICO: MOSTRAR A LISTA ---
            # Devemos adicionar a implantação à lista de exibição AQUI.
            dashboard_data['finalizadas'].append(impl)
            
            # --- CÁLCULO DA MÉTRICA SECUNDÁRIA (MENSAL) ---
            data_finalizacao_obj = impl.get('data_finalizacao')
            data_finalizacao_naive = _to_naive_datetime(data_finalizacao_obj)
            
            if data_finalizacao_naive and data_finalizacao_naive >= primeiro_dia_mes_atual:
                metrics['impl_finalizadas_mes_atual'] += 1 # Contagem do Mês Atual
            
            # NOVO: Módulo Finalizado
            if impl_type == 'modulo':
                 metrics['impl_modulo_finalizado'] += 1

        elif status == 'parada':
            dashboard_data['paradas'].append(impl)
            metrics['impl_paradas'] += 1
        elif status == 'futura' or impl.get('tipo') == 'futura': # Mantém tipo futura como segurança
            dashboard_data['futuras'].append(impl)
            metrics['implantacoes_futuras'] += 1
        elif status == 'andamento': # Trata apenas 'andamento' aqui
            # Cálculo de dias_passados em Python (CORREÇÃO DE BUG: Timezone e -1)
            dias_passados = 0
            data_criacao_obj = impl.get('data_criacao')

            agora_naive = _to_naive_datetime(agora)
            criacao_naive = _to_naive_datetime(data_criacao_obj)
            
            if agora_naive and criacao_naive:
                try:
                    dias_passados_delta = agora_naive - criacao_naive 
                    # Garante que o contador seja 0 ou positivo
                    dias_passados = dias_passados_delta.days if dias_passados_delta.days >= 0 else 0
                except Exception as e:
                    # CORREÇÃO DE BUG: Não retornar -1 (código de erro), retornar 0.
                    print(f"AVISO: Erro de cálculo de dias para impl {impl_id}. Erro: {e}")
                    dias_passados = 0 
            else:
                 dias_passados = 0 # Data de criação inválida ou nula

            impl['dias_passados'] = dias_passados # Adiciona o campo para o template

            if dias_passados > 25:
                dashboard_data['atrasadas'].append(impl)
                metrics['implantacoes_atrasadas'] += 1
            else:
                 # Inclui no andamento mesmo se o cálculo de dias falhar (0)
                 dashboard_data['andamento'].append(impl)

            # NOVO: Módulo em Andamento
            if impl_type == 'modulo':
                 metrics['impl_modulo_andamento'] += 1

            # Conta 'andamento' e 'atrasadas' no total em andamento
            metrics['impl_andamento_total'] += 1
        else:
            # Caso para status desconhecido ou None
            print(f"AVISO: Implantação ID {impl_id} com status desconhecido ou nulo: '{status}'. Ignorando na categorização.")


    # Atualiza o perfil com as métricas calculadas (APENAS se for a visão do próprio usuário)
    # Note: impl_finalizadas agora é o total ALL-TIME. O campo impl_finalizadas_mes_atual é APENAS para o dashboard.
    if impl_list and not is_manager and not target_user_email: 
        try:
             rows_affected = execute_db(
                 """
                 UPDATE perfil_usuario
                 SET impl_andamento_total = %s, implantacoes_atrasadas = %s,
                     impl_finalizadas = %s, impl_paradas = %s
                 WHERE usuario = %s
                 """,
                 (metrics['impl_andamento_total'], metrics['implantacoes_atrasadas'],
                  metrics['impl_finalizadas'], metrics['impl_paradas'], user_email)
             )
        except Exception as update_err:
             print(f"AVISO: Falha ao atualizar métricas no perfil {user_email}: {update_err}")

    return dashboard_data, metrics
# --- FIM DA FUNÇÃO get_dashboard_data ---


def calculate_time_in_status(impl_id, status_target='parada'):
    """
    Calcula o tempo (em dias) que uma implantação permaneceu em um status específico.
    Usado para calcular a duração da parada atual.
    """
    impl = query_db(
        "SELECT data_criacao, data_finalizacao, status FROM implantacoes WHERE id = %s",
        (impl_id,), one=True
    )

    if not impl or not impl.get('status'):
        return None # Implantação não encontrada ou sem status definido

    # Se a implantação está 'parada' e tem uma data_finalizacao (que guarda a data da pausa)
    if impl['status'] == status_target and status_target == 'parada' and impl.get('data_finalizacao'):
        data_inicio_parada_obj = impl['data_finalizacao']

        # O DB retorna um objeto datetime ou date
        # Usa a função auxiliar para garantir naive datetime (CORREÇÃO DE BUG: Timezone)
        agora = datetime.now()
        agora_naive = _to_naive_datetime(agora)
        parada_naive = _to_naive_datetime(data_inicio_parada_obj)
        
        if agora_naive and parada_naive:
            try:
                delta = agora_naive - parada_naive
                return max(0, int(delta.days)) # Retorna o número de dias
            except TypeError as te:
                 # CORREÇÃO: Não retorna erro de tipo, retorna None ou 0
                 print(f"AVISO: Erro de tipo ao calcular tempo parado para impl {impl_id}. Verifique timezones. Erro: {te}")
                 return None


    # Poderia adicionar lógica para outros status se necessário
    return None # Não está no status alvo ou dados insuficientes


def get_analytics_data(target_cs_email=None, target_status=None, start_date=None, end_date=None, target_paradas_cs=None):
    """Busca e processa dados de TODA a carteira (ou filtrada) para o módulo Gerencial."""

    query_impl = """
        SELECT i.*,
               p.nome as cs_nome, p.cargo as cs_cargo, p.perfil_acesso as cs_perfil
        FROM implantacoes i
        LEFT JOIN perfil_usuario p ON i.usuario_cs = p.usuario
        WHERE 1=1
    """
    args_impl = []

    is_sqlite = current_app.config.get('USE_SQLITE_LOCALLY', False)
    date_func = "date" if is_sqlite else "" # Função date() para SQLite

    # Filtro por CS (influencia as métricas de produtividade - cs_metrics)
    if target_cs_email:
        query_impl += " AND i.usuario_cs = %s "
        args_impl.append(target_cs_email)

    # Filtro por Status
    if target_status and target_status != 'todas':
        if target_status == 'atrasadas_status':
             # Ajuste para PostgreSQL >= ou SQLite JULIANDAY/date()
             if is_sqlite:
                 query_impl += " AND i.status = 'andamento' AND date(i.data_criacao) <= date('now', '-26 days') " # <= -26 para pegar > 25
             else: # PostgreSQL
                 query_impl += " AND i.status = 'andamento' AND i.data_criacao <= NOW() - INTERVAL '26 days' " # <= 26 dias atrás para pegar > 25
        else:
            query_impl += " AND i.status = %s "
            args_impl.append(target_status)

    # Filtro de Data para Implantações Finalizadas/Criadas
    # Aplica a data_criacao se não for 'finalizada', senão aplica a data_finalizacao
    date_field_to_filter = "i.data_finalizacao" if target_status == 'finalizada' else "i.data_criacao"

    if start_date:
        query_impl += f" AND {date_func}({date_field_to_filter}) >= {date_func}(%s) "
        args_impl.append(start_date)
    if end_date:
        # Para PostgreSQL, ajustar para incluir o dia inteiro (< próximo dia)
        if not is_sqlite:
            try:
                end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
                next_day = end_date_obj + timedelta(days=1)
                query_impl += f" AND {date_field_to_filter} < %s "
                args_impl.append(next_day.strftime('%Y-%m-%d'))
            except ValueError:
                 print(f"AVISO: Formato de end_date inválido ({end_date}). Usando <=.")
                 query_impl += f" AND {date_func}({date_field_to_filter}) <= {date_func}(%s) "
                 args_impl.append(end_date)
        else: # SQLite usa <=
             query_impl += f" AND {date_func}({date_field_to_filter}) <= {date_func}(%s) "
             args_impl.append(end_date)


    query_impl += " ORDER BY i.nome_empresa "

    # 1. Busca implantações filtradas (principal para métricas)
    impl_list = query_db(query_impl, tuple(args_impl))
    impl_list = impl_list if impl_list is not None else [] # Garante lista

    # --- NOVO: Query e processamento dedicado para Implantações Paradas Detalhadas ---
    query_paradas = """
        SELECT i.*,
               p.nome as cs_nome, p.cargo as cs_cargo, p.perfil_acesso as cs_perfil
        FROM implantacoes i
        LEFT JOIN perfil_usuario p ON i.usuario_cs = p.usuario
        WHERE i.status = 'parada'
    """
    args_paradas = []
    
    # Aplica o filtro de CS ESPECÍFICO para paradas
    if target_paradas_cs and target_paradas_cs != 'todos':
        query_paradas += " AND i.usuario_cs = %s "
        args_paradas.append(target_paradas_cs)

    # Aplica filtros de data à data de paralisação (data_finalizacao)
    date_field_to_filter_paradas = "i.data_finalizacao"

    if start_date:
        query_paradas += f" AND {date_func}({date_field_to_filter_paradas}) >= {date_func}(%s) "
        args_paradas.append(start_date)
    
    if end_date:
        if not is_sqlite:
            try:
                end_date_obj_paradas = datetime.strptime(end_date, '%Y-%m-%d').date()
                next_day_paradas = end_date_obj_paradas + timedelta(days=1)
                query_paradas += f" AND {date_field_to_filter_paradas} < %s "
                args_paradas.append(next_day_paradas.strftime('%Y-%m-%d'))
            except ValueError:
                query_paradas += f" AND {date_func}({date_field_to_filter_paradas}) <= {date_func}(%s) "
                args_paradas.append(end_date)
        else:
             query_paradas += f" AND {date_func}({date_field_to_filter_paradas}) <= {date_func}(%s) "
             args_paradas.append(end_date)

    query_paradas += " ORDER BY i.nome_empresa "
    paradas_raw = query_db(query_paradas, tuple(args_paradas))
    paradas_raw = paradas_raw if paradas_raw is not None else []
    
    implantacoes_paradas_detalhadas = []
    motivos_parada_global = {} # Recalculado separadamente
    total_paradas_detalhes = 0
    
    for impl_parada in paradas_raw:
        impl_id = impl_parada.get('id')
        cs_email_impl = impl_parada.get('usuario_cs')
        parada_dias = calculate_time_in_status(impl_id, 'parada')
        motivo = impl_parada.get('motivo_parada') or 'Motivo Não Especificado'
        
        # Agregação global de motivos (usando APENAS a lista filtrada)
        motivos_parada_global[motivo] = motivos_parada_global.get(motivo, 0) + 1
        total_paradas_detalhes += 1

        implantacoes_paradas_detalhadas.append({
            'id': impl_id,
            'nome_empresa': impl_parada.get('nome_empresa'),
            'motivo_parada': motivo,
            'parada_dias': parada_dias if parada_dias is not None else 0,
            'cs_nome': impl_parada.get('cs_nome', cs_email_impl)
        })
    # --- FIM DO NOVO PROCESSAMENTO ---


    # --- 2. Busca e Filtro de Tarefas por Período/Tag (Para Produtividade) ---
    query_tasks = """
        SELECT i.usuario_cs, t.tag
        FROM tarefas t
        JOIN implantacoes i ON t.implantacao_id = i.id
        WHERE t.concluida = TRUE AND t.tag IN ('Ação interna', 'Reunião')
        AND t.data_conclusao IS NOT NULL
    """
    args_tasks = []

    # Filtro de Data para Tarefas Concluídas
    if start_date:
        query_tasks += f" AND {date_func}(t.data_conclusao) >= {date_func}(%s) "
        args_tasks.append(start_date)
    if end_date:
        if not is_sqlite:
            try:
                end_date_obj_task = datetime.strptime(end_date, '%Y-%m-%d').date()
                next_day_task = end_date_obj_task + timedelta(days=1)
                query_tasks += " AND t.data_conclusao < %s "
                args_tasks.append(next_day_task.strftime('%Y-%m-%d'))
            except ValueError:
                query_tasks += f" AND {date_func}(t.data_conclusao) <= {date_func}(%s) "
                args_tasks.append(end_date)
        else: # SQLite
            query_tasks += f" AND {date_func}(t.data_conclusao) <= {date_func}(%s) "
            args_tasks.append(end_date)

    if target_cs_email:
        query_tasks += " AND i.usuario_cs = %s "
        args_tasks.append(target_cs_email)

    tasks_data = query_db(query_tasks, tuple(args_tasks))
    tasks_data = tasks_data if tasks_data is not None else [] # Garante lista

    # --- 3. Processamento e Agregação ---
    all_cs_profiles = query_db("SELECT usuario, nome, cargo, perfil_acesso FROM perfil_usuario")
    all_cs_profiles = all_cs_profiles if all_cs_profiles is not None else [] # Garante lista

    cs_metrics = {p['usuario']: {
        'email': p['usuario'], 'nome': p['nome'] or p['usuario'], 'cargo': p['cargo'] or 'N/A',
        'perfil': p['perfil_acesso'] or 'Nenhum',
        'impl_total': 0, 'impl_andamento': 0, 'impl_finalizadas': 0, 'impl_paradas': 0,
        'tma_sum': 0, 'progresso_medio': 0, 'tma_medio': 'N/A', 'motivos_parada': {},
        'prod_tags': {'Ação interna': 0, 'Reunião': 0}, # Inicializa contadores
        'parada_dias_total': 0, 'impl_atrasadas_count': 0 # Adiciona contador de atrasadas por CS
    } for p in all_cs_profiles if p and p.get('usuario')} # Garante que p e usuario existam

    # Agregação de tarefas concluídas por tag e CS (baseado nos filtros de data)
    for row in tasks_data:
        cs_email_task = row.get('usuario_cs')
        if cs_email_task in cs_metrics:
            tag = row.get('tag')
            if tag in cs_metrics[cs_email_task]['prod_tags']:
                cs_metrics[cs_email_task]['prod_tags'][tag] += 1

    # Agregações Globais e por Implantação (TMA, Status, Atraso)
    total_impl_global = 0
    total_finalizadas = 0
    total_andamento_global = 0
    # total_paradas = 0 # Removido, usando total_paradas_detalhes
    total_atrasadas_status = 0 # Contagem global de atrasadas (>25d)
    tma_dias_sum = 0
    # motivos_parada_global = {} # Removido, usando o da lista detalhada
    # implantacoes_paradas_detalhadas = [] # Removido, usando a lista separada
    agora = datetime.now() # Hora atual para cálculo de dias passados

    for impl in impl_list:
        # Pula se impl for None ou não dict
        if not impl or not isinstance(impl, dict): continue

        impl_id = impl.get('id')
        cs_email_impl = impl.get('usuario_cs')
        status = impl.get('status')

        # Ignora implantações sem CS associado ou sem ID
        if not impl_id or not cs_email_impl or cs_email_impl not in cs_metrics:
            continue

        total_impl_global += 1 # Conta apenas implantações válidas e com CS
        metrics = cs_metrics[cs_email_impl]
        metrics['impl_total'] += 1

        # Cálculo TMA em Python (CORREÇÃO DE BUG: Timezone)
        tma_dias = None
        if status == 'finalizada':
            dt_criacao = impl.get('data_criacao')
            dt_finalizacao = impl.get('data_finalizacao')
            if dt_criacao and dt_finalizacao:
                # Conversão segura para datetime
                if isinstance(dt_criacao, date) and not isinstance(dt_criacao, datetime): dt_criacao = datetime.combine(dt_criacao, datetime.min.time())
                if isinstance(dt_finalizacao, date) and not isinstance(dt_finalizacao, datetime): dt_finalizacao = datetime.combine(dt_finalizacao, datetime.min.time())
                # Cálculo se ambos são datetime
                if isinstance(dt_criacao, datetime) and isinstance(dt_finalizacao, datetime):
                     # Trata timezone (simplificado)
                     criacao_naive = dt_criacao.replace(tzinfo=None) if dt_criacao.tzinfo else dt_criacao
                     final_naive = dt_finalizacao.replace(tzinfo=None) if dt_finalizacao.tzinfo else dt_finalizacao
                     try:
                         delta = final_naive - criacao_naive
                         tma_dias = max(0, delta.days)
                     except TypeError: pass # Ignora erro de timezone

            total_finalizadas += 1
            metrics['impl_finalizadas'] += 1
            if tma_dias is not None:
                tma_dias_sum += tma_dias
                metrics['tma_sum'] += tma_dias

        elif status == 'parada':
            # total_paradas += 1 # Removido
            metrics['impl_paradas'] += 1
            parada_dias = calculate_time_in_status(impl_id, 'parada')
            if parada_dias is not None:
                metrics['parada_dias_total'] += parada_dias

            motivo = impl.get('motivo_parada') or 'Motivo Não Especificado'
            # motivos_parada_global[motivo] = motivos_parada_global.get(motivo, 0) + 1 # Removido
            metrics['motivos_parada'][motivo] = metrics['motivos_parada'].get(motivo, 0) + 1

        elif status == 'andamento':
            total_andamento_global += 1
            metrics['impl_andamento'] += 1

            # Cálculo de Dias Passados para Atraso
            data_criacao_obj = impl.get('data_criacao')
            dias_passados = 0
            if data_criacao_obj:
                 if isinstance(data_criacao_obj, date) and not isinstance(data_criacao_obj, datetime): data_criacao_obj = datetime.combine(data_criacao_obj, datetime.min.time())
                 if isinstance(data_criacao_obj, datetime):
                     agora_naive = agora.replace(tzinfo=None) if agora.tzinfo else agora
                     criacao_naive = data_criacao_obj.replace(tzinfo=None) if data_criacao_obj.tzinfo else data_criacao_obj
                     try:
                         dias_passados_delta = agora_naive - criacao_naive
                         dias_passados = dias_passados_delta.days if dias_passados_delta.days >= 0 else 0
                     except TypeError: dias_passados = -1 # Erro de timezone

            if dias_passados > 25:
                total_atrasadas_status += 1
                metrics['impl_atrasadas_count'] += 1 # Conta atrasadas por CS


    # Finalização das Métricas do CS
    # Filtra CSs que não têm implantações nos filtros atuais, a menos que nenhum CS tenha sido selecionado
    final_cs_metrics_list = []
    for email, metrics_data in cs_metrics.items():
        if metrics_data['impl_total'] > 0 or not target_cs_email: # Mostra todos se nenhum filtro de CS
            if metrics_data['impl_finalizadas'] > 0 and metrics_data['tma_sum'] is not None:
                metrics_data['tma_medio'] = round(metrics_data['tma_sum'] / metrics_data['impl_finalizadas'], 1)
            else:
                metrics_data['tma_medio'] = 'N/A'
            # Progresso médio não está sendo calculado aqui, manter 0 ou remover
            metrics_data['progresso_medio'] = 0
            final_cs_metrics_list.append(metrics_data)

    # Finalização das Métricas Globais
    global_metrics = {
        'total_impl': total_impl_global,
        'total_finalizadas': total_finalizadas,
        'total_andamento': total_andamento_global,
        'total_paradas': total_paradas_detalhes, # Usando o total da lista detalhada
        'total_atrasadas': total_atrasadas_status, # Usar a contagem feita no loop
        'global_tma': round(tma_dias_sum / total_finalizadas, 1) if total_finalizadas > 0 and tma_dias_sum is not None else 'N/A',
        'motivos_parada': motivos_parada_global # Usando o da lista detalhada
    }

    return global_metrics, final_cs_metrics_list, implantacoes_paradas_detalhadas


# --- FUNÇÃO PARA GAMIFICAÇÃO ---
def calcular_pontuacao_gamificacao(usuario_cs, mes, ano):
    """
    Calcula a pontuação da gamificação para um usuário em um mês/ano específico.
    CORREÇÃO DE BUG: Ajusta o filtro de data para garantir que todas as implantações do mês sejam contadas.
    """

    # 1. Buscar Perfil e Métricas Manuais
    perfil = query_db("SELECT cargo FROM perfil_usuario WHERE usuario = %s", (usuario_cs,), one=True)
    if not perfil:
        # Lança erro se o perfil não for encontrado, pois é essencial
        raise ValueError(f"Perfil de usuário não encontrado para {usuario_cs}")
    cargo = perfil.get('cargo', 'N/A') # Ex: Júnior, Pleno, Sênior

    metricas_manuais = query_db(
        "SELECT * FROM gamificacao_metricas_mensais WHERE usuario_cs = %s AND mes = %s AND ano = %s",
        (usuario_cs, mes, ano), one=True
    )
    # Converte para dicionário padrão se não for None
    metricas_manuais = dict(metricas_manuais) if metricas_manuais else {}

    # Preenche com padrões se o registro não existir ou campos forem NULL
    # Usar .setdefault() para garantir que a chave exista no dicionário
    metricas_manuais.setdefault('nota_qualidade', None)
    metricas_manuais.setdefault('assiduidade', None)
    metricas_manuais.setdefault('planos_sucesso_perc', None)
    metricas_manuais.setdefault('satisfacao_processo', None)
    metricas_manuais.setdefault('reclamacoes', 0)
    metricas_manuais.setdefault('perda_prazo', 0)
    metricas_manuais.setdefault('nao_preenchimento', 0)
    metricas_manuais.setdefault('elogios', 0)
    metricas_manuais.setdefault('recomendacoes', 0)
    metricas_manuais.setdefault('certificacoes', 0)
    metricas_manuais.setdefault('treinamentos_pacto_part', 0)
    metricas_manuais.setdefault('treinamentos_pacto_aplic', 0)
    metricas_manuais.setdefault('reunioes_presenciais', 0)
    metricas_manuais.setdefault('cancelamentos_resp', 0)
    metricas_manuais.setdefault('nao_envolvimento', 0)
    metricas_manuais.setdefault('desc_incompreensivel', 0)
    metricas_manuais.setdefault('hora_extra', 0)
    # Adicionar padrões para 'perda_sla_grupo' e 'finalizacao_incompleta' se forem usados
    metricas_manuais.setdefault('perda_sla_grupo', 0)
    metricas_manuais.setdefault('finalizacao_incompleta', 0)


    # 2. Definir Período
    try:
        primeiro_dia_obj = date(ano, mes, 1)
        ultimo_dia_mes = calendar.monthrange(ano, mes)[1]
        
        # O início é sempre 00:00:00 do primeiro dia do mês (limite inclusivo)
        primeiro_dia_inclusivo = datetime.combine(primeiro_dia_obj, datetime.min.time())
        
        # NOVO: Define o limite superior como 00:00:00 do primeiro dia do PRÓXIMO mês (limite exclusivo)
        fim_ultimo_dia_exclusivo = datetime.combine(primeiro_dia_obj + timedelta(days=ultimo_dia_mes), datetime.min.time())
        
        dias_no_mes = ultimo_dia_mes
    except ValueError:
        raise ValueError(f"Mês ({mes}) ou Ano ({ano}) inválido.")


    # 3. Buscar Dados Automáticos do Período
    # a) Implantações Finalizadas e TMA
    impl_finalizadas = query_db(
        """
        SELECT data_criacao, data_finalizacao FROM implantacoes
        WHERE usuario_cs = %s AND status = 'finalizada'
        AND data_finalizacao >= %s AND data_finalizacao < %s -- CORREÇÃO: Usando < e limite exclusivo
        """,
        (usuario_cs, primeiro_dia_inclusivo, fim_ultimo_dia_exclusivo)
    )
    impl_finalizadas = impl_finalizadas if impl_finalizadas is not None else [] # Garante lista
    count_finalizadas = len(impl_finalizadas)
    tma_total_dias = 0
    if count_finalizadas > 0:
        for impl in impl_finalizadas:
             # Garante que impl é um dicionário
             if not isinstance(impl, dict): continue
             dt_criacao = impl.get('data_criacao')
             dt_finalizacao = impl.get('data_finalizacao')
             if dt_criacao and dt_finalizacao:
                if isinstance(dt_criacao, date) and not isinstance(dt_criacao, datetime): dt_criacao = datetime.combine(dt_criacao, datetime.min.time())
                if isinstance(dt_finalizacao, date) and not isinstance(dt_finalizacao, datetime): dt_finalizacao = datetime.combine(dt_finalizacao, datetime.min.time())
                if isinstance(dt_criacao, datetime) and isinstance(dt_finalizacao, datetime):
                    # Trata timezone (simplificado)
                    criacao_naive = dt_criacao.replace(tzinfo=None) if dt_criacao.tzinfo else dt_criacao
                    final_naive = dt_finalizacao.replace(tzinfo=None) if dt_finalizacao.tzinfo else dt_finalizacao
                    try:
                        delta = final_naive - criacao_naive
                        tma_total_dias += max(0, delta.days)
                    except TypeError: pass # Ignora erro de timezone
        tma_medio = round(tma_total_dias / count_finalizadas, 1) if tma_total_dias is not None else None
    else:
        tma_medio = None # N/A se nenhuma finalizada

    # b) Implantações Iniciadas
    impl_iniciadas = query_db(
        "SELECT COUNT(*) as total FROM implantacoes WHERE usuario_cs = %s AND data_criacao >= %s AND data_criacao < %s", # Usando < para consistência
        (usuario_cs, primeiro_dia_inclusivo, fim_ultimo_dia_exclusivo), one=True
    )
    count_iniciadas = impl_iniciadas.get('total', 0) if impl_iniciadas else 0

    # c) Tarefas Concluídas (para média diária)
    tarefas_concluidas = query_db(
         """
         SELECT tag, COUNT(*) as total FROM tarefas
         WHERE implantacao_id IN (SELECT id FROM implantacoes WHERE usuario_cs = %s)
         AND concluida = TRUE AND tag IN ('Ação interna', 'Reunião')
         AND data_conclusao >= %s AND data_conclusao < %s -- Usando < para consistência
         GROUP BY tag
         """,
         (usuario_cs, primeiro_dia_inclusivo, fim_ultimo_dia_exclusivo)
    )
    tarefas_concluidas = tarefas_concluidas if tarefas_concluidas is not None else [] # Garante lista
    count_acao_interna = 0
    count_reuniao = 0
    for row in tarefas_concluidas:
        if isinstance(row, dict): # Garante que row é dict
             if row.get('tag') == 'Ação interna': count_acao_interna = row.get('total', 0)
             elif row.get('tag') == 'Reunião': count_reuniao = row.get('total', 0)

    # Aproximação Média Diária (pode ser refinada para dias úteis)
    media_reunioes_dia = round(count_reuniao / dias_no_mes, 2) if dias_no_mes > 0 else 0
    media_acoes_dia = round(count_acao_interna / dias_no_mes, 2) if dias_no_mes > 0 else 0


    # 4. Verificar Elegibilidade (usando métricas manuais e automáticas)
    elegivel = True
    motivo_inelegibilidade = []

    min_nota_qualidade = 80
    min_assiduidade = 85
    min_reunioes_dia_criterio = 3 # Limite do critério, não a média calculada
    min_planos_sucesso = 75
    max_reclamacoes = 1
    max_perda_prazo = 2
    max_nao_preenchimento = 2

    min_processos_concluidos = 0
    if cargo == 'Júnior': min_processos_concluidos = 4
    elif cargo == 'Pleno': min_processos_concluidos = 5
    elif cargo == 'Sênior': min_processos_concluidos = 5

    # Verificações (usar .get com default None para checar se foi preenchido)
    nq = metricas_manuais.get('nota_qualidade')
    if nq is None: elegivel = False; motivo_inelegibilidade.append("Nota Qualidade não informada")
    elif nq < min_nota_qualidade: elegivel = False; motivo_inelegibilidade.append(f"Nota Qualidade < {min_nota_qualidade}%")

    assid = metricas_manuais.get('assiduidade')
    if assid is None: elegivel = False; motivo_inelegibilidade.append("Assiduidade não informada")
    elif assid < min_assiduidade: elegivel = False; motivo_inelegibilidade.append(f"Assiduidade < {min_assiduidade}%")

    psp = metricas_manuais.get('planos_sucesso_perc')
    if psp is None: elegivel = False; motivo_inelegibilidade.append("Planos Sucesso % não informado")
    elif psp < min_planos_sucesso: elegivel = False; motivo_inelegibilidade.append(f"Planos Sucesso < {min_planos_sucesso}%")

    # Verificar critério de Reuniões por dia (se for uma métrica manual ou outra forma de medir)
    # Ex: reunioes_dia_manual = metricas_manuais.get('reunioes_dia_avg_manual')
    # if reunioes_dia_manual is None: elegivel = False; motivo_inelegibilidade.append("Média Reuniões/Dia não informada")
    # elif reunioes_dia_manual < min_reunioes_dia_criterio: elegivel = False; motivo_inelegibilidade.append(f"Média Reuniões/Dia < {min_reunioes_dia_criterio}")

    if count_finalizadas < min_processos_concluidos:
         elegivel = False
         motivo_inelegibilidade.append(f"Impl. Finalizadas ({count_finalizadas}) < {min_processos_concluidos} ({cargo})")

    # Critérios Impeditivos (Penalidades) - Usa .get com default 0
    if metricas_manuais.get('reclamacoes', 0) >= max_reclamacoes + 1:
        elegivel = False; motivo_inelegibilidade.append(f"Reclamações >= {max_reclamacoes + 1}")
    if metricas_manuais.get('perda_prazo', 0) >= max_perda_prazo + 1:
        elegivel = False; motivo_inelegibilidade.append(f"Perda Prazo >= {max_perda_prazo + 1}")
    if metricas_manuais.get('nao_preenchimento', 0) >= max_nao_preenchimento + 1:
        elegivel = False; motivo_inelegibilidade.append(f"Não Preenchimento >= {max_nao_preenchimento + 1}")

    # Regra especial para Nota de Qualidade < 80% (Eliminado)
    if nq is not None and nq < 80:
        elegivel = False; motivo_inelegibilidade.append("Nota Qualidade < 80% (Eliminado)")

    # 5. Calcular Pontuação (APENAS SE ELEGÍVEL)
    pontos = 0
    detalhamento_pontos = {} # Para mostrar o breakdown

    if elegivel:
        # a) Satisfação do Processo
        satisfacao = metricas_manuais.get('satisfacao_processo')
        pts_satisfacao = 0
        if satisfacao is not None:
            if satisfacao >= 100: pts_satisfacao = 25
            elif satisfacao >= 95: pts_satisfacao = 17
            elif satisfacao >= 90: pts_satisfacao = 15
            elif satisfacao >= 85: pts_satisfacao = 14
            elif satisfacao >= 80: pts_satisfacao = 12
        pontos += pts_satisfacao
        detalhamento_pontos['Satisfação Processo'] = f"{pts_satisfacao} pts ({satisfacao if satisfacao is not None else 'N/A'}%)"

        # b) Assiduidade
        pts_assiduidade = 0
        if assid is not None:
            if assid >= 100: pts_assiduidade = 30
            elif assid >= 98: pts_assiduidade = 20
            elif assid >= 95: pts_assiduidade = 15
        pontos += pts_assiduidade
        detalhamento_pontos['Assiduidade'] = f"{pts_assiduidade} pts ({assid if assid is not None else 'N/A'}%)"

        # c) TMA Médio
        pts_tma = 0
        tma_display = 'N/A'
        if tma_medio is not None:
             tma_display = f"{tma_medio:.1f} dias"
             if tma_medio <= 30: pts_tma = 45
             elif tma_medio <= 35: pts_tma = 32
             elif tma_medio <= 40: pts_tma = 24
             elif tma_medio <= 45: pts_tma = 16
             else: pts_tma = 8 # Acima de 46 dias
        pontos += pts_tma
        detalhamento_pontos['TMA Médio'] = f"{pts_tma} pts ({tma_display})"

        # d) Reuniões Realizadas por Dia (Média)
        pts_reunioes_dia = 0
        if media_reunioes_dia >= 5: pts_reunioes_dia = 40
        elif media_reunioes_dia >= 4: pts_reunioes_dia = 35
        elif media_reunioes_dia >= 3: pts_reunioes_dia = 25
        elif media_reunioes_dia >= 2: pts_reunioes_dia = 10
        pontos += pts_reunioes_dia
        detalhamento_pontos['Média Reuniões/Dia'] = f"{pts_reunioes_dia} pts ({media_reunioes_dia:.2f})"

        # e) Ações Realizadas por Dia (Média)
        pts_acoes_dia = 0
        if media_acoes_dia >= 7: pts_acoes_dia = 20
        elif media_acoes_dia >= 6: pts_acoes_dia = 15
        elif media_acoes_dia >= 5: pts_acoes_dia = 10
        elif media_acoes_dia >= 4: pts_acoes_dia = 5
        elif media_acoes_dia >= 3: pts_acoes_dia = 3
        pontos += pts_acoes_dia
        detalhamento_pontos['Média Ações/Dia'] = f"{pts_acoes_dia} pts ({media_acoes_dia:.2f})"

        # f) Planos de Sucesso em Dia
        pts_planos = 0
        if psp is not None:
            if psp >= 100: pts_planos = 45
            elif psp >= 95: pts_planos = 35
            elif psp >= 90: pts_planos = 30
            elif psp >= 85: pts_planos = 20
            elif psp >= 80: pts_planos = 10
        pontos += pts_planos
        detalhamento_pontos['Planos Sucesso'] = f"{pts_planos} pts ({psp if psp is not None else 'N/A'}%)"

        # g) Implantações / Planos Iniciados
        pts_iniciadas = 0
        if count_iniciadas >= 10: pts_iniciadas = 45
        elif count_iniciadas >= 9: pts_iniciadas = 32
        elif count_iniciadas >= 8: pts_iniciadas = 24
        elif count_iniciadas >= 7: pts_iniciadas = 16
        elif count_iniciadas >= 6: pts_iniciadas = 8
        pontos += pts_iniciadas
        detalhamento_pontos['Impl. Iniciadas'] = f"{pts_iniciadas} pts ({count_iniciadas})"

        # h) Avaliação de Qualidade
        pts_qualidade = 0
        if nq is not None:
             if nq >= 100: pts_qualidade = 55
             elif nq >= 95: pts_qualidade = 40
             elif nq >= 90: pts_qualidade = 30
             elif nq >= 85: pts_qualidade = 15
             elif nq >= 80: pts_qualidade = 0
        pontos += pts_qualidade
        detalhamento_pontos['Nota Qualidade'] = f"{pts_qualidade} pts ({nq if nq is not None else 'N/A'}%)"

        # i) Bônus (Ganho de Pontos) - Usando .get com default 0
        pts_bonus = 0
        elogios = metricas_manuais.get('elogios', 0)
        pts_bonus_elogios = min(elogios, 1) * 15 # Máximo 1 por mês
        pts_bonus += pts_bonus_elogios
        detalhamento_pontos['Bônus Elogios'] = f"+{pts_bonus_elogios} pts ({elogios} ocorr.)"

        recomendacoes = metricas_manuais.get('recomendacoes', 0)
        pts_bonus_recom = recomendacoes * 1
        pts_bonus += pts_bonus_recom
        detalhamento_pontos['Bônus Recomendações'] = f"+{pts_bonus_recom} pts ({recomendacoes} ocorr.)"

        certificacoes = metricas_manuais.get('certificacoes', 0)
        pts_bonus_cert = min(certificacoes, 1) * 15 # Máximo 1 por mês
        pts_bonus += pts_bonus_cert
        detalhamento_pontos['Bônus Certificações'] = f"+{pts_bonus_cert} pts ({certificacoes} ocorr.)"

        trein_part = metricas_manuais.get('treinamentos_pacto_part', 0)
        pts_bonus_tpart = trein_part * 15
        pts_bonus += pts_bonus_tpart
        detalhamento_pontos['Bônus Trein. Pacto (Part.)'] = f"+{pts_bonus_tpart} pts ({trein_part} ocorr.)"

        trein_aplic = metricas_manuais.get('treinamentos_pacto_aplic', 0)
        pts_bonus_taplic = trein_aplic * 30
        pts_bonus += pts_bonus_taplic
        detalhamento_pontos['Bônus Trein. Pacto (Aplic.)'] = f"+{pts_bonus_taplic} pts ({trein_aplic} ocorr.)"

        reun_pres = metricas_manuais.get('reunioes_presenciais', 0)
        pts_bonus_reun_pres = 0
        if reun_pres > 10: pts_bonus_reun_pres = 35
        elif reun_pres >= 7: pts_bonus_reun_pres = 30
        elif reun_pres >= 5: pts_bonus_reun_pres = 25
        elif reun_pres >= 3: pts_bonus_reun_pres = 20
        elif reun_pres >= 1: pts_bonus_reun_pres = 15
        pts_bonus += pts_bonus_reun_pres
        detalhamento_pontos['Bônus Reuniões Presenciais'] = f"+{pts_bonus_reun_pres} pts ({reun_pres} ocorr.)"

        pontos += pts_bonus # Adiciona bônus ao total

        # j) Penalidades (Perda de Pontos) - Usando .get com default 0
        pts_penalidade = 0
        reclamacoes = metricas_manuais.get('reclamacoes', 0)
        pts_pen_reclam = reclamacoes * 50
        pts_penalidade += pts_pen_reclam
        detalhamento_pontos['Penalidade Reclamação'] = f"-{pts_pen_reclam} pts ({reclamacoes} ocorr.)"

        perda_prazo = metricas_manuais.get('perda_prazo', 0)
        pts_pen_prazo = perda_prazo * 10
        pts_penalidade += pts_pen_prazo
        detalhamento_pontos['Penalidade Perda Prazo'] = f"-{pts_pen_prazo} pts ({perda_prazo} ocorr.)"

        desc_incomp = metricas_manuais.get('desc_incompreensivel', 0)
        pts_pen_desc = desc_incomp * 10
        pts_penalidade += pts_pen_desc
        detalhamento_pontos['Penalidade Desc. Incomp.'] = f"-{pts_pen_desc} pts ({desc_incomp} ocorr.)"

        cancel_resp = metricas_manuais.get('cancelamentos_resp', 0)
        pts_pen_cancel = cancel_resp * 100
        pts_penalidade += pts_pen_cancel
        detalhamento_pontos['Penalidade Cancelamento Resp.'] = f"-{pts_pen_cancel} pts ({cancel_resp} ocorr.)"

        nao_envolv = metricas_manuais.get('nao_envolvimento', 0)
        pts_pen_envolv = nao_envolv * 10
        pts_penalidade += pts_pen_envolv
        detalhamento_pontos['Penalidade Não Envolv.'] = f"-{pts_pen_envolv} pts ({nao_envolv} ocorr.)"

        nao_preench = metricas_manuais.get('nao_preenchimento', 0)
        pts_pen_preench = nao_preench * 10
        pts_penalidade += pts_pen_preench
        detalhamento_pontos['Penalidade Não Preench.'] = f"-{pts_pen_preench} pts ({nao_preench} ocorr.)"

        perda_sla = metricas_manuais.get('perda_sla_grupo', 0)
        pts_pen_sla = perda_sla * 5
        pts_penalidade += pts_pen_sla
        detalhamento_pontos['Penalidade SLA Grupo'] = f"-{pts_pen_sla} pts ({perda_sla} ocorr.)"

        final_incomp = metricas_manuais.get('finalizacao_incompleta', 0)
        pts_pen_final = final_incomp * 10
        pts_penalidade += pts_pen_final
        detalhamento_pontos['Penalidade Finaliz. Incomp.'] = f"-{pts_pen_final} pts ({final_incomp} ocorr.)"

        hora_extra = metricas_manuais.get('hora_extra', 0)
        pts_pen_he = hora_extra * 10
        pts_penalidade += pts_pen_he
        detalhamento_pontos['Penalidade Hora Extra'] = f"-{pts_pen_he} pts ({hora_extra} ocorr.)"

        pontos -= pts_penalidade # Subtrai penalidades

    # 6. Preparar Resultado Final
    resultado = {
        'elegivel': elegivel,
        'motivo_inelegibilidade': ", ".join(motivo_inelegibilidade) if motivo_inelegibilidade else None,
        'pontuacao_final': max(0, pontos) if elegivel else 0, # Garante que a pontuação não seja negativa
        'detalhamento_pontos': detalhamento_pontos if elegivel else {},
        'impl_finalizadas_mes': count_finalizadas,
        # Formata TMA para exibição ou N/A
        'tma_medio_mes': f"{tma_medio:.1f}" if tma_medio is not None else 'N/A',
        'impl_iniciadas_mes': count_iniciadas,
        'media_reunioes_dia': media_reunioes_dia,
        'media_acoes_dia': media_acoes_dia,
        'metricas_manuais_usadas': metricas_manuais # Para depuração ou exibição
    }

    # 7. Opcional, mas recomendado: Atualizar o DB com os resultados calculados
    try:
         existing_record_id = query_db(
             "SELECT id FROM gamificacao_metricas_mensais WHERE usuario_cs = %s AND mes = %s AND ano = %s",
             (usuario_cs, mes, ano), one=True
         )
         calculated_data = {
             'pontuacao_calculada': resultado['pontuacao_final'],
             'elegivel': resultado['elegivel'],
             'impl_finalizadas_mes': count_finalizadas,
             'tma_medio_mes': tma_medio, # Salva o número ou None
             'impl_iniciadas_mes': count_iniciadas,
             'reunioes_concluidas_dia_media': media_reunioes_dia,
             'acoes_concluidas_dia_media': media_acoes_dia,
             # Atualiza data_registro para refletir o último cálculo
             'data_registro': datetime.now()
         }
         if existing_record_id:
             # UPDATE
             set_clauses_calc = [f"{key} = %s" for key in calculated_data.keys()]
             sql_update_calc = f"""
                 UPDATE gamificacao_metricas_mensais
                 SET {', '.join(set_clauses_calc)}
                 WHERE id = %s
             """
             args_update_calc = list(calculated_data.values()) + [existing_record_id['id']]
             execute_db(sql_update_calc, tuple(args_update_calc))
         else:
             # INSERT (Apenas com dados calculados e identificadores)
             columns_calc = ['usuario_cs', 'mes', 'ano'] + list(calculated_data.keys())
             values_placeholders_calc = ['%s'] * len(columns_calc)
             sql_insert_calc = f"INSERT INTO gamificacao_metricas_mensais ({', '.join(columns_calc)}) VALUES ({', '.join(values_placeholders_calc)})"
             args_insert_calc = [usuario_cs, mes, ano] + list(calculated_data.values())
             execute_db(sql_insert_calc, tuple(args_insert_calc))

    except Exception as db_update_err:
        print(f"AVISO: Falha ao salvar resultados calculados da gamificação para {usuario_cs} ({mes}/{ano}): {db_update_err}")


    return resultado