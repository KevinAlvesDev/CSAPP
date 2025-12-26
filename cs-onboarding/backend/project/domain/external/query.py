"""
Módulo de Queries do External Service
Construção e execução de queries SQL para o banco OAMD.
Princípio SOLID: Single Responsibility
"""
import re

from ...config.logging_config import api_logger
from ...database.external_db import query_external_db


# Query base com todos os JOINs necessários
OAMD_BASE_QUERY = """
    SELECT 
        ef.codigo,
        ef.codigofinanceiro,
        ef.nomefantasia,
        ef.razaosocial,
        ef.cnpj,
        ef.email,
        ef.telefone,
        ef.datacadastro,
        ef.chavezw,
        ef.nomeempresazw,
        ef.empresazw,
        ef.grupofavorecido,
        ef.tipogrupofavorecido,
        ef.nicho,
        ef.detalheempresa_codigo,
        
        de.inicioimplantacao,
        de.finalimplantacao,
        de.inicioproducao,
        de.statusimplantacao,
        de.nivelatendimento,
        de.nivelreceitamensal,
        de.tipocliente,
        de.categoria,
        de.condicaoespecial,
        
        ps.datainicio as plano_datainicio,
        ps.datafinal as plano_datafinal,
        ps.dataconclusao as plano_dataconclusao,
        ps.duracao as plano_duracao,
        ps.porcentagemconcluida as plano_porcentagem,
        ps.nomeresponsavel as plano_responsavel,
        ps.nome as plano_nome
        
    FROM empresafinanceiro ef
    LEFT JOIN detalheempresa de ON de.codigo = ef.detalheempresa_codigo
    LEFT JOIN planosucesso ps ON ps.empresafinanceiro_codigo = ef.codigo
    WHERE {where_clause}
    ORDER BY ps.criadoem DESC
    LIMIT 1
"""


def build_oamd_query(where_clause):
    """
    Constrói a query OAMD completa com a cláusula WHERE especificada.
    
    Args:
        where_clause: Cláusula WHERE para filtrar os resultados
        
    Returns:
        str: Query SQL completa
    """
    return OAMD_BASE_QUERY.format(where_clause=where_clause)


def execute_oamd_search(id_favorecido=None, infra_req=None):
    """
    Executa a busca no banco OAMD usando diferentes estratégias.
    
    Args:
        id_favorecido: ID do favorecido para busca
        infra_req: Código de infraestrutura (ZW_###) para busca
        
    Returns:
        list: Lista de resultados da busca ou lista vazia
        
    Estratégia de busca:
    1. Se infra_req fornecido: busca por empresazw ou nomeempresazw
    2. Se id_favorecido fornecido:
       a. Primeiro tenta ef.codigofinanceiro (preferido)
       b. Depois tenta ef.codigo (fallback)
    """
    results = []
    
    # Busca por Infra (ZW_###)
    if infra_req and not id_favorecido:
        results = _search_by_infra(infra_req)
    else:
        # Busca por ID Favorecido
        results = _search_by_id_favorecido(id_favorecido)
    
    return results


def _search_by_infra(infra_req):
    """
    Busca empresa pelo código de infraestrutura.
    
    Args:
        infra_req: Código de infra (ex: 'ZW_123' ou '123')
        
    Returns:
        list: Resultados da busca
    """
    # Extrair dígitos do código infra
    digits = ''.join(re.findall(r"\d+", str(infra_req)))
    
    try:
        emp_int = int(digits) if digits else None
    except Exception:
        emp_int = None
    
    if emp_int:
        # Busca numérica por empresazw
        where_clause = "ef.empresazw = :empresazw"
        params = {'empresazw': emp_int}
    else:
        # Busca por nome (LIKE)
        where_clause = "LOWER(ef.nomeempresazw) LIKE :nomezw"
        params = {'nomezw': f"%{str(infra_req).lower()}%"}
    
    try:
        query = build_oamd_query(where_clause)
        return query_external_db(query, params) or []
    except Exception as e:
        api_logger.warning(f"Erro ao buscar por infra '{infra_req}': {e}")
        return []


def _search_by_id_favorecido(id_favorecido):
    """
    Busca empresa pelo ID Favorecido.
    Tenta primeiro codigofinanceiro, depois codigo como fallback.
    
    Args:
        id_favorecido: ID do favorecido
        
    Returns:
        list: Resultados da busca
    """
    params = {'id_favorecido': id_favorecido}
    
    # 1. Tentar por ef.codigofinanceiro (preferido)
    try:
        where_clause = "ef.codigofinanceiro = :id_favorecido"
        query = build_oamd_query(where_clause)
        results = query_external_db(query, params) or []
        
        if results:
            api_logger.info(f"Empresa encontrada por codigofinanceiro: {id_favorecido}")
            return results
            
    except Exception as e:
        api_logger.warning(f"Erro ao buscar por ef.codigofinanceiro: {e}")
    
    # 2. Fallback: tentar por ef.codigo
    try:
        where_clause = "ef.codigo = :id_favorecido"
        query = build_oamd_query(where_clause)
        results = query_external_db(query, params) or []
        
        if results:
            api_logger.info(f"Empresa encontrada por codigo (fallback): {id_favorecido}")
            return results
            
    except Exception as e:
        api_logger.warning(f"Erro ao buscar por ef.codigo: {e}")
    
    return []
