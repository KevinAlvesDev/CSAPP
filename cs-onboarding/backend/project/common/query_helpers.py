"""
Query Helpers - Funções reutilizáveis para queries comuns
Elimina duplicação de código em todo o projeto
"""

from typing import List, Dict, Optional, Any
from datetime import datetime, date
from ..db import query_db


def get_implantacoes_with_progress(
    usuario_cs: Optional[str] = None,
    status: Optional[str] = None,
    limit: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Busca implantações com progresso calculado (SEM N+1).
    
    Args:
        usuario_cs: Filtrar por usuário CS
        status: Filtrar por status
        limit: Limitar resultados
        
    Returns:
        Lista de implantações com progresso já calculado
    """
    
    query = """
        SELECT
            i.*,
            p.nome as cs_nome,
            
            -- Progresso calculado no SQL (evita N+1)
            COALESCE(prog.total_tarefas, 0) as total_tarefas,
            COALESCE(prog.tarefas_concluidas, 0) as tarefas_concluidas,
            CASE 
                WHEN COALESCE(prog.total_tarefas, 0) > 0 
                THEN ROUND((COALESCE(prog.tarefas_concluidas, 0)::NUMERIC / prog.total_tarefas::NUMERIC) * 100)
                ELSE 100
            END as progresso_percent
            
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
        WHERE 1=1
    """
    
    args = []
    
    if usuario_cs:
        query += " AND i.usuario_cs = %s"
        args.append(usuario_cs)
    
    if status:
        query += " AND i.status = %s"
        args.append(status)
    
    query += " ORDER BY i.data_criacao DESC"
    
    if limit:
        query += " LIMIT %s"
        args.append(limit)
    
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
