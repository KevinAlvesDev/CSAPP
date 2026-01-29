# -*- coding: utf-8 -*-
import os
import re
import time
from datetime import datetime

from flask import Blueprint, current_app, flash, g, jsonify, redirect, request, url_for
from flask_limiter.util import get_remote_address
from werkzeug.utils import secure_filename

from ...common import utils
from ...common.audit_decorator import audit
from ...common.validation import ValidationError, sanitize_string, validate_date, validate_integer
from ...config.cache_config import clear_implantacao_cache, clear_user_cache
from ...config.logging_config import app_logger
from ...constants import PERFIS_COM_CRIACAO, PERFIS_COM_GESTAO
from ...core.extensions import limiter, r2_client
from ...db import logar_timeline
from ..auth import login_required, permission_required

grandes_contas_actions_bp = Blueprint("grandes_contas_actions", __name__)


@grandes_contas_actions_bp.route("/criar_implantacao", methods=["POST"])
@login_required
@permission_required(PERFIS_COM_CRIACAO)
@limiter.limit("50 per minute", key_func=lambda: g.user_email or get_remote_address())
@audit(action="CREATE_IMPLANTACAO_GC", target_type="implantacao")
def criar_implantacao():
    usuario_criador = g.user_email

    try:
        nome_empresa = sanitize_string(request.form.get("nome_empresa", ""), max_length=200)
        usuario_atribuido = sanitize_string(request.form.get("usuario_atribuido_cs", ""), max_length=100)
        usuario_atribuido = usuario_atribuido or usuario_criador

        id_favorecido_raw = request.form.get("id_favorecido")
        id_favorecido = None
        if id_favorecido_raw:
            try:
                import re as _re

                digits_only = "".join(_re.findall(r"\d+", str(id_favorecido_raw)))
                if digits_only:
                    id_favorecido = validate_integer(digits_only, min_value=1)
            except Exception:
                id_favorecido = None

        from ...domain.implantacao.crud import criar_implantacao_service

        # Passando contexto explícito para Grandes Contas
        implantacao_id = criar_implantacao_service(
            nome_empresa, usuario_atribuido, usuario_criador, id_favorecido, contexto="grandes_contas"
        )

        flash(
            f'Implantação "{nome_empresa}" (Grandes Contas) criada com sucesso. Aplique um plano de sucesso.',
            "success",
        )

        try:
            clear_user_cache(usuario_criador)
            if usuario_atribuido and usuario_atribuido != usuario_criador:
                clear_user_cache(usuario_atribuido)
            clear_implantacao_cache(implantacao_id)
        except Exception:
            pass
        return redirect(url_for("grandes_contas.dashboard"))

    except ValueError as e:
        flash(str(e), "error")
        return redirect(url_for("grandes_contas.dashboard"))
    except Exception as e:
        app_logger.error(f"ERRO ao criar implantação GC por {usuario_criador}: {e}")
        flash(f"Erro ao criar implantação: {e}.", "error")
        return redirect(url_for("grandes_contas.dashboard"))


@grandes_contas_actions_bp.route("/criar_implantacao_modulo", methods=["POST"])
@login_required
@permission_required(PERFIS_COM_CRIACAO)
@limiter.limit("50 per minute", key_func=lambda: g.user_email or get_remote_address())
@audit(action="CREATE_IMPLANTACAO_MODULO_GC", target_type="implantacao")
def criar_implantacao_modulo():
    usuario_criador = g.user_email

    try:
        nome_empresa = sanitize_string(request.form.get("nome_empresa_modulo", ""), max_length=200)
        usuario_atribuido = sanitize_string(request.form.get("usuario_atribuido_cs_modulo", ""), max_length=100)
        modulo_tipo = sanitize_string(request.form.get("modulo_tipo", ""), max_length=50)

        id_favorecido_raw = request.form.get("id_favorecido")
        id_favorecido = None
        if id_favorecido_raw:
            try:
                digits_only = "".join(re.findall(r"\d+", str(id_favorecido_raw)))
                if digits_only:
                    id_favorecido = validate_integer(digits_only, min_value=1)
            except Exception:
                id_favorecido = None

        from ...domain.implantacao.crud import criar_implantacao_modulo_service

        # Passando contexto explícito para Grandes Contas
        implantacao_id = criar_implantacao_modulo_service(
            nome_empresa, usuario_atribuido, usuario_criador, modulo_tipo, id_favorecido, contexto="grandes_contas"
        )

        try:
            clear_user_cache(usuario_criador)
            if usuario_atribuido and usuario_atribuido != usuario_criador:
                clear_user_cache(usuario_atribuido)
            clear_implantacao_cache(implantacao_id)
        except Exception:
            pass

        flash(f'Implantação de Módulo "{nome_empresa}" (GC) criada e atribuída a {usuario_atribuido}.', "success")
        return redirect(url_for("grandes_contas.dashboard"))

    except ValueError as e:
        flash(str(e), "error")
        return redirect(url_for("grandes_contas.dashboard"))
    except Exception as e:
        app_logger.error(f"ERRO ao criar implantação de módulo GC por {usuario_criador}: {e}")
        flash(f"Erro ao criar implantação de módulo: {e}.", "error")
        return redirect(url_for("grandes_contas.dashboard"))


@grandes_contas_actions_bp.route("/iniciar_implantacao", methods=["POST"])
@login_required
@limiter.limit("50 per minute", key_func=lambda: g.user_email or get_remote_address())
def iniciar_implantacao():
    usuario_cs_email = g.user_email

    try:
        implantacao_id = validate_integer(request.form.get("implantacao_id"), min_value=1)
    except ValidationError as e:
        flash(f"ID de implantação inválido: {str(e)}", "error")
        return redirect(url_for("grandes_contas.dashboard"))

    redirect_to_fallback = request.form.get("redirect_to", "dashboard")
    dest_url_fallback = url_for("grandes_contas.dashboard")
    if redirect_to_fallback == "detalhes":
        dest_url_fallback = url_for("grandes_contas.ver_implantacao", impl_id=implantacao_id)

    try:
        from ...domain.implantacao_service import iniciar_implantacao_service

        iniciar_implantacao_service(implantacao_id, usuario_cs_email)

        flash("Implantação iniciada com sucesso (GC)!", "success")
        try:
            clear_user_cache(usuario_cs_email)
            clear_implantacao_cache(implantacao_id)
        except Exception:
            pass

        return redirect(url_for("grandes_contas.ver_implantacao", impl_id=implantacao_id))

    except ValueError as e:
        flash(str(e), "error")
        return redirect(request.referrer or dest_url_fallback)
    except Exception as e:
        app_logger.error(f"Erro ao iniciar implantação ID {implantacao_id}: {e}")
        flash("Erro ao iniciar implantação.", "error")
        return redirect(url_for("grandes_contas.dashboard"))


@grandes_contas_actions_bp.route("/desfazer_inicio_implantacao", methods=["POST"])
@login_required
def desfazer_inicio_implantacao():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Dados inválidos"}), 400

    implantacao_id = data.get("implantacao_id")
    usuario_cs_email = g.user_email

    if not implantacao_id:
        return jsonify({"error": "ID da implantação é obrigatório"}), 400

    try:
        from ...domain.implantacao.status import desfazer_inicio_implantacao_service

        desfazer_inicio_implantacao_service(implantacao_id, usuario_cs_email)

        try:
            clear_implantacao_cache(implantacao_id)
            clear_user_cache(usuario_cs_email)
        except Exception:
            pass

        return jsonify({"message": "Início da implantação desfeito com sucesso!"}), 200

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception:
        import traceback

        traceback.print_exc()
        return jsonify({"error": "Erro interno ao desfazer início."}), 500


@grandes_contas_actions_bp.route("/agendar_implantacao", methods=["POST"])
@login_required
@limiter.limit("50 per minute", key_func=lambda: g.user_email or get_remote_address())
def agendar_implantacao():
    usuario_cs_email = g.user_email
    implantacao_id = request.form.get("implantacao_id")
    data_prevista = request.form.get("data_inicio_previsto")

    if not data_prevista:
        flash("A data de início previsto é obrigatória.", "error")
        return redirect(url_for("grandes_contas.dashboard"))
    try:
        data_prevista_iso = validate_date(data_prevista)
    except ValidationError:
        flash("Data de início inválida. Formatos aceitos: DD/MM/AAAA, MM/DD/AAAA, AAAA-MM-DD.", "error")
        return redirect(url_for("grandes_contas.dashboard"))

    try:
        from ...domain.implantacao_service import agendar_implantacao_service

        nome_empresa = agendar_implantacao_service(implantacao_id, usuario_cs_email, data_prevista_iso)

        flash(f'Implantação "{nome_empresa}" movida para "Futuras" com início em {data_prevista}.', "success")
        try:
            clear_user_cache(usuario_cs_email)
            clear_implantacao_cache(implantacao_id)
        except Exception:
            pass

    except ValueError as e:
        flash(str(e), "error")
    except Exception as e:
        app_logger.error(f"Erro ao agendar implantação ID {implantacao_id}: {e}")
        flash(f"Erro ao agendar implantação: {e}", "error")

    return redirect(url_for("grandes_contas.dashboard", refresh="1"))


@grandes_contas_actions_bp.route("/marcar_sem_previsao", methods=["POST"])
@login_required
@limiter.limit("50 per minute", key_func=lambda: g.user_email or get_remote_address())
def marcar_sem_previsao():
    usuario_cs_email = g.user_email
    implantacao_id_raw = request.form.get("implantacao_id")
    try:
        implantacao_id = validate_integer(int(implantacao_id_raw), min_value=1)
    except Exception:
        flash("ID da implantação inválido.", "error")
        return redirect(url_for("grandes_contas.dashboard", refresh="1"))

    try:
        from ...domain.implantacao_service import marcar_sem_previsao_service

        nome_empresa = marcar_sem_previsao_service(implantacao_id, usuario_cs_email)

        flash(f'Implantação "{nome_empresa}" marcada como "Sem previsão".', "success")
        try:
            clear_user_cache(usuario_cs_email)
            clear_implantacao_cache(implantacao_id)
        except Exception:
            pass
    except ValueError as e:
        flash(str(e), "error")
    except Exception as e:
        app_logger.error(f"Erro ao marcar sem previsão implantação ID {implantacao_id}: {e}")
        flash(f"Erro ao marcar sem previsão: {e}", "error")

    return redirect(url_for("grandes_contas.dashboard", refresh="1"))


@grandes_contas_actions_bp.route("/finalizar_implantacao", methods=["POST"])
@login_required
@limiter.limit("50 per minute", key_func=lambda: g.user_email or get_remote_address())
@audit(action="FINALIZE_IMPLANTACAO_GC", target_type="implantacao")
def finalizar_implantacao():
    usuario_cs_email = g.user_email
    implantacao_id = request.form.get("implantacao_id")
    redirect_target = request.form.get("redirect_to", "dashboard")
    dest_url = url_for("grandes_contas.dashboard")
    if redirect_target == "detalhes":
        dest_url = url_for("grandes_contas.ver_implantacao", impl_id=implantacao_id)

    try:
        data_finalizacao = request.form.get("data_finalizacao")
        if not data_finalizacao:
            flash("A data da finalização é obrigatória.", "error")
            return redirect(dest_url)
        try:
            data_final_iso = validate_date(data_finalizacao)
        except ValidationError:
            flash("Data da finalização inválida. Formatos aceitos: DD/MM/AAAA, MM/DD/AAAA, AAAA-MM-DD.", "error")
            return redirect(dest_url)

        from ...domain.implantacao_service import finalizar_implantacao_service

        finalizar_implantacao_service(implantacao_id, usuario_cs_email, data_final_iso)

        flash("Implantação finalizada com sucesso!", "success")
        try:
            clear_user_cache(usuario_cs_email)
            clear_implantacao_cache(implantacao_id)
        except Exception:
            pass

    except ValueError as e:
        flash(str(e), "error")
    except Exception as e:
        app_logger.error(f"Erro ao finalizar implantação id={implantacao_id} user={usuario_cs_email}: {e}")
        flash("Erro ao finalizar implantação.", "error")

    return redirect(dest_url)


@grandes_contas_actions_bp.route("/parar_implantacao", methods=["POST"])
@login_required
@limiter.limit("50 per minute", key_func=lambda: g.user_email or get_remote_address())
def parar_implantacao():
    usuario_cs_email = g.user_email
    implantacao_id = request.form.get("implantacao_id")
    motivo = request.form.get("motivo_parada", "").strip()
    data_parada = request.form.get("data_parada")
    dest_url = url_for("grandes_contas.ver_implantacao", impl_id=implantacao_id)

    if not motivo:
        flash("O motivo da parada é obrigatória.", "error")
        return redirect(dest_url)
    if not data_parada:
        flash("A data da parada é obrigatória.", "error")
        return redirect(dest_url)
    try:
        data_parada_iso = validate_date(data_parada)
    except ValidationError:
        flash("Data da parada inválida. Formatos aceitos: DD/MM/AAAA, MM/DD/AAAA, AAAA-MM-DD.", "error")
        return redirect(dest_url)

    try:
        user_perfil_acesso = g.perfil.get("perfil_acesso") if getattr(g, "perfil", None) else None

        from ...domain.implantacao_service import parar_implantacao_service

        parar_implantacao_service(implantacao_id, usuario_cs_email, user_perfil_acesso, data_parada_iso, motivo)

        flash('Implantação marcada como "Parada" (GC).', "success")
        try:
            clear_user_cache(usuario_cs_email)
            clear_implantacao_cache(implantacao_id)
        except Exception:
            pass

    except ValueError as e:
        flash(str(e), "error")
    except Exception as e:
        app_logger.error(f"Erro ao parar implantação ID {implantacao_id}: {e}")
        flash(f"Erro ao parar implantação: {e}", "error")

    return redirect(dest_url)


@grandes_contas_actions_bp.route("/retomar_implantacao", methods=["POST"])
@login_required
@limiter.limit("50 per minute", key_func=lambda: g.user_email or get_remote_address())
def retomar_implantacao():
    usuario_cs_email = g.user_email
    implantacao_id = request.form.get("implantacao_id")
    redirect_to = request.form.get("redirect_to", "dashboard")
    dest_url = url_for("grandes_contas.dashboard")
    if redirect_to == "detalhes":
        dest_url = url_for("grandes_contas.ver_implantacao", impl_id=implantacao_id)

    try:
        user_perfil_acesso = g.perfil.get("perfil_acesso") if getattr(g, "perfil", None) else None

        from ...domain.implantacao_service import retomar_implantacao_service

        retomar_implantacao_service(implantacao_id, usuario_cs_email, user_perfil_acesso)

        flash('Implantação retomada e movida para "Em Andamento".', "success")
        try:
            clear_user_cache(usuario_cs_email)
            clear_implantacao_cache(implantacao_id)
        except Exception:
            pass

    except ValueError as e:
        flash(str(e), "error")
        return redirect(request.referrer or dest_url)
    except Exception as e:
        app_logger.error(f"Erro ao retomar implantação ID {implantacao_id}: {e}")
        flash(f"Erro ao retomar implantação: {e}", "error")

    return redirect(dest_url)


@grandes_contas_actions_bp.route("/reabrir_implantacao", methods=["POST"])
@login_required
@limiter.limit("50 per minute", key_func=lambda: g.user_email or get_remote_address())
def reabrir_implantacao():
    usuario_cs_email = g.user_email
    implantacao_id = request.form.get("implantacao_id")
    redirect_to = request.form.get("redirect_to", "dashboard")
    dest_url = url_for("grandes_contas.dashboard")
    if redirect_to == "detalhes":
        dest_url = url_for("grandes_contas.ver_implantacao", impl_id=implantacao_id)

    try:
        from ...domain.implantacao_service import reabrir_implantacao_service

        reabrir_implantacao_service(implantacao_id, usuario_cs_email)

        flash('Implantação reaberta com sucesso e movida para "Em Andamento".', "success")
        try:
            clear_user_cache(usuario_cs_email)
            clear_implantacao_cache(implantacao_id)
        except Exception:
            pass

    except ValueError as e:
        flash(str(e), "error")
        return redirect(request.referrer or url_for("grandes_contas.dashboard"))
    except Exception as e:
        app_logger.error(f"Erro ao reabrir implantação ID {implantacao_id}: {e}")
        flash(f"Erro ao reabrir implantação: {e}", "error")

    return redirect(dest_url)


@grandes_contas_actions_bp.route("/atualizar_detalhes_empresa", methods=["POST"])
@login_required
@limiter.limit("100 per minute", key_func=lambda: g.user_email or get_remote_address())
def atualizar_detalhes_empresa():
    from ..helpers import build_detalhes_campos

    usuario_cs_email = g.user_email
    implantacao_id = request.form.get("implantacao_id")
    redirect_to = request.form.get("redirect_to", "dashboard")
    user_perfil_acesso = g.perfil.get("perfil_acesso") if g.perfil else None

    # Determine response type early
    wants_json = "application/json" in (request.headers.get("Accept") or "")
    is_modal = (redirect_to or "").lower() == "modal"

    dest_url = url_for("grandes_contas.dashboard")
    if redirect_to == "detalhes":
        dest_url = url_for("grandes_contas.ver_implantacao", impl_id=implantacao_id)

    try:
        final_campos, error = build_detalhes_campos()

        if error:
            if wants_json or is_modal:
                return jsonify({"ok": False, "error": error}), 400
            flash(error, "warning")
            return redirect(dest_url)

        from ...domain.implantacao_service import atualizar_detalhes_empresa_service

        atualizar_detalhes_empresa_service(implantacao_id, usuario_cs_email, user_perfil_acesso, final_campos)

        try:
            logar_timeline(
                implantacao_id, usuario_cs_email, "detalhes_alterados", "Detalhes da empresa/cliente foram atualizados."
            )
        except Exception as e:
            app_logger.error(f"ERRO NO logar_timeline: {e}")
            pass

        if not (wants_json or is_modal):
            flash("Detalhes da implantação atualizados com sucesso!", "success")

        try:
            clear_implantacao_cache(implantacao_id)
            clear_user_cache(usuario_cs_email)
        except Exception as ex:
            app_logger.error(f"Erro ao limpar cache: {ex}")
            pass

        if wants_json or is_modal:
            return jsonify({"ok": True, "implantacao_id": implantacao_id})

    except AttributeError as e:
        if "isoformat" in str(e):
            app_logger.error(f"ERRO: Tentativa de chamar .isoformat() em string: {e}")
            msg = "❌ Erro ao processar data. Verifique o formato (DD/MM/AAAA)."
        else:
            app_logger.error(f"ERRO AttributeError: {e}")
            msg = "❌ Erro ao processar dados. Tente novamente."

        if wants_json or is_modal:
            return jsonify({"ok": False, "error": msg}), 400
        flash(msg, "error")

    except ValueError as e:
        error_msg = str(e)
        app_logger.warning(f"Validation error: {error_msg}")
        msg = error_msg if error_msg else "❌ Dados inválidos. Verifique os campos."

        if wants_json or is_modal:
            return jsonify({"ok": False, "error": msg}), 400
        flash(msg, "error")

    except PermissionError as e:
        app_logger.warning(f"Permission denied: {e}")
        msg = "❌ Você não tem permissão para realizar esta ação."

        if wants_json or is_modal:
            return jsonify({"ok": False, "error": msg}), 403
        flash(msg, "error")

    except TimeoutError as e:
        app_logger.error(f"Timeout error: {e}")
        msg = "❌ Operação demorou muito tempo. Verifique sua conexão e tente novamente."

        if wants_json or is_modal:
            return jsonify({"ok": False, "error": msg}), 504
        flash(msg, "error")

    except Exception as e:
        app_logger.error(f"ERRO COMPLETO ao atualizar detalhes (Impl. ID {implantacao_id}): {e}", exc_info=True)

        error_str = str(e).lower()
        if "database" in error_str or "connection" in error_str:
            msg = "❌ Erro de conexão com o banco de dados. Tente novamente em alguns segundos."
        elif "timeout" in error_str:
            msg = "❌ Tempo de espera esgotado. Tente novamente."
        else:
            msg = "❌ Erro inesperado ao atualizar detalhes. Nossa equipe foi notificada."

        if wants_json or is_modal:
            return jsonify({"ok": False, "error": msg}), 500
        flash(msg, "error")

    return redirect(dest_url)


@grandes_contas_actions_bp.route("/remover_plano_implantacao", methods=["POST"])
@login_required
@limiter.limit("30 per minute", key_func=lambda: g.user_email or get_remote_address())
def remover_plano_implantacao():
    usuario_cs_email = g.user_email
    implantacao_id = request.form.get("implantacao_id")
    user_perfil_acesso = g.perfil.get("perfil_acesso") if g.perfil else None

    dest_url = url_for("grandes_contas.ver_implantacao", impl_id=implantacao_id)

    try:
        from ...domain.implantacao_service import remover_plano_implantacao_service

        remover_plano_implantacao_service(implantacao_id, usuario_cs_email, user_perfil_acesso)

        flash("Plano de sucesso removido com sucesso!", "success")
        try:
            clear_implantacao_cache(implantacao_id)
        except Exception as e:
            app_logger.warning(f"Erro ao limpar cache após remover plano: {e}")
            pass

    except ValueError as e:
        flash(str(e), "error")
    except Exception as e:
        app_logger.error(f"Erro ao remover plano da implantação ID {implantacao_id}: {e}")
        flash(f"Erro ao remover plano: {e}", "error")

    return redirect(dest_url)


@grandes_contas_actions_bp.route("/transferir_implantacao", methods=["POST"])
@login_required
@permission_required(PERFIS_COM_GESTAO)
@limiter.limit("30 per minute", key_func=lambda: g.user_email or get_remote_address())
@audit(action="TRANSFER_IMPLANTACAO_GC", target_type="implantacao")
def transferir_implantacao():
    usuario_cs_email = g.user_email
    implantacao_id = request.form.get("implantacao_id")
    novo_usuario_cs = request.form.get("novo_usuario_cs")
    dest_url = url_for("grandes_contas.ver_implantacao", impl_id=implantacao_id)

    try:
        from ...domain.implantacao_service import transferir_implantacao_service

        antigo_usuario_cs = transferir_implantacao_service(implantacao_id, usuario_cs_email, novo_usuario_cs)

        flash(f"Implantação transferida para {novo_usuario_cs} com sucesso!", "success")
        if antigo_usuario_cs == usuario_cs_email:
            return redirect(url_for("grandes_contas.dashboard"))

    except ValueError as e:
        flash(str(e), "error")
    except Exception as e:
        app_logger.error(f"Erro ao transferir implantação ID {implantacao_id}: {e}")
        flash(f"Erro ao transferir implantação: {e}", "error")

    return redirect(dest_url)


@grandes_contas_actions_bp.route("/excluir_implantacao", methods=["POST"])
@login_required
@limiter.limit("100 per minute", key_func=lambda: g.user_email or get_remote_address())
@audit(action="DELETE_IMPLANTACAO_GC", target_type="implantacao")
def excluir_implantacao():
    usuario_cs_email = g.user_email
    implantacao_id = request.form.get("implantacao_id")
    user_perfil_acesso = g.perfil.get("perfil_acesso") if g.perfil else None

    try:
        from ...domain.implantacao_service import excluir_implantacao_service

        excluir_implantacao_service(implantacao_id, usuario_cs_email, user_perfil_acesso)

        flash("Implantação e todos os dados associados foram excluídos com sucesso.", "success")
        try:
            clear_user_cache(usuario_cs_email)
            clear_implantacao_cache(implantacao_id)
        except Exception:
            pass
    except ValueError as e:
        flash(str(e), "error")
    except Exception as e:
        app_logger.error(f"Erro ao excluir implantação ID {implantacao_id}: {e}")
        flash("Erro ao excluir implantação.", "error")

    return redirect(url_for("grandes_contas.dashboard"))


@grandes_contas_actions_bp.route("/cancelar_implantacao", methods=["POST"])
@login_required
@audit(action="CANCEL_IMPLANTACAO_GC", target_type="implantacao")
def cancelar_implantacao():
    usuario_cs_email = g.user_email
    implantacao_id = request.form.get("implantacao_id")
    data_cancelamento = request.form.get("data_cancelamento")
    motivo = request.form.get("motivo_cancelamento", "").strip()
    user_perfil_acesso = g.perfil.get("perfil_acesso") if g.perfil else None

    if not r2_client:
        flash(
            "Erro: Serviço de armazenamento R2 não configurado. Não é possível fazer upload do comprovante obrigatório.",
            "error",
        )
        return redirect(url_for("grandes_contas.ver_implantacao", impl_id=implantacao_id))

    if not all([implantacao_id, data_cancelamento, motivo]):
        flash("Todos os campos (Data, Motivo Resumo) são obrigatórios para cancelar.", "error")
        return redirect(url_for("grandes_contas.ver_implantacao", impl_id=implantacao_id))

    try:
        data_cancel_iso = validate_date(data_cancelamento)
    except ValidationError:
        flash("Data do cancelamento inválida. Formatos aceitos: DD/MM/AAAA, MM/DD/AAAA, AAAA-MM-DD.", "error")
        return redirect(url_for("grandes_contas.ver_implantacao", impl_id=implantacao_id))

    file = request.files.get("comprovante_cancelamento")
    if not file or file.filename == "":
        flash("O upload do print do e-mail de cancelamento é obrigatório.", "error")
        return redirect(url_for("grandes_contas.ver_implantacao", impl_id=implantacao_id))

    try:
        comprovante_url = None
        if file and utils.allowed_file(file.filename):
            filename = secure_filename(file.filename)
            _, extensao = os.path.splitext(filename)
            nome_unico = f"cancel_proof_{implantacao_id}_{int(time.time())}{extensao}"
            object_name = f"comprovantes_cancelamento/{nome_unico}"

            bucket_name = current_app.config.get("CLOUDFLARE_BUCKET_NAME")
            public_url = current_app.config.get("CLOUDFLARE_PUBLIC_URL")
            r2_ok = (
                bool(r2_client)
                and bool(bucket_name)
                and bool(public_url)
                and bool(current_app.config.get("R2_CONFIGURADO"))
                and bool(re.match(r"^[a-zA-Z0-9.\-_]{1,255}$", bucket_name))
            )

            if r2_ok:
                r2_client.upload_fileobj(file, bucket_name, object_name, ExtraArgs={"ContentType": file.content_type})
                comprovante_url = f"{public_url}/{object_name}"
            else:
                # Fallback local
                base_dir = os.path.join(os.path.dirname(current_app.root_path), "uploads")
                target_dir = os.path.join(base_dir, "comprovantes_cancelamento")
                try:
                    os.makedirs(target_dir, exist_ok=True)
                except Exception:
                    pass
                local_path = os.path.join(target_dir, nome_unico)
                file.stream.seek(0)
                with open(local_path, "wb") as f_out:
                    f_out.write(file.stream.read())
                comprovante_url = url_for("main.serve_upload", filename=f"comprovantes_cancelamento/{nome_unico}")
        else:
            flash("Tipo de arquivo inválido para o comprovante.", "error")
            return redirect(url_for("grandes_contas.ver_implantacao", impl_id=implantacao_id))

        from ...domain.implantacao_service import cancelar_implantacao_service

        cancelar_implantacao_service(
            implantacao_id, usuario_cs_email, user_perfil_acesso, data_cancel_iso, motivo, comprovante_url
        )

        flash("Implantação cancelada com sucesso.", "success")
        return redirect(url_for("grandes_contas.dashboard"))

    except ValueError as e:
        flash(str(e), "error")
        return redirect(url_for("grandes_contas.ver_implantacao", impl_id=implantacao_id))
    except Exception as e:
        app_logger.error(f"Erro ao cancelar implantação ID {implantacao_id}: {e}")
        flash(f"Erro ao cancelar implantação: {e}", "error")
        return redirect(url_for("grandes_contas.ver_implantacao", impl_id=implantacao_id))


@grandes_contas_actions_bp.route("/desfazer_cancelamento_implantacao", methods=["POST"])
@login_required
@audit(action="UNDO_CANCEL_IMPLANTACAO_GC", target_type="implantacao")
def desfazer_cancelamento_implantacao():
    """
    Endpoint para desfazer o cancelamento de uma implantação em Grandes Contas.
    """
    usuario_cs_email = g.user_email
    data = request.get_json()
    if not data:
        return jsonify({"ok": False, "error": "Dados inválidos"}), 400

    implantacao_id = data.get("implantacao_id")
    user_perfil_acesso = g.perfil.get("perfil_acesso") if g.perfil else None

    if not implantacao_id:
        return jsonify({"ok": False, "error": "ID da implantação é obrigatório"}), 400

    try:
        from ...domain.implantacao.status import desfazer_cancelamento_implantacao_service

        desfazer_cancelamento_implantacao_service(implantacao_id, usuario_cs_email, user_perfil_acesso)

        # Limpar caches
        try:
            clear_implantacao_cache(implantacao_id)
            clear_user_cache(usuario_cs_email)
        except Exception:
            pass

        return (
            jsonify({"ok": True, "message": "Cancelamento desfeito com sucesso! A implantação retornou para 'Em Andamento'."}),
            200,
        )

    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    except Exception as e:
        app_logger.error(f"Erro ao desfazer cancelamento GC (ID {implantacao_id}): {e}")
        return jsonify({"ok": False, "error": "Erro interno ao desfazer cancelamento."}), 500


# Rotas 'Jira' também mantidas mas cuidado com URLs de API. 
# Se o JS de frontend chama /api/implantacao/... talvez não precise de mudança se for rota API genérica.
# Mas aqui elas dependem de login_required e parecem ser específicas do blueprint?
# No onboarding.actions a rota é @onboarding_actions_bp.route("/api/implantacao/...")
# Se o frontend usa a URL gerada por 'url_for', eu preciso replicar e atualizar.
# Se o frontend usa URL hardcoded /api/..., terei colisão.
# Verifiquei os JS: 'js/pages/implantacao_detalhes.js' ou similar provavelmente chama isso.

@grandes_contas_actions_bp.route("/api/implantacao/<int:implantacao_id>/jira-issues", methods=["GET"])
@login_required
def get_jira_issues(implantacao_id):
    try:
        from ...domain.implantacao_service import _get_implantacao_and_validate_access

        implantacao, _ = _get_implantacao_and_validate_access(implantacao_id, g.user_email, g.perfil)

        from ...domain.jira_service import get_linked_jira_keys, search_issues_by_context

        extra_keys = get_linked_jira_keys(implantacao_id)
        result = search_issues_by_context(implantacao, extra_keys=extra_keys)

        if extra_keys and "issues" in result:
            returned_keys = set(i.get("key") for i in result["issues"])
            for k in extra_keys:
                if k not in returned_keys:
                    result["issues"].insert(
                        0,
                        {
                            "key": k,
                            "summary": "Carregando detalhes ou Ticket arquivado...",
                            "status": "Salvo",
                            "status_color": "bg-secondary",
                            "created": datetime.now().isoformat(),
                            "type": "Unknown",
                            "priority": "N/A",
                            "link": "#",
                            "is_linked": True,
                            "is_fallback": True,
                        },
                    )

        return jsonify(result)
    except ValueError as e:
        return jsonify({"error": str(e)}), 403
    except Exception as e:
        app_logger.error(f"Erro na rota jira-issues GC: {e}")
        return jsonify({"error": "Erro interno servidor"}), 500


@grandes_contas_actions_bp.route("/api/implantacao/<int:implantacao_id>/jira-issues", methods=["POST"])
@login_required
def create_jira_issue_action(implantacao_id):
    try:
        from ...domain.implantacao_service import _get_implantacao_and_validate_access

        implantacao, _ = _get_implantacao_and_validate_access(implantacao_id, g.user_email, g.perfil)

        files_list = None
        data = None

        if request.content_type and "multipart/form-data" in request.content_type:
            data = request.form.to_dict()
            files_list = request.files.getlist("files")
        else:
            data = request.get_json()

        if not data:
            return jsonify({"error": "JSON ou Form inválido"}), 400

        from ...domain.jira_service import create_jira_issue, save_jira_link

        result = create_jira_issue(implantacao, data, files=files_list)

        if result.get("success"):
            try:
                new_key = result.get("key")
                if new_key:
                    save_jira_link(implantacao_id, new_key, g.user_email)
            except Exception as e:
                app_logger.warning(f"Erro ao salvar link do Jira recém criado: {e}")

        return jsonify(result)

    except ValueError as e:
        return jsonify({"error": str(e)}), 403
    except Exception as e:
        app_logger.error(f"Erro ao criar issue Jira GC: {e}")
        return jsonify({"error": "Erro ao criar ticket"}), 500


@grandes_contas_actions_bp.route("/api/implantacao/<int:implantacao_id>/jira-issues/fetch", methods=["POST"])
@login_required
def fetch_jira_issue_action(implantacao_id):
    try:
        data = request.get_json()
        if not data or "key" not in data:
            return jsonify({"error": "Chave do ticket obrigatória"}), 400

        key = data["key"].strip().upper()

        from ...domain.implantacao_service import _get_implantacao_and_validate_access

        _get_implantacao_and_validate_access(implantacao_id, g.user_email, g.perfil)

        from ...domain.jira_service import get_issue_details, save_jira_link

        result = get_issue_details(key)

        if "error" in result:
            return jsonify(result), 404

        try:
            save_jira_link(implantacao_id, key, g.user_email)
        except Exception as e_save:
            app_logger.error(f"Erro ao salvar link Jira: {e_save}")
            return jsonify({"error": f"Erro de persistência: {str(e_save)}", "issue": result.get("issue")}), 500

        if "issue" in result:
            result["issue"]["is_linked"] = True

        return jsonify(result)

    except Exception as e:
        app_logger.error(f"Erro ao buscar/vincular ticket Jira {implantacao_id}: {e}")
        return jsonify({"error": str(e)}), 500


@grandes_contas_actions_bp.route("/api/implantacao/<int:implantacao_id>/jira-issues/<path:jira_key>", methods=["DELETE"])
@login_required
def delete_jira_link_action(implantacao_id, jira_key):
    try:
        jira_key = jira_key.strip().upper()

        from ...domain.implantacao_service import _get_implantacao_and_validate_access

        _get_implantacao_and_validate_access(implantacao_id, g.user_email, g.perfil)

        from ...domain.jira_service import remove_jira_link

        remove_jira_link(implantacao_id, jira_key)

        return jsonify({"success": True, "message": "Vínculo removido com sucesso"})

    except ValueError as e:
        return jsonify({"error": str(e)}), 403
    except Exception as e:
        app_logger.error(f"Erro na exclusão de vinculo Jira: {e}")
        return jsonify({"error": "Erro interno servidor"}), 500
