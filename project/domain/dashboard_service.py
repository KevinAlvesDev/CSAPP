# project/domain/dashboard_service.py
# (Função movida de project/services.py)

from flask import g
from ..db import query_db, execute_db
from ..constants import (
    PERFIL_ADMIN, PERFIL_GERENTE, PERFIL_COORDENADOR
)
from ..utils import format_date_iso_for_json, format_date_br
from datetime import datetime, date 

# --- Função de Lógica do Dashboard ---

def get_dashboard_data(user_email, filtered_cs_email=None):
    """
    Busca e processa todos os dados para o dashboard.
    """
    perfil_acesso = g.perfil.get('perfil_acesso') if g.get('perfil') else None
    manager_profiles = [PERFIL_ADMIN, PERFIL_GERENTE, PERFIL_COORDENADOR]
    
    is_manager_view = perfil_acesso in manager_profiles

    # 1. Busca implantações
    query_sql = """
        SELECT i.*, p.nome as cs_nome
        FROM implantacoes i
        LEFT JOIN perfil_usuario p ON i.usuario_cs = p.usuario
    """
    args = []
    
    if not is_manager_view:
        query_sql += " WHERE i.usuario_cs = %s "
        args.append(user_email)
    elif is_manager_view and filtered_cs_email:
        query_sql += " WHERE i.usuario_cs = %s "
        args.append(filtered_cs_email)
    
    query_sql += """
        ORDER BY CASE status
                     WHEN 'nova' THEN 1
                     WHEN 'andamento' THEN 2
                     WHEN 'parada' THEN 3
                     WHEN 'futura' THEN 4
                     WHEN 'finalizada' THEN 5
                     ELSE 6
                 END, data_criacao DESC
    """
    
    impl_list = query_db(query_sql, tuple(args))
    impl_list = impl_list if impl_list is not None else []


    dashboard_data = {
        'andamento': [], 'atrasadas': [], 'futuras': [],
        'finalizadas': [], 'paradas': [], 'novas': [] 
    }
    metrics = {
        'impl_andamento_total': 0, 'implantacoes_atrasadas': 0,
        'implantacoes_futuras': 0, 'impl_finalizadas': 0, 'impl_paradas': 0,
        'impl_novas': 0, 
        'total_valor_andamento': 0.0,
        'total_valor_atrasadas': 0.0,
        'total_valor_futuras': 0.0,
        'total_valor_finalizadas': 0.0,
        'total_valor_paradas': 0.0,
        'total_valor_novas': 0.0, 
    }

    impl_ids = [impl['id'] for impl in impl_list if impl and 'id' in impl] 
    tasks_by_impl = {}
    if impl_ids:
        if impl_ids:
            placeholders = ','.join(['%s'] * len(impl_ids)) 
            sql = f"SELECT implantacao_id, concluida FROM tarefas WHERE implantacao_id IN ({placeholders})"
            all_tasks = query_db(sql, tuple(impl_ids))
        else:
            all_tasks = [] 

        if all_tasks: 
            for task in all_tasks:
                impl_id_key = task.get('implantacao_id')
                if impl_id_key is not None: 
                    if impl_id_key not in tasks_by_impl:
                        tasks_by_impl[impl_id_key] = []
                    tasks_by_impl[impl_id_key].append(task)

    agora = datetime.now() 

    for impl in impl_list:
        if not impl or not isinstance(impl, dict):
            continue

        impl_id = impl.get('id')
        if impl_id is None:
            continue

        status = impl.get('status')

        impl['data_criacao_iso'] = format_date_iso_for_json(impl.get('data_criacao'), only_date=True)
        impl['data_inicio_efetivo_iso'] = format_date_iso_for_json(impl.get('data_inicio_efetivo'), only_date=True)
        impl['data_inicio_producao_iso'] = format_date_iso_for_json(impl.get('data_inicio_producao'), only_date=True)
        impl['data_final_implantacao_iso'] = format_date_iso_for_json(impl.get('data_final_implantacao'), only_date=True)

        impl_tasks = tasks_by_impl.get(impl_id, []) 
        total_tasks = len(impl_tasks)
        done_tasks = sum(1 for t in impl_tasks if t.get('concluida')) 
        impl['progresso'] = int(round((done_tasks / total_tasks) * 100)) if total_tasks > 0 else 0

        try:
            impl_valor = float(impl.get('valor_atribuido', 0.0))
        except (ValueError, TypeError):
            impl_valor = 0.0
        impl['valor_atribuido'] = impl_valor


        dias_passados = 0
        data_inicio_obj = impl.get('data_inicio_efetivo') 
        
        if data_inicio_obj:
            data_inicio_datetime = None
            if isinstance(data_inicio_obj, str):
                try:
                    data_inicio_datetime = datetime.fromisoformat(data_inicio_obj.replace('Z', '+00:00'))
                except ValueError:
                    try:
                        if '.' in data_inicio_obj:
                            data_inicio_datetime = datetime.strptime(data_inicio_obj, '%Y-%m-%d %H:%M:%S.%f')
                        else:
                            data_inicio_datetime = datetime.strptime(data_inicio_obj, '%Y-%m-%d %H:%M:%S')
                    except ValueError:
                         try:
                            data_inicio_datetime = datetime.strptime(data_inicio_obj, '%Y-%m-%d')
                         except ValueError:
                            print(f"AVISO: Formato de data_inicio_efetivo (str) inválido para impl {impl_id}: {data_inicio_obj}")
            
            elif isinstance(data_inicio_obj, date) and not isinstance(data_inicio_obj, datetime):
                data_inicio_datetime = datetime.combine(data_inicio_obj, datetime.min.time())
            
            elif isinstance(data_inicio_obj, datetime):
                data_inicio_datetime = data_inicio_obj

            if data_inicio_datetime:
                try:
                    agora_naive = agora.replace(tzinfo=None) if agora.tzinfo else agora
                    inicio_naive = data_inicio_datetime.replace(tzinfo=None) if data_inicio_datetime.tzinfo else data_inicio_datetime
                    dias_passados_delta = agora_naive - inicio_naive
                    dias_passados = dias_passados_delta.days if dias_passados_delta.days >= 0 else 0
                except TypeError as te:
                    print(f"AVISO: Erro de tipo ao calcular dias passados para impl {impl_id}. Verifique timezones. Erro: {te}")
                    dias_passados = -1 
                    
        impl['dias_passados'] = dias_passados 

        if status == 'finalizada':
            dashboard_data['finalizadas'].append(impl)
            metrics['impl_finalizadas'] += 1
            metrics['total_valor_finalizadas'] += impl_valor
        elif status == 'parada':
            dashboard_data['paradas'].append(impl)
            metrics['impl_paradas'] += 1
            metrics['total_valor_paradas'] += impl_valor
        elif status == 'futura': 
            dashboard_data['futuras'].append(impl)
            metrics['implantacoes_futuras'] += 1
            metrics['total_valor_futuras'] += impl_valor
            
            data_prevista_str = impl.get('data_inicio_previsto')
            data_prevista_obj = None

            if data_prevista_str and isinstance(data_prevista_str, str):
                try:
                    data_prevista_obj = datetime.strptime(data_prevista_str, '%Y-%m-%d').date()
                except ValueError:
                    print(f"AVISO: Formato de data_inicio_previsto (str) inválido para impl {impl_id}: {data_prevista_str}")
            elif isinstance(data_prevista_str, date):
                data_prevista_obj = data_prevista_str

            impl['data_inicio_previsto_fmt_d'] = format_date_br(data_prevista_obj or data_prevista_str, include_time=False)
            
            if data_prevista_obj and data_prevista_obj < agora.date():
                impl['atrasada_para_iniciar'] = True
            else:
                impl['atrasada_para_iniciar'] = False

        elif status == 'nova':
            dashboard_data['novas'].append(impl)
            metrics['impl_novas'] += 1
            metrics['total_valor_novas'] += impl_valor

        elif status == 'andamento':
            metrics['impl_andamento_total'] += 1 
            
            if dias_passados > 25:
                dashboard_data['atrasadas'].append(impl)
                metrics['implantacoes_atrasadas'] += 1
                metrics['total_valor_atrasadas'] += impl_valor
            else:
                dashboard_data['andamento'].append(impl)
                metrics['total_valor_andamento'] += impl_valor 

        else:
            print(f"AVISO: Implantação ID {impl_id} com status desconhecido ou nulo: '{status}'. Ignorando na categorização.")

    if not is_manager_view and not filtered_cs_email and impl_list:
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