"""
Facade para manter compatibilidade de imports durante a modularização.
"""

from ...modules.implantacao.application.actions import (
    handle_agendar_implantacao,
    handle_atualizar_detalhes_empresa,
    handle_cancelar_implantacao,
    handle_criar_implantacao,
    handle_criar_implantacao_modulo,
    handle_create_jira_issue,
    handle_delete_jira_link,
    handle_desfazer_inicio_implantacao,
    handle_excluir_implantacao,
    handle_finalizar_implantacao,
    handle_fetch_jira_issue,
    handle_get_jira_issues,
    handle_iniciar_implantacao,
    handle_marcar_sem_previsao,
    handle_parar_implantacao,
    handle_reabrir_implantacao,
    handle_remover_plano_implantacao,
    handle_retomar_implantacao,
    handle_transferir_implantacao,
)

__all__ = [
    "handle_agendar_implantacao",
    "handle_atualizar_detalhes_empresa",
    "handle_cancelar_implantacao",
    "handle_criar_implantacao",
    "handle_criar_implantacao_modulo",
    "handle_create_jira_issue",
    "handle_delete_jira_link",
    "handle_desfazer_inicio_implantacao",
    "handle_excluir_implantacao",
    "handle_finalizar_implantacao",
    "handle_fetch_jira_issue",
    "handle_get_jira_issues",
    "handle_iniciar_implantacao",
    "handle_marcar_sem_previsao",
    "handle_parar_implantacao",
    "handle_reabrir_implantacao",
    "handle_remover_plano_implantacao",
    "handle_retomar_implantacao",
    "handle_transferir_implantacao",
]
