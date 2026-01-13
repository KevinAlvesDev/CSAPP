"""
Query Helpers - Funções reutilizáveis para queries comuns
Elimina duplicação de código em todo o projeto
"""

from typing import List, Dict, Optional, Any
from datetime import datetime, date
from flask import current_app
from ..db import query_db


def get_implantacoes_with_progress(
    usuario_cs: Optional[str] = None,
    status: Optional[str] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    sort_by_status: bool = False,
    context: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Busca implantações com progresso calculado (SEM N+1).
    
    Args:
        usuario_cs: Filtrar por usuário CS
        status: Filtrar por status
        limit: Limitar resultados
        offset: Pular resultados (paginação)
        sort_by_status: Ordenar por status (ordem específica do dashboard)
        
    Returns:
        Lista de implantações com progresso já calculado
    """
    
    # Detectar tipo de banco
    use_sqlite = current_app.config.get('USE_SQLITE_LOCALLY', False)
    
    # Sintaxe de cast diferente para SQLite vs PostgreSQL
    if use_sqlite:
        progress_calc = """
            CASE 
                WHEN COALESCE(prog.total_tarefas, 0) > 0 
                THEN ROUND((CAST(COALESCE(prog.tarefas_concluidas, 0) AS REAL) / CAST(prog.total_tarefas AS REAL)) * 100)
                ELSE 100
            END as progresso_percent
        """
        completed_check = "ci.completed = 1"
        placeholder = "?"
    else:
        progress_calc = """
            CASE 
                WHEN COALESCE(prog.total_tarefas, 0) > 0 
                THEN ROUND((COALESCE(prog.tarefas_concluidas, 0)::NUMERIC / prog.total_tarefas::NUMERIC) * 100)
                ELSE 100
            END as progresso_percent
        """
        completed_check = "ci.completed = TRUE"
        placeholder = "%s"
    
    query = f"""
        SELECT
            i.*,
            p.nome as cs_nome,
            
            -- Progresso calculado no SQL (evita N+1)
            COALESCE(prog.total_tarefas, 0) as total_tarefas,
            COALESCE(prog.tarefas_concluidas, 0) as tarefas_concluidas,
            {progress_calc},
            
            -- Última atividade (comentários)
            last_activity.ultima_atividade as ultima_atividade
            
        FROM implantacoes i
        LEFT JOIN perfil_usuario p ON i.usuario_cs = p.usuario
        LEFT JOIN (
            SELECT
                ci.implantacao_id,
                COUNT(DISTINCT CASE WHEN ci.tipo_item = 'subtarefa' THEN ci.id END) as total_tarefas,
                COUNT(DISTINCT CASE WHEN ci.tipo_item = 'subtarefa' AND {completed_check} THEN ci.id END) as tarefas_concluidas
            FROM checklist_items ci
            WHERE ci.tipo_item = 'subtarefa'
            GROUP BY ci.implantacao_id
        ) prog ON prog.implantacao_id = i.id
        LEFT JOIN (
            SELECT
                ci.implantacao_id,
                MAX(ch.data_criacao) as ultima_atividade
            FROM comentarios_h ch
            INNER JOIN checklist_items ci ON ch.checklist_item_id = ci.id
            GROUP BY ci.implantacao_id
        ) last_activity ON last_activity.implantacao_id = i.id
        WHERE 1=1
    """
    
    args = []
    
    if usuario_cs:
        query += f" AND i.usuario_cs = {placeholder}"
        args.append(usuario_cs)
    
    if status:
        query += f" AND i.status = {placeholder}"
        args.append(status)
    
    if context:
        query += f" AND i.contexto = {placeholder}"
        args.append(context)
    
    if sort_by_status:
        query += """
         ORDER BY CASE i.status
                     WHEN 'nova' THEN 1
                     WHEN 'andamento' THEN 2
                     WHEN 'parada' THEN 3
                     WHEN 'futura' THEN 4
                     WHEN 'finalizada' THEN 5
                     WHEN 'cancelada' THEN 6
                     ELSE 7
                 END, i.data_criacao DESC
        """
    else:
        query += " ORDER BY i.data_criacao DESC"
    
    if limit:
        query += f" LIMIT {placeholder}"
        args.append(limit)
    
    if offset is not None:
        query += f" OFFSET {placeholder}"
        args.append(offset)
    
    return query_db(query, tuple(args)) or []


def get_implantacao_with_details(implantacao_id: int) -> Optional[Dict[str, Any]]:
    """
    Busca uma implantação com todos os detalhes (SEM N+1).
    
    Args:
        implantacao_id: ID da implantação
        
    Returns:
        Implantação com detalhes ou None
    """
    
    query = """
        SELECT
            i.*,
            p.nome as cs_nome,
            p.cargo as cs_cargo,
            p.foto_url as cs_foto,
            
            -- Progresso
            COALESCE(prog.total_tarefas, 0) as total_tarefas,
            COALESCE(prog.tarefas_concluidas, 0) as tarefas_concluidas,
            
            -- Última atividade
            last_activity.ultima_atividade as ultima_atividade,
            
            -- Plano
            pl.nome as plano_nome
            
        FROM implantacoes i
        LEFT JOIN perfil_usuario p ON i.usuario_cs = p.usuario
        LEFT JOIN (
            SELECT
                ci.implantacao_id,
                COUNT(DISTINCT CASE WHEN ci.tipo_item = 'subtarefa' THEN ci.id END) as total_tarefas,
                COUNT(DISTINCT CASE WHEN ci.tipo_item = 'subtarefa' AND ci.completed = TRUE THEN ci.id END) as tarefas_concluidas
            FROM checklist_items ci
            WHERE ci.tipo_item = 'subtarefa'
            GROUP BY ci.implantacao_id
        ) prog ON prog.implantacao_id = i.id
        LEFT JOIN (
            SELECT
                ci.implantacao_id,
                MAX(ch.data_criacao) as ultima_atividade
            FROM comentarios_h ch
            INNER JOIN checklist_items ci ON ch.checklist_item_id = ci.id
            GROUP BY ci.implantacao_id
        ) last_activity ON last_activity.implantacao_id = i.id
        LEFT JOIN planos_sucesso pl ON i.plano_sucesso_id = pl.id
        WHERE i.id = %s
    """
    
    return query_db(query, (implantacao_id,), one=True)


def get_checklist_tree_optimized(implantacao_id: int) -> List[Dict[str, Any]]:
    """
    Busca árvore de checklist otimizada (SEM subqueries correlacionadas).
    
    Args:
        implantacao_id: ID da implantação
        
    Returns:
        Lista de itens com contadores de filhos
    """
    
    query = """
        SELECT
            ci.*,
            COUNT(sub.id) as total_filhos,
            SUM(CASE WHEN sub.completed THEN 1 ELSE 0 END) as filhos_concluidos
        FROM checklist_items ci
        LEFT JOIN checklist_items sub ON sub.parent_id = ci.id
        WHERE ci.implantacao_id = %s
        GROUP BY ci.id
        ORDER BY ci.ordem, ci.id
    """
    
    return query_db(query, (implantacao_id,)) or []


def get_implantacoes_count(
    usuario_cs: Optional[str] = None,
    status: Optional[str] = None
) -> int:
    """
    Conta total de implantações para paginação.
    
    Args:
        usuario_cs: Filtrar por usuário CS
        status: Filtrar por status
        
    Returns:
        Total de registros
    """
    # Detectar tipo de banco
    use_sqlite = current_app.config.get('USE_SQLITE_LOCALLY', False)
    placeholder = "?" if use_sqlite else "%s"
    
    query = "SELECT COUNT(*) as total FROM implantacoes i WHERE 1=1"
    args = []
    
    if usuario_cs:
        query += f" AND i.usuario_cs = {placeholder}"
        args.append(usuario_cs)
        
    if status:
        query += f" AND i.status = {placeholder}"
        args.append(status)
        
    res = query_db(query, tuple(args), one=True)
    return res.get('total', 0) if res else 0
