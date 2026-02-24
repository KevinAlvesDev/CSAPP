import contextlib
import os
import re
import time
from datetime import datetime

from flask import Blueprint, current_app, flash, g, jsonify, redirect, request, url_for
from flask_limiter.util import get_remote_address
from werkzeug.utils import secure_filename

from ....common import utils
from ....common.audit_decorator import audit
from ....common.validation import ValidationError, sanitize_string, validate_date, validate_integer
from ....config.cache_config import clear_implantacao_cache, clear_user_cache
from ....config.logging_config import app_logger
from ....constants import PERFIS_COM_CRIACAO, PERFIS_COM_GESTAO
from ....core.extensions import limiter, r2_client
from ....db import logar_timeline
from ....blueprints.auth import login_required, permission_required
from ....blueprints.helpers.shared_actions import (
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

grandes_contas_actions_bp = Blueprint("grandes_contas_actions", __name__)


@grandes_contas_actions_bp.route("/criar_implantacao", methods=["POST"])
@login_required
@permission_required(PERFIS_COM_CRIACAO)
@limiter.limit("50 per minute", key_func=lambda: g.user_email or get_remote_address())
@audit(action="CREATE_IMPLANTACAO_GC", target_type="implantacao")
def criar_implantacao():
    return handle_criar_implantacao(
        dashboard_endpoint="grandes_contas.dashboard",
        contexto="grandes_contas",
        success_message='Implantação "{nome_empresa}" criada com sucesso. Aplique um plano de sucesso para criar as tarefas.',
        clear_dashboard=True,
    )


@grandes_contas_actions_bp.route("/criar_implantacao_modulo", methods=["POST"])
@login_required
@permission_required(PERFIS_COM_CRIACAO)
@limiter.limit("50 per minute", key_func=lambda: g.user_email or get_remote_address())
@audit(action="CREATE_IMPLANTACAO_MODULO_GC", target_type="implantacao")
def criar_implantacao_modulo():
    return handle_criar_implantacao_modulo(
        dashboard_endpoint="grandes_contas.dashboard",
        contexto="grandes_contas",
        success_message='Implantação de Módulo "{nome_empresa}" criada e atribuída a {usuario_atribuido}.',
        clear_dashboard=True,
    )


@grandes_contas_actions_bp.route("/iniciar_implantacao", methods=["POST"])
@login_required
@limiter.limit("50 per minute", key_func=lambda: g.user_email or get_remote_address())
def iniciar_implantacao():
    return handle_iniciar_implantacao(
        dashboard_endpoint="grandes_contas.dashboard",
        detail_endpoint="grandes_contas.ver_implantacao",
        success_message="Implantação iniciada com sucesso!",
        clear_dashboard=True,
    )


@grandes_contas_actions_bp.route("/desfazer_inicio_implantacao", methods=["POST"])
@login_required
def desfazer_inicio_implantacao():
    return handle_desfazer_inicio_implantacao(clear_dashboard=True)

@grandes_contas_actions_bp.route("/agendar_implantacao", methods=["POST"])
@login_required
@limiter.limit("50 per minute", key_func=lambda: g.user_email or get_remote_address())
def agendar_implantacao():
    return handle_agendar_implantacao(dashboard_endpoint="grandes_contas.dashboard", clear_dashboard=True)


@grandes_contas_actions_bp.route("/marcar_sem_previsao", methods=["POST"])
@login_required
@limiter.limit("50 per minute", key_func=lambda: g.user_email or get_remote_address())
def marcar_sem_previsao():
    return handle_marcar_sem_previsao(dashboard_endpoint="grandes_contas.dashboard", clear_dashboard=True)


@grandes_contas_actions_bp.route("/finalizar_implantacao", methods=["POST"])
@login_required
@limiter.limit("50 per minute", key_func=lambda: g.user_email or get_remote_address())
@audit(action="FINALIZE_IMPLANTACAO_GC", target_type="implantacao")
def finalizar_implantacao():
    return handle_finalizar_implantacao(
        dashboard_endpoint="grandes_contas.dashboard",
        detail_endpoint="grandes_contas.ver_implantacao",
        clear_dashboard=True,
    )


@grandes_contas_actions_bp.route("/parar_implantacao", methods=["POST"])
@login_required
@limiter.limit("50 per minute", key_func=lambda: g.user_email or get_remote_address())
def parar_implantacao():
    return handle_parar_implantacao(
        detail_endpoint="grandes_contas.ver_implantacao",
        clear_dashboard=True,
        success_message='Implantação marcada como "Parada" (GC).',
    )


@grandes_contas_actions_bp.route("/retomar_implantacao", methods=["POST"])
@login_required
@limiter.limit("50 per minute", key_func=lambda: g.user_email or get_remote_address())
def retomar_implantacao():
    return handle_retomar_implantacao(
        dashboard_endpoint="grandes_contas.dashboard",
        detail_endpoint="grandes_contas.ver_implantacao",
        clear_dashboard=True,
    )


@grandes_contas_actions_bp.route("/reabrir_implantacao", methods=["POST"])
@login_required
@limiter.limit("50 per minute", key_func=lambda: g.user_email or get_remote_address())
def reabrir_implantacao():
    return handle_reabrir_implantacao(
        dashboard_endpoint="grandes_contas.dashboard",
        detail_endpoint="grandes_contas.ver_implantacao",
        clear_dashboard=True,
    )


@grandes_contas_actions_bp.route("/atualizar_detalhes_empresa", methods=["POST"])
@login_required
@limiter.limit("100 per minute", key_func=lambda: g.user_email or get_remote_address())
def atualizar_detalhes_empresa():
    return handle_atualizar_detalhes_empresa(
        dashboard_endpoint="grandes_contas.dashboard",
        detail_endpoint="grandes_contas.ver_implantacao",
        clear_dashboard=True,
    )


@grandes_contas_actions_bp.route("/remover_plano_implantacao", methods=["POST"])
@login_required
@limiter.limit("30 per minute", key_func=lambda: g.user_email or get_remote_address())
def remover_plano_implantacao():
    return handle_remover_plano_implantacao(
        detail_endpoint="grandes_contas.ver_implantacao",
        clear_dashboard=True,
    )


@grandes_contas_actions_bp.route("/transferir_implantacao", methods=["POST"])
@login_required
@permission_required(PERFIS_COM_GESTAO)
@limiter.limit("30 per minute", key_func=lambda: g.user_email or get_remote_address())
@audit(action="TRANSFER_IMPLANTACAO_GC", target_type="implantacao")
def transferir_implantacao():
    return handle_transferir_implantacao(
        dashboard_endpoint="grandes_contas.dashboard",
        detail_endpoint="grandes_contas.ver_implantacao",
    )


@grandes_contas_actions_bp.route("/excluir_implantacao", methods=["POST"])
@login_required
@limiter.limit("100 per minute", key_func=lambda: g.user_email or get_remote_address())
@audit(action="DELETE_IMPLANTACAO_GC", target_type="implantacao")
def excluir_implantacao():
    return handle_excluir_implantacao(
        dashboard_endpoint="grandes_contas.dashboard",
        clear_dashboard=True,
    )


@grandes_contas_actions_bp.route("/cancelar_implantacao", methods=["POST"])
@login_required
@audit(action="CANCEL_IMPLANTACAO_GC", target_type="implantacao")
def cancelar_implantacao():
    return handle_cancelar_implantacao(
        dashboard_endpoint="grandes_contas.dashboard",
        detail_endpoint="grandes_contas.ver_implantacao",
    )

@grandes_contas_actions_bp.route("/api/implantacao/<int:implantacao_id>/jira-issues", methods=["GET"])
@login_required
def get_jira_issues(implantacao_id):
    return handle_get_jira_issues(implantacao_id, log_label="[Grandes Contas]")

@grandes_contas_actions_bp.route("/api/implantacao/<int:implantacao_id>/jira-issues", methods=["POST"])
@login_required
def create_jira_issue_action(implantacao_id):
    return handle_create_jira_issue(implantacao_id, use_onboarding_status_codes=False)

@grandes_contas_actions_bp.route("/api/implantacao/<int:implantacao_id>/jira-issues/fetch", methods=["POST"])
@login_required
def fetch_jira_issue_action(implantacao_id):
    return handle_fetch_jira_issue(implantacao_id)

@grandes_contas_actions_bp.route(
    "/api/implantacao/<int:implantacao_id>/jira-issues/<path:jira_key>", methods=["DELETE"]
)
@login_required
def delete_jira_link_action(implantacao_id, jira_key):
    return handle_delete_jira_link(implantacao_id, jira_key)









