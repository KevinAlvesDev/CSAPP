import re

import contextlib

from datetime import datetime, timezone



from flask import flash, g, jsonify, redirect, request, url_for



from ....config.cache_config import clear_dashboard_cache, clear_implantacao_cache, clear_user_cache

from ....config.logging_config import app_logger





def handle_criar_implantacao(

    *,

    contexto: str,

    dashboard_endpoint: str,

    success_message: str,

    clear_dashboard: bool,

) -> object:

    usuario_criador = g.user_email

    from ....common.validation import sanitize_string, validate_integer

    from ..domain.crud import criar_implantacao_service



    nome_empresa = sanitize_string(request.form.get("nome_empresa", ""), max_length=200)

    usuario_atribuido = sanitize_string(request.form.get("usuario_atribuido_cs", ""), max_length=100)

    usuario_atribuido = usuario_atribuido or usuario_criador



    id_favorecido_raw = request.form.get("id_favorecido")

    id_favorecido = None

    if id_favorecido_raw:

        with contextlib.suppress(Exception):

            digits_only = "".join(re.findall(r"\d+", str(id_favorecido_raw)))

            if digits_only:

                id_favorecido = validate_integer(digits_only, min_value=1)



    implantacao_id = criar_implantacao_service(

        nome_empresa, usuario_atribuido, usuario_criador, id_favorecido, contexto=contexto

    )



    flash(success_message.format(nome_empresa=nome_empresa), "success")



    with contextlib.suppress(Exception):

        clear_user_cache(usuario_criador)

        if usuario_atribuido and usuario_atribuido != usuario_criador:

            clear_user_cache(usuario_atribuido)

        clear_implantacao_cache(implantacao_id)

        if clear_dashboard:

            clear_dashboard_cache()

            

    return redirect(url_for(dashboard_endpoint, context=getattr(g, "modulo_atual", None)))





def handle_criar_implantacao_modulo(

    *,

    contexto: str,

    dashboard_endpoint: str,

    success_message: str,

    clear_dashboard: bool,

) -> object:

    usuario_criador = g.user_email

    from ....common.validation import sanitize_string, validate_integer

    from ..domain.crud import criar_implantacao_modulo_service



    nome_empresa = sanitize_string(request.form.get("nome_empresa_modulo", ""), max_length=200)

    usuario_atribuido = sanitize_string(request.form.get("usuario_atribuido_cs_modulo", ""), max_length=100)

    modulo_tipo = sanitize_string(request.form.get("modulo_tipo", ""), max_length=50)



    id_favorecido_raw = request.form.get("id_favorecido")

    id_favorecido = None

    if id_favorecido_raw:

        with contextlib.suppress(Exception):

            digits_only = "".join(re.findall(r"\d+", str(id_favorecido_raw)))

            if digits_only:

                id_favorecido = validate_integer(digits_only, min_value=1)



    implantacao_id = criar_implantacao_modulo_service(

        nome_empresa, usuario_atribuido, usuario_criador, modulo_tipo, id_favorecido, contexto=contexto

    )



    with contextlib.suppress(Exception):

        clear_user_cache(usuario_criador)

        if usuario_atribuido and usuario_atribuido != usuario_criador:

            clear_user_cache(usuario_atribuido)

        clear_implantacao_cache(implantacao_id)

        if clear_dashboard:

            clear_dashboard_cache()



    flash(success_message.format(nome_empresa=nome_empresa, usuario_atribuido=usuario_atribuido), "success")

    return redirect(url_for(dashboard_endpoint, context=getattr(g, "modulo_atual", None)))





def handle_iniciar_implantacao(

    *,

    dashboard_endpoint: str,

    detail_endpoint: str,

    success_message: str,

    clear_dashboard: bool,

) -> object:

    usuario_cs_email = g.user_email

    from ....common.validation import validate_integer

    from ..domain.status import iniciar_implantacao_service



    implantacao_id = validate_integer(request.form.get("implantacao_id"), min_value=1)



    iniciar_implantacao_service(implantacao_id, usuario_cs_email)

    flash(success_message, "success")

    

    with contextlib.suppress(Exception):

        clear_user_cache(usuario_cs_email)

        clear_implantacao_cache(implantacao_id)

        if clear_dashboard:

            clear_dashboard_cache()



    return redirect(url_for(detail_endpoint, impl_id=implantacao_id, context=getattr(g, "modulo_atual", None)))





def handle_desfazer_inicio_implantacao(*, clear_dashboard: bool) -> object:

    data = request.get_json()

    if not data:

        return jsonify({"error": "Dados inválidos"}), 400



    implantacao_id = data.get("implantacao_id")

    usuario_cs_email = g.user_email



    if not implantacao_id:

        return jsonify({"error": "ID da implantação é obrigatório"}), 400



    from ..domain.status import desfazer_inicio_implantacao_service

    desfazer_inicio_implantacao_service(implantacao_id, usuario_cs_email)



    with contextlib.suppress(Exception):

        clear_implantacao_cache(implantacao_id)

        clear_user_cache(usuario_cs_email)

        if clear_dashboard:

            clear_dashboard_cache()



    return jsonify({"message": "Início da implantação desfeito com sucesso!"}), 200





def handle_agendar_implantacao(*, dashboard_endpoint: str, clear_dashboard: bool) -> object:

    usuario_cs_email = g.user_email

    implantacao_id = request.form.get("implantacao_id", "")

    data_prevista = request.form.get("data_inicio_previsto")



    from ....common.validation import validate_date

    from ..domain.status import agendar_implantacao_service



    if not data_prevista:

        from ....common.exceptions import ValidationError

        raise ValidationError("A data de início previsto é obrigatória.")

    

    data_prevista_iso = validate_date(data_prevista)



    nome_empresa = agendar_implantacao_service(implantacao_id, usuario_cs_email, data_prevista_iso)

    flash(f'Implantação "{nome_empresa}" movida para "Futuras" com início em {data_prevista}.', "success")

    

    with contextlib.suppress(Exception):

        clear_user_cache(usuario_cs_email)

        clear_implantacao_cache(implantacao_id)

        if clear_dashboard:

            clear_dashboard_cache()



    return redirect(url_for(dashboard_endpoint, context=getattr(g, "modulo_atual", None), refresh="1"))





def handle_marcar_sem_previsao(*, dashboard_endpoint: str, clear_dashboard: bool) -> object:

    usuario_cs_email = g.user_email

    implantacao_id_raw = request.form.get("implantacao_id")

    

    from ....common.validation import validate_integer

    from ..domain.status import marcar_sem_previsao_service



    implantacao_id = validate_integer(implantacao_id_raw, min_value=1)



    nome_empresa = marcar_sem_previsao_service(implantacao_id, usuario_cs_email)

    flash(f'Implantação "{nome_empresa}" marcada como "Sem previsão".', "success")

    

    with contextlib.suppress(Exception):

        clear_user_cache(usuario_cs_email)

        clear_implantacao_cache(implantacao_id)

        if clear_dashboard:

            clear_dashboard_cache()



    return redirect(url_for(dashboard_endpoint, context=getattr(g, "modulo_atual", None), refresh="1"))





def handle_finalizar_implantacao(*, dashboard_endpoint: str, detail_endpoint: str, clear_dashboard: bool) -> object:

    usuario_cs_email = g.user_email

    implantacao_id = request.form.get("implantacao_id", "")

    redirect_target = request.form.get("redirect_to", "dashboard")

    dest_url = url_for(dashboard_endpoint, context=getattr(g, "modulo_atual", None))

    if redirect_target == "detalhes":

        dest_url = url_for(detail_endpoint, impl_id=implantacao_id, context=getattr(g, "modulo_atual", None))



    from ....common.validation import validate_date

    from ..domain.status import finalizar_implantacao_service



    data_finalizacao = request.form.get("data_finalizacao")

    if not data_finalizacao:

        from ....common.exceptions import ValidationError

        raise ValidationError("A data da finalização é obrigatória.")

    

    data_final_iso = validate_date(data_finalizacao)



    finalizar_implantacao_service(implantacao_id, usuario_cs_email, data_final_iso)

    flash("Implantação finalizada com sucesso!", "success")

    

    with contextlib.suppress(Exception):

        clear_user_cache(usuario_cs_email)

        clear_implantacao_cache(implantacao_id)

        if clear_dashboard:

            clear_dashboard_cache()



    return redirect(dest_url)





def handle_parar_implantacao(*, detail_endpoint: str, clear_dashboard: bool, success_message: str) -> object:

    usuario_cs_email = g.user_email

    implantacao_id_val = request.form.get("implantacao_id")

    implantacao_id = str(implantacao_id_val) if implantacao_id_val is not None else ""

    motivo = request.form.get("motivo_parada", "").strip()

    data_parada = request.form.get("data_parada")

    dest_url = url_for(detail_endpoint, impl_id=implantacao_id, context=getattr(g, "modulo_atual", None))



    if not motivo:

        flash("O motivo da parada é obrigatório.", "error")

        return redirect(dest_url)

    if not data_parada:

        flash("A data da parada é obrigatória.", "error")

        return redirect(dest_url)

    from ....common.validation import ValidationError, validate_date



    try:

        data_parada_iso = validate_date(data_parada)

    except ValidationError:

        flash("Data da parada inválida. Formatos aceitos: DD/MM/AAAA, MM/DD/AAAA, AAAA-MM-DD.", "error")

        return redirect(dest_url)



    try:

        user_perfil_acesso = g.perfil.get("perfil_acesso") if getattr(g, "perfil", None) else None



        from ..domain.status import parar_implantacao_service



        parar_implantacao_service(implantacao_id, usuario_cs_email, user_perfil_acesso, data_parada_iso, motivo)

        flash(success_message, "success")

        try:

            clear_user_cache(usuario_cs_email)

            clear_implantacao_cache(implantacao_id)

            if clear_dashboard:

                clear_dashboard_cache()

        except Exception as e:

            app_logger.warning(f"Falha ao limpar cache após parar implantação {implantacao_id}: {e}", exc_info=True)

    except ValueError as e:

        flash(str(e), "error")

    except Exception as e:

        app_logger.error(f"Erro ao parar implantação ID {implantacao_id}: {e}", exc_info=True)

        flash(f"Erro ao parar implantação: {e}", "error")



    return redirect(dest_url)





def handle_retomar_implantacao(*, dashboard_endpoint: str, detail_endpoint: str, clear_dashboard: bool) -> object:

    usuario_cs_email = g.user_email

    implantacao_id_val = request.form.get("implantacao_id")

    implantacao_id = str(implantacao_id_val) if implantacao_id_val is not None else ""

    redirect_to = request.form.get("redirect_to", "dashboard")

    dest_url = url_for(dashboard_endpoint, context=getattr(g, "modulo_atual", None))

    if redirect_to == "detalhes":

        dest_url = url_for(detail_endpoint, impl_id=implantacao_id, context=getattr(g, "modulo_atual", None))



    try:

        user_perfil_acesso = g.perfil.get("perfil_acesso") if getattr(g, "perfil", None) else None



        from ..domain.status import retomar_implantacao_service



        retomar_implantacao_service(implantacao_id, usuario_cs_email, user_perfil_acesso)

        flash('Implantação retomada e movida para "Em Andamento".', "success")

        try:

            clear_user_cache(usuario_cs_email)

            clear_implantacao_cache(implantacao_id)

            if clear_dashboard:

                clear_dashboard_cache()

        except Exception as e:

            app_logger.warning(f"Falha ao limpar cache após retomar implantação {implantacao_id}: {e}", exc_info=True)

    except ValueError as e:

        flash(str(e), "error")

        return redirect(request.referrer or dest_url)

    except Exception as e:

        app_logger.error(f"Erro ao retomar implantação ID {implantacao_id}: {e}", exc_info=True)

        flash(f"Erro ao retomar implantação: {e}", "error")



    return redirect(dest_url)





def handle_reabrir_implantacao(*, dashboard_endpoint: str, detail_endpoint: str, clear_dashboard: bool) -> object:

    usuario_cs_email = g.user_email

    implantacao_id_val = request.form.get("implantacao_id")

    implantacao_id = str(implantacao_id_val) if implantacao_id_val is not None else ""

    redirect_to = request.form.get("redirect_to", "dashboard")

    dest_url = url_for(dashboard_endpoint, context=getattr(g, "modulo_atual", None))

    if redirect_to == "detalhes":

        dest_url = url_for(detail_endpoint, impl_id=implantacao_id, context=getattr(g, "modulo_atual", None))



    try:

        from ..domain.status import reabrir_implantacao_service



        reabrir_implantacao_service(implantacao_id, usuario_cs_email)

        flash('Implantação reaberta com sucesso e movida para "Em Andamento".', "success")

        try:

            clear_user_cache(usuario_cs_email)

            clear_implantacao_cache(implantacao_id)

            if clear_dashboard:

                clear_dashboard_cache()

        except Exception as e:

            app_logger.warning(f"Falha ao limpar cache após reabrir implantação {implantacao_id}: {e}", exc_info=True)

    except ValueError as e:

        flash(str(e), "error")

        return redirect(request.referrer or url_for(dashboard_endpoint, context=getattr(g, "modulo_atual", None)))

    except Exception as e:

        app_logger.error(f"Erro ao reabrir implantação ID {implantacao_id}: {e}", exc_info=True)

        flash(f"Erro ao reabrir implantação: {e}", "error")



    return redirect(dest_url)





def handle_atualizar_detalhes_empresa(*, dashboard_endpoint: str, detail_endpoint: str, clear_dashboard: bool) -> object:

    from ....db import logar_timeline

    from ....shared.form_processors import build_detalhes_campos



    usuario_cs_email = g.user_email

    implantacao_id_val = request.form.get("implantacao_id")

    implantacao_id = str(implantacao_id_val) if implantacao_id_val is not None else ""

    redirect_to = request.form.get("redirect_to", "dashboard")

    user_perfil_acesso = g.perfil.get("perfil_acesso") if g.perfil else None



    wants_json = "application/json" in (request.headers.get("Accept") or "")

    is_modal = (redirect_to or "").lower() == "modal"



    dest_url = url_for(dashboard_endpoint, context=getattr(g, "modulo_atual", None))

    if redirect_to == "detalhes":

        dest_url = url_for(detail_endpoint, impl_id=implantacao_id, context=getattr(g, "modulo_atual", None))



    try:

        final_campos, error = build_detalhes_campos()



        if error:

            if wants_json or is_modal:

                return jsonify({"ok": False, "error": error}), 400

            flash(error, "warning")

            return redirect(dest_url)



        from ..domain.details import atualizar_detalhes_empresa_service



        atualizar_detalhes_empresa_service(implantacao_id, usuario_cs_email, user_perfil_acesso, final_campos)



        try:

            logar_timeline(

                implantacao_id, usuario_cs_email, "detalhes_alterados", "Detalhes da empresa/cliente foram atualizados."

            )

        except Exception as e:

            app_logger.error(f"ERRO NO logar_timeline: {e}", exc_info=True)



        if not (wants_json or is_modal):

            flash("Detalhes da implantação atualizados com sucesso!", "success")



        try:

            clear_implantacao_cache(implantacao_id)

            clear_user_cache(usuario_cs_email)

            if clear_dashboard:

                clear_dashboard_cache()

        except Exception as ex:

            app_logger.error(f"Erro ao limpar cache: {ex}", exc_info=True)



        if wants_json or is_modal:

            return jsonify({"ok": True, "implantacao_id": implantacao_id})



    except AttributeError as e:

        if "isoformat" in str(e):

            app_logger.error(f"ERRO: Tentativa de chamar .isoformat() em string: {e}", exc_info=True)

            msg = "❌ Erro ao processar data. Verifique o formato (DD/MM/AAAA)."

        else:

            app_logger.error(f"ERRO AttributeError: {e}", exc_info=True)

            msg = "❌ Erro ao processar dados. Tente novamente."



        if wants_json or is_modal:

            return jsonify({"ok": False, "error": msg}), 400

        flash(msg, "error")



    except ValueError as e:

        error_msg = str(e)

        app_logger.warning(f"Validation error: {error_msg}", exc_info=True)

        msg = error_msg if error_msg else "❌ Dados inválidos. Verifique os campos."



        if wants_json or is_modal:

            return jsonify({"ok": False, "error": msg}), 400

        flash(msg, "error")



    except PermissionError as e:

        app_logger.warning(f"Permission denied: {e}", exc_info=True)

        msg = "❌ Você não tem permissão para realizar esta ação."



        if wants_json or is_modal:

            return jsonify({"ok": False, "error": msg}), 403

        flash(msg, "error")



    except TimeoutError as e:

        app_logger.error(f"Timeout error: {e}", exc_info=True)

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

def handle_remover_plano_implantacao(*, detail_endpoint: str, clear_dashboard: bool) -> object:

    usuario_cs_email = g.user_email

    implantacao_id_val = request.form.get("implantacao_id")

    implantacao_id = str(implantacao_id_val) if implantacao_id_val is not None else ""

    user_perfil_acesso = g.perfil.get("perfil_acesso") if g.perfil else None

    dest_url = url_for(detail_endpoint, impl_id=implantacao_id, context=getattr(g, "modulo_atual", None))



    from ..domain.crud import remover_plano_implantacao_service

    remover_plano_implantacao_service(int(implantacao_id), usuario_cs_email, str(user_perfil_acesso or ""))

    flash("Plano de sucesso removido com sucesso!", "success")

    

    with contextlib.suppress(Exception):

        clear_implantacao_cache(implantacao_id)

        if clear_dashboard:

            clear_dashboard_cache()



    return redirect(dest_url)





def handle_transferir_implantacao(*, dashboard_endpoint: str, detail_endpoint: str) -> object:

    usuario_cs_email = g.user_email

    implantacao_id_val = request.form.get("implantacao_id")

    implantacao_id = str(implantacao_id_val) if implantacao_id_val is not None else ""

    novo_usuario_cs = request.form.get("novo_usuario_cs")

    dest_url = url_for(detail_endpoint, impl_id=implantacao_id, context=getattr(g, "modulo_atual", None))



    from ..domain.crud import transferir_implantacao_service

    antigo_usuario_cs = transferir_implantacao_service(implantacao_id, usuario_cs_email, novo_usuario_cs)

    flash(f"Implantação transferida para {novo_usuario_cs} com sucesso!", "success")

    if antigo_usuario_cs == usuario_cs_email:

        return redirect(url_for(dashboard_endpoint, context=getattr(g, "modulo_atual", None)))



    return redirect(dest_url)





def handle_excluir_implantacao(*, dashboard_endpoint: str, clear_dashboard: bool) -> object:

    usuario_cs_email = g.user_email

    implantacao_id_val = request.form.get("implantacao_id")

    implantacao_id = str(implantacao_id_val) if implantacao_id_val is not None else ""

    user_perfil_acesso = g.perfil.get("perfil_acesso") if g.perfil else None



    from ..domain.crud import excluir_implantacao_service

    excluir_implantacao_service(implantacao_id, usuario_cs_email, user_perfil_acesso)

    flash("Implantação e todos os dados associados foram excluídos com sucesso.", "success")

    

    with contextlib.suppress(Exception):

        clear_user_cache(usuario_cs_email)

        clear_implantacao_cache(implantacao_id)

        if clear_dashboard:

            clear_dashboard_cache()



    return redirect(url_for(dashboard_endpoint, context=getattr(g, "modulo_atual", None)))





def handle_cancelar_implantacao(*, dashboard_endpoint: str, detail_endpoint: str) -> object:

    usuario_cs_email = g.user_email

    implantacao_id_val = request.form.get("implantacao_id")

    implantacao_id = str(implantacao_id_val) if implantacao_id_val is not None else ""

    data_cancelamento = request.form.get("data_cancelamento")

    motivo = request.form.get("motivo_cancelamento", "").strip()

    user_perfil_acesso = g.perfil.get("perfil_acesso") if g.perfil else None



    if not all([implantacao_id, data_cancelamento, motivo]):

        from ....common.exceptions import ValidationError

        raise ValidationError("Todos os campos (Data e Motivo) são obrigatórios para cancelar.")



    from ....common.validation import validate_date

    data_cancel_iso = validate_date(str(data_cancelamento))



    comprovante_url = None

    from ..domain.crud import cancelar_implantacao_service



    cancelar_implantacao_service(

        implantacao_id, usuario_cs_email, user_perfil_acesso, data_cancel_iso, motivo, comprovante_url

    )



    flash("Implantação cancelada com sucesso.", "success")

    return redirect(url_for(dashboard_endpoint, context=getattr(g, "modulo_atual", None)))





def handle_get_jira_issues(implantacao_id: int, *, log_label: str = "") -> object:

    try:

        from ..domain.access import _get_implantacao_and_validate_access

        from ..infra.jira_service import get_linked_jira_keys, search_issues_by_context



        implantacao, _ = _get_implantacao_and_validate_access(implantacao_id, g.user_email, g.perfil)

        extra_keys = get_linked_jira_keys(implantacao_id)

        result = search_issues_by_context(implantacao, extra_keys=extra_keys)



        if extra_keys and "issues" in result:

            returned_keys = {i.get("key") for i in result["issues"]}

            for key in extra_keys:

                if key not in returned_keys:

                    app_logger.warning(f"[{log_label}] Ticket {key} no BD mas não retornado pelo Jira. Injetando Stub.")

                    result["issues"].insert(

                        0,

                        {

                            "key": key,

                            "summary": "Carregando detalhes ou Ticket arquivado...",

                            "status": "Salvo",

                            "status_color": "bg-secondary",

                            "created": datetime.now(timezone.utc).isoformat(),

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

        app_logger.error(f"Erro na rota jira-issues {log_label}: {e}", exc_info=True)

        return jsonify({"error": "Erro interno servidor"}), 500





def handle_create_jira_issue(implantacao_id: int, *, use_onboarding_status_codes: bool) -> object:

    try:

        from ..domain.access import _get_implantacao_and_validate_access

        from ..infra.jira_service import create_jira_issue, save_jira_link



        implantacao, _ = _get_implantacao_and_validate_access(implantacao_id, g.user_email, g.perfil)



        if request.content_type and "multipart/form-data" in request.content_type:

            data = request.form.to_dict()

            files_list = request.files.getlist("files")

        else:

            data = request.get_json()

            files_list = None



        if not data:

            return jsonify({"error": "JSON ou Form inválido"}), 400



        result = create_jira_issue(implantacao, data, files=files_list)

        if result.get("success"):

            try:

                new_key = result.get("key")

                if new_key:

                    save_jira_link(implantacao_id, new_key, g.user_email)

            except Exception as e_link:

                app_logger.error(f"Erro no auto-vinculo do Jira criado: {e_link}", exc_info=True)

            if use_onboarding_status_codes:

                return jsonify(result), 201

            return jsonify(result)



        if use_onboarding_status_codes:

            return jsonify(result), 400

        return jsonify(result)

    except ValueError as e:

        return jsonify({"error": str(e)}), 403

    except Exception as e:

        app_logger.error(f"Erro na criação de issue Jira: {e}", exc_info=True)

        return jsonify({"error": "Erro interno servidor"}), 500





def handle_fetch_jira_issue(implantacao_id: int) -> object:

    try:

        data = request.get_json()

        if not data or "key" not in data:

            return jsonify({"error": "Chave do ticket obrigatória"}), 400



        key = data["key"].strip().upper()



        from ..domain.access import _get_implantacao_and_validate_access

        from ..infra.jira_service import get_issue_details, save_jira_link



        _get_implantacao_and_validate_access(implantacao_id, g.user_email, g.perfil)

        result = get_issue_details(key)

        if "error" in result:

            return jsonify(result), 404



        try:

            save_jira_link(implantacao_id, key, g.user_email)

        except Exception as e_save:

            app_logger.error(f"Erro ao salvar link Jira: {e_save}", exc_info=True)

            return jsonify({"error": f"Erro de persistência: {e_save!s}", "issue": result.get("issue")}), 500



        if "issue" in result:

            result["issue"]["is_linked"] = True



        return jsonify(result)

    except Exception as e:

        app_logger.error(f"Erro ao buscar/vincular ticket Jira {implantacao_id}: {e}", exc_info=True)

        return jsonify({"error": str(e)}), 500





def handle_delete_jira_link(implantacao_id: int, jira_key: str) -> object:

    try:

        jira_key = jira_key.strip().upper()



        from ..domain.access import _get_implantacao_and_validate_access

        from ..infra.jira_service import remove_jira_link



        _get_implantacao_and_validate_access(implantacao_id, g.user_email, g.perfil)

        remove_jira_link(implantacao_id, jira_key)

        return jsonify({"success": True, "message": "Vínculo removido com sucesso"})

    except ValueError as e:

        return jsonify({"error": str(e)}), 403

    except Exception as e:

        app_logger.error(f"Erro na exclusão de vinculo Jira: {e}", exc_info=True)

        return jsonify({"error": "Erro interno servidor"}), 500




