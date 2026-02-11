"""
Módulo de Implantação - Pacote SOLID
Re-exporta todas as funções para manter compatibilidade com código existente.

Estrutura:
- progress.py          -> Cálculo de progresso e cache
- status.py            -> Mudanças de status (iniciar, parar, finalizar...)
- crud.py              -> Criar, excluir, transferir, cancelar
- details.py           -> Detalhes e formatação
- listing.py           -> Listagem e busca de implantações
- oamd_integration.py  -> Integração com sistema externo OAMD
"""

# Importações de progress.py
# Importações de crud.py
from .crud import (
    cancelar_implantacao_service,
    criar_implantacao_modulo_service,
    criar_implantacao_service,
    excluir_implantacao_service,
    transferir_implantacao_service,
)

# Importações de details.py
from .details import (
    _format_implantacao_dates,
    _get_timeline_logs,
    atualizar_detalhes_empresa_service,
)

# Importações de listing.py
from .listing import (
    listar_implantacoes,
    obter_implantacao_basica,
)

# Importações de oamd_integration.py
from .oamd_integration import (
    aplicar_dados_oamd,
    consultar_dados_oamd,
)
from .progress import (
    _get_progress,
    _get_progress_legacy,
    _get_progress_optimized,
    cached_progress,
    invalidar_cache_progresso,
)

# Importações de status.py
from .status import (
    agendar_implantacao_service,
    finalizar_implantacao_service,
    iniciar_implantacao_service,
    marcar_sem_previsao_service,
    parar_implantacao_service,
    reabrir_implantacao_service,
    retomar_implantacao_service,
)

# Exports públicos
__all__ = [
    # Details
    "_format_implantacao_dates",
    # Progress
    "_get_progress",
    "_get_progress_legacy",
    "_get_progress_optimized",
    "_get_timeline_logs",
    # Status
    "agendar_implantacao_service",
    "aplicar_dados_oamd",
    "atualizar_detalhes_empresa_service",
    "cached_progress",
    # CRUD
    "cancelar_implantacao_service",
    # OAMD Integration
    "consultar_dados_oamd",
    "criar_implantacao_modulo_service",
    "criar_implantacao_service",
    "excluir_implantacao_service",
    "finalizar_implantacao_service",
    "iniciar_implantacao_service",
    "invalidar_cache_progresso",
    # Listing
    "listar_implantacoes",
    "marcar_sem_previsao_service",
    "obter_implantacao_basica",
    "parar_implantacao_service",
    "reabrir_implantacao_service",
    "retomar_implantacao_service",
    "transferir_implantacao_service",
]
