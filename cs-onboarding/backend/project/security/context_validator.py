"""
Módulo de Validação de Contexto.
Implementa middleware e decorators para garantir isolamento de dados entre contextos.
Resolve: Problemas de Isolamento de Contexto (ALTO RISCO)
"""

from __future__ import annotations

from functools import wraps
from typing import Callable, Optional, TypeVar, Any

from flask import g, jsonify, request

from ..config.logging_config import security_logger
from ..db import query_db


# Type hint para funções decoradas
F = TypeVar('F', bound=Callable[..., Any])


def get_current_context() -> Optional[str]:
    """
    Obtém o contexto atual da requisição.
    
    Ordem de prioridade:
    1. Query parameter 'context'
    2. Header 'X-Context'
    3. URL path (detecta /grandes_contas/, /onboarding/, /ongoing/)
    4. Sessão do usuário
    
    Returns:
        str: Contexto atual ('onboarding', 'grandes_contas', 'ongoing') ou None
    """
    # 1. Query parameter
    context = request.args.get('context')
    if context and context in ('onboarding', 'grandes_contas', 'ongoing'):
        return context
    
    # 2. Header
    context = request.headers.get('X-Context')
    if context and context in ('onboarding', 'grandes_contas', 'ongoing'):
        return context
    
    # 3. URL path
    path = request.path.lower()
    if '/grandes_contas/' in path or '/grandes-contas/' in path:
        return 'grandes_contas'
    elif '/ongoing/' in path:
        return 'ongoing'
    elif '/onboarding/' in path:
        return 'onboarding'
    
    # 4. Default para onboarding (compatibilidade com dados legados)
    return None


def validate_implantacao_belongs_to_context(
    impl_id: int, 
    expected_context: Optional[str]
) -> bool:
    """
    Verifica se uma implantação pertence ao contexto esperado.
    
    Args:
        impl_id: ID da implantação
        expected_context: Contexto esperado ('onboarding', 'grandes_contas', 'ongoing')
        
    Returns:
        bool: True se a implantação pertence ao contexto ou se contexto é None (bypass)
    """
    if expected_context is None:
        # Sem contexto especificado = permite acesso (modo legado)
        return True
    
    try:
        result = query_db(
            "SELECT contexto FROM implantacoes WHERE id = %s",
            (impl_id,),
            one=True
        )
        
        if not result:
            security_logger.warning(
                f"Validação de contexto: implantação {impl_id} não encontrada"
            )
            return False
        
        impl_context = result.get('contexto')
        
        # Onboarding aceita NULL ou 'onboarding' (compatibilidade legado)
        if expected_context == 'onboarding':
            return impl_context is None or impl_context == 'onboarding'
        
        return impl_context == expected_context
        
    except Exception as e:
        security_logger.error(
            f"Erro ao validar contexto da implantação {impl_id}: {e}"
        )
        # Em caso de erro, nega acesso por segurança
        return False


def validate_checklist_item_belongs_to_context(
    item_id: int, 
    expected_context: Optional[str]
) -> bool:
    """
    Verifica se um item de checklist pertence ao contexto esperado.
    O item herda o contexto da sua implantação.
    
    Args:
        item_id: ID do item de checklist
        expected_context: Contexto esperado
        
    Returns:
        bool: True se o item pertence ao contexto
    """
    if expected_context is None:
        return True
    
    try:
        # Query que busca o contexto via implantação do item
        result = query_db(
            """
            SELECT i.contexto 
            FROM checklist_items ci
            JOIN implantacoes i ON ci.implantacao_id = i.id
            WHERE ci.id = %s
            """,
            (item_id,),
            one=True
        )
        
        if not result:
            security_logger.warning(
                f"Validação de contexto: item {item_id} não encontrado ou sem implantação"
            )
            return False
        
        impl_context = result.get('contexto')
        
        if expected_context == 'onboarding':
            return impl_context is None or impl_context == 'onboarding'
        
        return impl_context == expected_context
        
    except Exception as e:
        security_logger.error(
            f"Erro ao validar contexto do item {item_id}: {e}"
        )
        return False


def validate_context_access(
    id_param: str = 'impl_id',
    entity_type: str = 'implantacao'
) -> Callable[[F], F]:
    """
    Decorator para validar acesso baseado em contexto.
    
    Uso:
        @validate_context_access(id_param='impl_id')
        def get_implantacao_comments(impl_id):
            ...
            
        @validate_context_access(id_param='item_id', entity_type='checklist_item')
        def toggle_item(item_id):
            ...
    
    Args:
        id_param: Nome do parâmetro na URL que contém o ID
        entity_type: Tipo da entidade ('implantacao' ou 'checklist_item')
        
    Returns:
        Decorator function
    """
    def decorator(f: F) -> F:
        @wraps(f)
        def decorated_function(*args: Any, **kwargs: Any) -> Any:
            # Obter o ID da entidade
            entity_id = kwargs.get(id_param) or request.args.get(id_param)
            
            if entity_id is None:
                # Se não tem ID, deixa a função lidar
                return f(*args, **kwargs)
            
            try:
                entity_id = int(entity_id)
            except (ValueError, TypeError):
                return jsonify({
                    "ok": False, 
                    "error": f"ID inválido: {entity_id}"
                }), 400
            
            # Obter o contexto esperado
            expected_context = get_current_context()
            
            # Validar baseado no tipo de entidade
            if entity_type == 'implantacao':
                is_valid = validate_implantacao_belongs_to_context(
                    entity_id, expected_context
                )
            elif entity_type == 'checklist_item':
                is_valid = validate_checklist_item_belongs_to_context(
                    entity_id, expected_context
                )
            else:
                security_logger.warning(
                    f"Tipo de entidade desconhecido: {entity_type}"
                )
                is_valid = True  # Fallback permissivo
            
            if not is_valid:
                security_logger.warning(
                    f"Acesso negado: {entity_type} {entity_id} não pertence ao contexto "
                    f"{expected_context}. User: {getattr(g, 'user_email', 'anonymous')}"
                )
                return jsonify({
                    "ok": False, 
                    "error": "Acesso negado: recurso não pertence ao contexto atual"
                }), 403
            
            return f(*args, **kwargs)
        
        return decorated_function  # type: ignore
    
    return decorator


def add_context_filter_to_query(
    base_query: str, 
    context: Optional[str],
    context_column: str = 'contexto',
    params: Optional[list] = None
) -> tuple[str, list]:
    """
    Adiciona filtro de contexto a uma query SQL de forma segura.
    Evita SQL injection usando prepared statements.
    
    Args:
        base_query: Query SQL base
        context: Contexto para filtrar
        context_column: Nome da coluna de contexto (default: 'contexto')
        params: Lista de parâmetros existentes (será modificada in-place)
        
    Returns:
        tuple: (query modificada, lista de parâmetros atualizada)
        
    Example:
        query = "SELECT * FROM implantacoes WHERE status = %s"
        params = ['ativo']
        query, params = add_context_filter_to_query(query, 'grandes_contas', params=params)
        # query = "SELECT * FROM implantacoes WHERE status = %s AND contexto = %s"
        # params = ['ativo', 'grandes_contas']
    """
    if params is None:
        params = []
    
    if context is None:
        return base_query, params
    
    # Validar context_column para prevenir injection
    allowed_columns = {'contexto', 'i.contexto', 'impl.contexto', 'implantacoes.contexto'}
    if context_column not in allowed_columns:
        raise ValueError(f"Coluna de contexto inválida: {context_column}")
    
    if context == 'onboarding':
        # Onboarding inclui NULL (dados legados) e 'onboarding'
        filter_clause = f" AND ({context_column} IS NULL OR {context_column} = %s)"
        params.append('onboarding')
    else:
        filter_clause = f" AND {context_column} = %s"
        params.append(context)
    
    # Adicionar antes do ORDER BY, GROUP BY, LIMIT se existirem
    import re
    match = re.search(r'\s+(ORDER BY|GROUP BY|LIMIT|OFFSET)\s+', base_query, re.IGNORECASE)
    if match:
        insert_pos = match.start()
        modified_query = base_query[:insert_pos] + filter_clause + base_query[insert_pos:]
    else:
        modified_query = base_query + filter_clause
    
    return modified_query, params


# Constantes de contexto válidos
VALID_CONTEXTS = frozenset({'onboarding', 'grandes_contas', 'ongoing'})


def validate_context_value(context: Optional[str]) -> Optional[str]:
    """
    Valida e sanitiza um valor de contexto.
    
    Args:
        context: Valor de contexto a validar
        
    Returns:
        str: Contexto validado ou None se inválido
    """
    if context is None:
        return None
    
    context = str(context).lower().strip()
    
    # Normalizar variações comuns
    if context in ('grandes-contas', 'grandescontas', 'gc'):
        context = 'grandes_contas'
    elif context in ('on-boarding', 'onboard'):
        context = 'onboarding'
    
    if context in VALID_CONTEXTS:
        return context
    
    return None
