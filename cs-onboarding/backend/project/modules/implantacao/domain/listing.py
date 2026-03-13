import logging
logger = logging.getLogger(__name__)
"""
Módulo de Listagem de Implantações
Funções para listar e buscar implantações.
Princípio SOLID: Single Responsibility
"""

from flask import current_app

from ....common.context_profiles import resolve_context
from ....db import query_db
from ....modules.hierarquia.application.hierarquia_service import get_hierarquia_implantacao
from .details import _format_implantacao_dates


def listar_implantacoes(user_email, status_filter=None, page=1, per_page=50, is_admin=False, context=None):
    """
    Lista implantações com paginação e filtro.
    Substitui a lógica do endpoint GET /api/v1/implantacoes.

    Args:
        user_email: Email do usuário
        status_filter: Filtro de status (opcional)
        page: Página atual
        per_page: Itens por página
        is_admin: Se é admin (pode ver todas)
        context: Filtro de contexto (onboarding, ongoing, grandes_contas)

    Returns:
        dict: Dados com paginação
    """
    try:
        page = int(page)
        per_page = int(per_page)
        per_page = min(per_page, 200)
    except (TypeError, ValueError):
        page = 1
        per_page = 50

    offset = (page - 1) * per_page

    # Base query reconstruction
    where_clauses = []
    params = []

    # If not admin, filter by user
    if not is_admin:
        where_clauses.append("i.usuario_cs = %s")
        params.append(user_email)

    if status_filter:
        where_clauses.append("i.status = %s")
        params.append(status_filter)

    ctx = resolve_context(context)
    if ctx == "onboarding":
        where_clauses.append("(i.contexto IS NULL OR i.contexto = 'onboarding')")
    else:
        where_clauses.append("i.contexto = %s")
        params.append(ctx)

    where_str = " WHERE " + " AND ".join(where_clauses) if where_clauses else ""

    query = f"""
        SELECT i.*, p.nome as cs_nome
        FROM implantacoes i
        LEFT JOIN perfil_usuario p ON i.usuario_cs = p.usuario
        LEFT JOIN perfil_usuario_contexto puc ON i.usuario_cs = puc.usuario AND puc.contexto = COALESCE(i.contexto, 'onboarding')
        {where_str}
        ORDER BY i.data_criacao DESC LIMIT %s OFFSET %s
    """

    # query param arguments
    query_args = [*params, per_page, offset]

    try:
        implantacoes = query_db(query, tuple(query_args))  # nosec B608
    except Exception as e:
        current_app.logger.error(f"Erro ao listar implantações: {e}", exc_info=True)
        implantacoes = []

    # Count query
    count_query = f"SELECT COUNT(*) as total FROM implantacoes i {where_str}"
    try:
        total_result = query_db(count_query, tuple(params), one=True)  # nosec B608
        total = total_result.get("total", 0) if total_result else 0
    except Exception as exc:
        logger.exception("Unhandled exception", exc_info=True)
        total = 0

    return {
        "data": implantacoes,
        "pagination": {"page": page, "per_page": per_page, "total": total, "pages": (total + per_page - 1) // per_page},
    }


def obter_implantacao_basica(impl_id, user_email, is_manager=False):
    """
    Retorna detalhes básicos de uma implantação e sua hierarquia.
    Substitui a lógica do endpoint GET /api/v1/implantacoes/<id>.

    Args:
        impl_id: ID da implantação
        user_email: Email do usuário
        is_manager: Se é gerente (pode ver todas)

    Returns:
        dict: Dados da implantação e hierarquia ou None
    """

    query_base = """
        SELECT i.*, p.nome as cs_nome
        FROM implantacoes i
        LEFT JOIN perfil_usuario p ON i.usuario_cs = p.usuario
        LEFT JOIN perfil_usuario_contexto puc ON i.usuario_cs = puc.usuario AND puc.contexto = COALESCE(i.contexto, 'onboarding')
        WHERE i.id = %s
    """
    params = [impl_id]

    if not is_manager:
        query_base += " AND i.usuario_cs = %s"
        params.append(user_email)

    impl = query_db(query_base, tuple(params), one=True)

    if not impl:
        return None

    # Validação de Contexto: Garante que o usuário não acesse dados de outro módulo via URL manual
    from flask import g
    from ....common.context_navigation import normalize_context
    
    modulo_atual = getattr(g, "modulo_atual", "onboarding")
    impl_contexto = normalize_context(impl.get("contexto"))
    
    # Se não for manager, o contexto DEVE bater. Se for manager, permitimos mas registramos (ou podemos bloquear se desejar isolamento estrito)
    if not is_manager and impl_contexto != modulo_atual:
        current_app.logger.warning(f"Acesso bloqueado: Implantação {impl_id} é do contexto {impl_contexto}, mas usuário está em {modulo_atual}")
        return None

    # Normalizar datas
    impl = _format_implantacao_dates(impl)

    # Obter Hierarquia
    hierarquia = get_hierarquia_implantacao(impl_id)

    return {"implantacao": impl, "hierarquia": hierarquia}