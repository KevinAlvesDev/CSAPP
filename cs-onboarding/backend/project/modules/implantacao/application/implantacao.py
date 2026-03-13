"""
Compat module kept for legacy imports.
Prefer importing directly from modules.implantacao.domain.
"""

from ..domain import (  # noqa: F401
    _format_implantacao_dates,
    _get_progress,
    _get_progress_legacy,
    _get_progress_optimized,
    _get_timeline_logs,
    agendar_implantacao_service,
    aplicar_dados_oamd,
    atualizar_detalhes_empresa_service,
    cached_progress,
    cancelar_implantacao_service,
    consultar_dados_oamd,
    criar_implantacao_modulo_service,
    criar_implantacao_service,
    excluir_implantacao_service,
    finalizar_implantacao_service,
    get_implantacao_details,
    iniciar_implantacao_service,
    invalidar_cache_progresso,
    listar_implantacoes,
    marcar_sem_previsao_service,
    obter_implantacao_basica,
    parar_implantacao_service,
    reabrir_implantacao_service,
    retomar_implantacao_service,
    transferir_implantacao_service,
)
