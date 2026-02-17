from flask import Blueprint, flash, g, jsonify, redirect, request, url_for
from flask_limiter.util import get_remote_address

from ....blueprints.auth import login_required, permission_required
from ....blueprints.helpers.shared_actions import (
    handle_agendar_implantacao,
    handle_atualizar_detalhes_empresa,
    handle_cancelar_implantacao,
    handle_create_jira_issue,
    handle_criar_implantacao,
    handle_criar_implantacao_modulo,
    handle_delete_jira_link,
    handle_desfazer_inicio_implantacao,
    handle_excluir_implantacao,
    handle_fetch_jira_issue,
    handle_finalizar_implantacao,
    handle_get_jira_issues,
    handle_iniciar_implantacao,
    handle_marcar_sem_previsao,
    handle_parar_implantacao,
    handle_reabrir_implantacao,
    handle_remover_plano_implantacao,
    handle_retomar_implantacao,
    handle_transferir_implantacao,
)
from ....common.audit_decorator import audit
from ....config.cache_config import clear_dashboard_cache, clear_implantacao_cache, clear_user_cache
from ....constants import PERFIS_COM_CRIACAO, PERFIS_COM_GESTAO
from ....core.extensions import limiter

onboarding_actions_bp = Blueprint("onboarding_actions", __name__)


@onboarding_actions_bp.route("/criar_implantacao", methods=["POST"])
@login_required
@permission_required(PERFIS_COM_CRIACAO)
@limiter.limit("50 per minute", key_func=lambda: g.user_email or get_remote_address())
@audit(action="CREATE_IMPLANTACAO", target_type="implantacao")
def criar_implantacao():
    return handle_criar_implantacao(
        dashboard_endpoint="onboarding.dashboard",
        contexto="onboarding",
        success_message='Implantação "{nome_empresa}" criada com sucesso. Aplique um plano de sucesso para criar as tarefas.',
        clear_dashboard=True,
    )

@onboarding_actions_bp.route("/criar_implantacao_modulo", methods=["POST"])
@login_required
@permission_required(PERFIS_COM_CRIACAO)
@limiter.limit("50 per minute", key_func=lambda: g.user_email or get_remote_address())
@audit(action="CREATE_IMPLANTACAO_MODULO", target_type="implantacao")
def criar_implantacao_modulo():
    return handle_criar_implantacao_modulo(
        dashboard_endpoint="onboarding.dashboard",
        contexto="onboarding",
        success_message='Implantação de Módulo "{nome_empresa}" criada e atribuída a {usuario_atribuido}.',
        clear_dashboard=True,
    )

@onboarding_actions_bp.route("/iniciar_implantacao", methods=["POST"])
@login_required
@limiter.limit("50 per minute", key_func=lambda: g.user_email or get_remote_address())
def iniciar_implantacao():
    return handle_iniciar_implantacao(
        dashboard_endpoint="onboarding.dashboard",
        detail_endpoint="onboarding.ver_implantacao",
        success_message="Implantação iniciada com sucesso!",
        clear_dashboard=True,
    )

@onboarding_actions_bp.route("/desfazer_inicio_implantacao", methods=["POST"])
@login_required
def desfazer_inicio_implantacao():
    return handle_desfazer_inicio_implantacao(clear_dashboard=True)

@onboarding_actions_bp.route("/desfazer_cancelamento_implantacao", methods=["POST"])
@login_required
def desfazer_cancelamento_implantacao():
    data = request.get_json()
    if not data:
        return jsonify({"ok": False, "error": "Dados inválidos"}), 400

    implantacao_id = data.get("implantacao_id")
    usuario_cs_email = g.user_email
    user_perfil_acesso = g.perfil.get("perfil_acesso") if g.perfil else None

    if not implantacao_id:
        return jsonify({"ok": False, "error": "ID da implantação é obrigatório"}), 400

    try:
        from ....modules.implantacao.domain.status import desfazer_cancelamento_implantacao_service

        desfazer_cancelamento_implantacao_service(implantacao_id, usuario_cs_email, user_perfil_acesso)

        try:
            clear_implantacao_cache(implantacao_id)
            clear_user_cache(usuario_cs_email)
            clear_dashboard_cache()
        except Exception:
            pass

        return jsonify(
            {"ok": True, "message": "Cancelamento desfeito com sucesso! A implantação retornou para 'Em Andamento'."}
        ), 200

    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    except Exception:
        import traceback

        traceback.print_exc()
        return jsonify({"ok": False, "error": "Erro interno ao desfazer cancelamento."}), 500


@onboarding_actions_bp.route("/agendar_implantacao", methods=["POST"])
@login_required
@limiter.limit("50 per minute", key_func=lambda: g.user_email or get_remote_address())
def agendar_implantacao():
    return handle_agendar_implantacao(dashboard_endpoint="onboarding.dashboard", clear_dashboard=True)


@onboarding_actions_bp.route("/marcar_sem_previsao", methods=["POST"])
@login_required
@limiter.limit("50 per minute", key_func=lambda: g.user_email or get_remote_address())
def marcar_sem_previsao():
    return handle_marcar_sem_previsao(dashboard_endpoint="onboarding.dashboard", clear_dashboard=True)


@onboarding_actions_bp.route("/finalizar_implantacao", methods=["POST"])
@login_required
@limiter.limit("50 per minute", key_func=lambda: g.user_email or get_remote_address())
@audit(action="FINALIZE_IMPLANTACAO", target_type="implantacao")
def finalizar_implantacao():
    return handle_finalizar_implantacao(
        dashboard_endpoint="onboarding.dashboard",
        detail_endpoint="onboarding.ver_implantacao",
        clear_dashboard=True,
    )


@onboarding_actions_bp.route("/parar_implantacao", methods=["POST"])
@login_required
@limiter.limit("50 per minute", key_func=lambda: g.user_email or get_remote_address())
def parar_implantacao():
    return handle_parar_implantacao(
        detail_endpoint="onboarding.ver_implantacao",
        clear_dashboard=True,
        success_message='Implantação marcada como "Parada" com data retroativa.',
    )


@onboarding_actions_bp.route("/retomar_implantacao", methods=["POST"])
@login_required
@limiter.limit("50 per minute", key_func=lambda: g.user_email or get_remote_address())
def retomar_implantacao():
    return handle_retomar_implantacao(
        dashboard_endpoint="onboarding.dashboard",
        detail_endpoint="onboarding.ver_implantacao",
        clear_dashboard=False,
    )


@onboarding_actions_bp.route("/reabrir_implantacao", methods=["POST"])
@login_required
@limiter.limit("50 per minute", key_func=lambda: g.user_email or get_remote_address())
def reabrir_implantacao():
    return handle_reabrir_implantacao(
        dashboard_endpoint="onboarding.dashboard",
        detail_endpoint="onboarding.ver_implantacao",
        clear_dashboard=True,
    )


@onboarding_actions_bp.route("/atualizar_detalhes_empresa", methods=["POST"])
@login_required
@limiter.limit("100 per minute", key_func=lambda: g.user_email or get_remote_address())
def atualizar_detalhes_empresa():
    return handle_atualizar_detalhes_empresa(
        dashboard_endpoint="onboarding.dashboard",
        detail_endpoint="onboarding.ver_implantacao",
        clear_dashboard=True,
    )


@onboarding_actions_bp.route("/remover_plano_implantacao", methods=["POST"])
@login_required
@limiter.limit("30 per minute", key_func=lambda: g.user_email or get_remote_address())
def remover_plano_implantacao():
    return handle_remover_plano_implantacao(
        detail_endpoint="onboarding.ver_implantacao",
        clear_dashboard=True,
    )


@onboarding_actions_bp.route("/concluir_plano_implantacao", methods=["POST"])
@login_required
@limiter.limit("30 per minute", key_func=lambda: g.user_email or get_remote_address())
def concluir_plano_implantacao():
    """
    Endpoint de compatibilidade para concluir plano pela tela de detalhes da implantação.
    """
    try:
        implantacao_id = request.form.get("implantacao_id", type=int)
        plano_instancia_id = request.form.get("plano_instancia_id", type=int)

        if not implantacao_id:
            flash("Implantação inválida.", "error")
            return redirect(url_for("onboarding.dashboard"))

        if not plano_instancia_id:
            from ....db import query_db

            plano_em_andamento = query_db(
                """
                SELECT id
                FROM planos_sucesso
                WHERE processo_id = %s AND status = 'em_andamento'
                ORDER BY data_criacao DESC
                LIMIT 1
                """,
                (implantacao_id,),
                one=True,
            )
            plano_instancia_id = plano_em_andamento["id"] if plano_em_andamento else None

        if not plano_instancia_id:
            from ....db import query_db

            impl = query_db(
                "SELECT plano_sucesso_id FROM implantacoes WHERE id = %s",
                (implantacao_id,),
                one=True,
            )
            plano_instancia_id = impl.get("plano_sucesso_id") if impl else None

        if not plano_instancia_id:
            flash("Nenhum plano em andamento encontrado para concluir.", "warning")
            return redirect(url_for("onboarding.ver_implantacao", impl_id=implantacao_id))

        from ....db import db_connection, query_db
        from ....modules.implantacao.domain.progress import _get_progress
        from ....modules.planos.application.planos_sucesso_service import concluir_plano_sucesso
        from ....modules.planos.domain.aplicar import criar_instancia_plano_para_implantacao

        progresso, total_itens, _ = _get_progress(implantacao_id)
        if int(total_itens or 0) <= 0 or float(progresso or 0) < 100:
            flash("Para concluir o plano, o progresso precisa estar em 100%.", "warning")
            return redirect(url_for("onboarding.ver_implantacao", impl_id=implantacao_id))

        plano = query_db("SELECT * FROM planos_sucesso WHERE id = %s", (plano_instancia_id,), one=True)
        if plano and not plano.get("processo_id"):
            # Plano apontando para template. Criar instancia e concluir apenas a instancia.
            with db_connection() as (conn, db_type):
                cursor = conn.cursor()
                plano_instancia_id = criar_instancia_plano_para_implantacao(
                    plano_id=plano.get("id"),
                    implantacao_id=implantacao_id,
                    usuario=g.user_email,
                    cursor=cursor,
                    db_type=db_type,
                )
                sql_update = "UPDATE implantacoes SET plano_sucesso_id = %s WHERE id = %s"
                if db_type == "sqlite":
                    sql_update = sql_update.replace("%s", "?")
                cursor.execute(sql_update, (plano_instancia_id, implantacao_id))
                conn.commit()

        concluir_plano_sucesso(plano_instancia_id)
        flash("Plano concluído com sucesso!", "success")
        return redirect(url_for("onboarding.ver_implantacao", impl_id=implantacao_id))
    except Exception as e:
        impl_id = request.form.get("implantacao_id", type=int)
        flash(f"Erro ao concluir plano: {e!s}", "error")
        if impl_id:
            return redirect(url_for("onboarding.ver_implantacao", impl_id=impl_id))
        return redirect(url_for("onboarding.dashboard"))


@onboarding_actions_bp.route("/transferir_implantacao", methods=["POST"])
@login_required
@permission_required(PERFIS_COM_GESTAO)
@limiter.limit("30 per minute", key_func=lambda: g.user_email or get_remote_address())
@audit(action="TRANSFER_IMPLANTACAO", target_type="implantacao")
def transferir_implantacao():
    return handle_transferir_implantacao(
        dashboard_endpoint="onboarding.dashboard",
        detail_endpoint="onboarding.ver_implantacao",
    )


@onboarding_actions_bp.route("/excluir_implantacao", methods=["POST"])
@login_required
@limiter.limit("100 per minute", key_func=lambda: g.user_email or get_remote_address())
@audit(action="DELETE_IMPLANTACAO", target_type="implantacao")
def excluir_implantacao():
    return handle_excluir_implantacao(
        dashboard_endpoint="onboarding.dashboard",
        clear_dashboard=True,
    )


@onboarding_actions_bp.route("/cancelar_implantacao", methods=["POST"])
@login_required
@audit(action="CANCEL_IMPLANTACAO", target_type="implantacao")
def cancelar_implantacao():
    return handle_cancelar_implantacao(
        dashboard_endpoint="onboarding.dashboard",
        detail_endpoint="onboarding.ver_implantacao",
    )

@onboarding_actions_bp.route("/api/implantacao/<int:implantacao_id>/jira-issues", methods=["GET"])
@login_required
def get_jira_issues(implantacao_id):
    return handle_get_jira_issues(implantacao_id, log_label="[Onboarding]")

@onboarding_actions_bp.route("/api/implantacao/<int:implantacao_id>/jira-issues", methods=["POST"])
@login_required
def create_jira_issue_action(implantacao_id):
    return handle_create_jira_issue(implantacao_id, use_onboarding_status_codes=True)

@onboarding_actions_bp.route("/api/implantacao/<int:implantacao_id>/jira-issues/fetch", methods=["POST"])
@login_required
def fetch_jira_issue_action(implantacao_id):
    return handle_fetch_jira_issue(implantacao_id)

@onboarding_actions_bp.route("/api/implantacao/<int:implantacao_id>/jira-issues/<path:jira_key>", methods=["DELETE"])
@login_required
def delete_jira_link_action(implantacao_id, jira_key):
    return handle_delete_jira_link(implantacao_id, jira_key)
