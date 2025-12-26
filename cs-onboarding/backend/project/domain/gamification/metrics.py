"""
Módulo de Métricas de Gamificação
Buscar e salvar métricas mensais de gamificação.
Princípio SOLID: Single Responsibility
"""
from datetime import date, datetime

from ...db import execute_db, query_db


def _get_gamification_automatic_data_bulk(mes, ano, primeiro_dia_str, fim_ultimo_dia_str, target_cs_email=None):
    """Busca todos os dados automáticos de todos os usuários de uma vez."""

    sql_finalizadas = """
        SELECT usuario_cs, data_criacao, data_finalizacao FROM implantacoes
        WHERE status = 'finalizada'
        AND data_finalizacao >= %s AND data_finalizacao <= %s
    """
    args_finalizadas = [primeiro_dia_str, fim_ultimo_dia_str]
    if target_cs_email:
        sql_finalizadas += " AND usuario_cs = %s"
        args_finalizadas.append(target_cs_email)

    impl_finalizadas_raw = query_db(sql_finalizadas, tuple(args_finalizadas))
    impl_finalizadas_raw = impl_finalizadas_raw if impl_finalizadas_raw is not None else []

    tma_data_map = {}
    for impl in impl_finalizadas_raw:
        if not isinstance(impl, dict): continue
        email = impl.get('usuario_cs')
        dt_criacao = impl.get('data_criacao')
        dt_finalizacao = impl.get('data_finalizacao')
        if not email or not dt_criacao or not dt_finalizacao:
            continue

        if email not in tma_data_map:
            tma_data_map[email] = {'total_dias': 0, 'count': 0}

        dt_criacao_datetime = None
        dt_finalizacao_datetime = None
        if isinstance(dt_criacao, str):
            try:
                dt_criacao_datetime = datetime.fromisoformat(dt_criacao.replace('Z', '+00:00'))
            except ValueError:
                try:
                    if '.' in dt_criacao:
                        dt_criacao_datetime = datetime.strptime(dt_criacao, '%Y-%m-%d %H:%M:%S.%f')
                    else:
                        dt_criacao_datetime = datetime.strptime(dt_criacao, '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    pass
        elif isinstance(dt_criacao, date) and not isinstance(dt_criacao, datetime):
            dt_criacao_datetime = datetime.combine(dt_criacao, datetime.min.time())
        elif isinstance(dt_criacao, datetime):
            dt_criacao_datetime = dt_criacao

        if isinstance(dt_finalizacao, str):
            try:
                dt_finalizacao_datetime = datetime.fromisoformat(dt_finalizacao.replace('Z', '+00:00'))
            except ValueError:
                try:
                    if '.' in dt_finalizacao:
                        dt_finalizacao_datetime = datetime.strptime(dt_finalizacao, '%Y-%m-%d %H:%M:%S.%f')
                    else:
                        dt_finalizacao_datetime = datetime.strptime(dt_finalizacao, '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    pass
        elif isinstance(dt_finalizacao, date) and not isinstance(dt_finalizacao, datetime):
            dt_finalizacao_datetime = datetime.combine(dt_finalizacao, datetime.min.time())
        elif isinstance(dt_finalizacao, datetime):
            dt_finalizacao_datetime = dt_finalizacao

        if dt_criacao_datetime and dt_finalizacao_datetime:
            criacao_naive = dt_criacao_datetime.replace(tzinfo=None) if dt_criacao_datetime.tzinfo else dt_criacao_datetime
            final_naive = dt_finalizacao_datetime.replace(tzinfo=None) if dt_finalizacao_datetime.tzinfo else dt_finalizacao_datetime
            try:
                delta = final_naive - criacao_naive
                tma_data_map[email]['total_dias'] += max(0, delta.days)
                tma_data_map[email]['count'] += 1
            except TypeError:
                pass

    sql_iniciadas = "SELECT usuario_cs, COUNT(*) as total FROM implantacoes WHERE data_inicio_efetivo >= %s AND data_inicio_efetivo <= %s"
    args_iniciadas = [primeiro_dia_str, fim_ultimo_dia_str]
    if target_cs_email:
        sql_iniciadas += " AND usuario_cs = %s"
        args_iniciadas.append(target_cs_email)
    sql_iniciadas += " GROUP BY usuario_cs"

    impl_iniciadas_raw = query_db(sql_iniciadas, tuple(args_iniciadas))
    impl_iniciadas_raw = impl_iniciadas_raw if impl_iniciadas_raw is not None else []
    iniciadas_map = {row['usuario_cs']: row['total'] for row in impl_iniciadas_raw if isinstance(row, dict)}

    sql_tarefas = """
        SELECT i.usuario_cs, COALESCE(ci.tag, 'Ação interna') as tag, COUNT(DISTINCT ci.id) as total
        FROM checklist_items ci
        JOIN implantacoes i ON ci.implantacao_id = i.id
        WHERE ci.tipo_item = 'subtarefa'
        AND ci.completed = TRUE 
        AND ci.tag IN ('Ação interna', 'Reunião')
        AND ci.data_conclusao >= %s AND ci.data_conclusao <= %s
    """
    args_tarefas = [primeiro_dia_str, fim_ultimo_dia_str]
    if target_cs_email:
        sql_tarefas += " AND i.usuario_cs = %s"
        args_tarefas.append(target_cs_email)
    sql_tarefas += " GROUP BY i.usuario_cs, ci.tag"

    tarefas_concluidas_raw = query_db(sql_tarefas, tuple(args_tarefas))
    tarefas_concluidas_raw = tarefas_concluidas_raw if tarefas_concluidas_raw is not None else []

    tarefas_map = {}
    for row in tarefas_concluidas_raw:
        if not isinstance(row, dict): continue
        email = row.get('usuario_cs')
        tag = row.get('tag')
        total = row.get('total', 0)
        if not email or not tag: continue

        if email not in tarefas_map:
            tarefas_map[email] = {'Ação interna': 0, 'Reunião': 0}

        if tag == 'Ação interna':
            tarefas_map[email]['Ação interna'] = total
        elif tag == 'Reunião':
            tarefas_map[email]['Reunião'] = total

    return tma_data_map, iniciadas_map, tarefas_map


def obter_metricas_mensais(usuario_cs, mes, ano):
    """Busca as métricas mensais de um usuário específico."""
    return query_db(
        "SELECT * FROM gamificacao_metricas_mensais WHERE usuario_cs = %s AND mes = %s AND ano = %s",
        (usuario_cs, mes, ano),
        one=True
    )


def salvar_metricas_mensais(data_to_save, existing_record_id=None):
    """
    Salva ou atualiza métricas mensais de gamificação.
    
    Args:
        data_to_save: Dicionário com os dados a salvar
        existing_record_id: ID do registro existente (None para inserir novo)
        
    Returns:
        bool: True se sucesso
    """
    if existing_record_id:
        # Atualizar registro existente
        set_clauses = [f"{key} = %s" for key in data_to_save.keys() if key not in ['usuario_cs', 'mes', 'ano']]
        sql_update = f"""
            UPDATE gamificacao_metricas_mensais
            SET {', '.join(set_clauses)}
            WHERE id = %s
        """
        args = list(data_to_save.values())[3:] + [existing_record_id]
        execute_db(sql_update, tuple(args))
    else:
        # Inserir novo registro
        columns = data_to_save.keys()
        values_placeholders = ['%s'] * len(columns)
        sql_insert = f"INSERT INTO gamificacao_metricas_mensais ({', '.join(columns)}) VALUES ({', '.join(values_placeholders)})"
        args = list(data_to_save.values())
        execute_db(sql_insert, tuple(args))
    
    return True
