from flask import Blueprint, g, jsonify, make_response, request



from ..blueprints.auth import login_required



# Importar cache para invalidação

try:

    from ..config.cache_config import cache

except ImportError:

    cache = None





from flask_limiter.util import get_remote_address



from ..common.validation import ValidationError, validate_integer

from ..config.logging_config import api_logger

from ..core.extensions import limiter

from ..modules.implantacao.domain import _get_progress

from ..security.api_security import validate_api_origin

from ..security.context_validator import validate_context_access



api_bp = Blueprint("api", __name__, url_prefix="/api")





@api_bp.before_request

def _api_origin_guard():

    return validate_api_origin(lambda: None)()





@api_bp.route("/progresso_implantacao/<int:impl_id>", methods=["GET"])

@login_required

@validate_api_origin

@validate_context_access(id_param="impl_id", entity_type="implantacao")

@limiter.limit("2000 per minute")

def progresso_implantacao(impl_id):

    try:

        impl_id = validate_integer(impl_id, min_value=1)

    except ValidationError as e:

        return jsonify({"ok": False, "error": f"ID inválido: {e!s}"}), 400

    try:

        pct, total, done = _get_progress(impl_id)

        return jsonify({"ok": True, "progresso": pct, "total": total, "concluidas": done})

    except Exception as e:

        api_logger.error(f"Erro ao obter progresso da implantação {impl_id}: {e}", exc_info=True)

        return jsonify({"ok": False, "error": "Erro interno"}), 500





@api_bp.route("/implantacao/<int:impl_id>/timeline", methods=["GET"])

@login_required

@validate_api_origin

@validate_context_access(id_param="impl_id", entity_type="implantacao")

@limiter.limit("200 per minute", key_func=lambda: g.user_email or get_remote_address())

def get_timeline(impl_id: int):

    try:

        val_id = validate_integer(impl_id, min_value=1)

        if val_id is None:

            return jsonify({"ok": False, "error": "ID inválido"}), 400

        impl_id = val_id

    except ValidationError as e:

        return jsonify({"ok": False, "error": f"ID inválido: {e!s}"}), 400



    page_num = request.args.get("page", 1, type=int)

    page = int(page_num) if page_num is not None else 1

    

    per_page_num = request.args.get("per_page", 50, type=int)

    per_page = int(per_page_num) if per_page_num is not None else 50

    if per_page > 200:

        per_page = 200

    types_param = request.args.get("types", "")

    q = request.args.get("q", "")

    dt_from = request.args.get("from", "")

    dt_to = request.args.get("to", "")



    try:

        from ..modules.timeline.application.timeline_service import get_timeline_logs



        data = get_timeline_logs(

            impl_id=impl_id,

            page=page,

            per_page=per_page,

            types_param=types_param,

            q=q,

            dt_from=dt_from,

            dt_to=dt_to,

        )

        return jsonify({"ok": True, "logs": data["logs"], "pagination": data["pagination"]})

    except Exception as e:

        api_logger.error(f"Erro ao buscar timeline da implantação {impl_id}: {e}", exc_info=True)

        return jsonify({"ok": False, "error": "Erro interno ao buscar timeline"}), 500





@api_bp.route("/implantacao/<int:impl_id>/timeline/export", methods=["GET"])

@login_required

@validate_api_origin

@validate_context_access(id_param="impl_id", entity_type="implantacao")

@limiter.limit("30 per minute", key_func=lambda: g.user_email or get_remote_address())

def export_timeline(impl_id: int):

    try:

        val_id = validate_integer(impl_id, min_value=1)

        if val_id is None:

            return jsonify({"ok": False, "error": "ID inválido"}), 400

        impl_id = val_id

    except ValidationError as e:

        return jsonify({"ok": False, "error": f"ID inválido: {e!s}"}), 400

    from ..modules.perfis.application.perfis_service import verificar_permissao_por_contexto
    if not verificar_permissao_por_contexto(g.perfil, "timeline.export"):
        return jsonify({"ok": False, "error": "Sem permissão para exportar timeline"}), 403

    types_param = request.args.get("types", "")

    q = request.args.get("q", "")

    dt_from = request.args.get("from", "")

    dt_to = request.args.get("to", "")



    try:

        from ..modules.timeline.application.timeline_service import export_timeline_csv



        csv_content = export_timeline_csv(

            impl_id=impl_id,

            types_param=types_param,

            q=q,

            dt_from=dt_from,

            dt_to=dt_to,

        )

        resp = make_response(csv_content)

        resp.headers["Content-Type"] = "text/csv; charset=utf-8"

        resp.headers["Content-Disposition"] = f'attachment; filename="timeline_implantacao_{impl_id}.csv"'

        return resp

    except Exception as e:

        api_logger.error(f"Erro ao exportar timeline da implantação {impl_id}: {e}", exc_info=True)

        return jsonify({"ok": False, "error": "Erro interno ao exportar timeline"}), 500





@api_bp.route("/implantacao/<int:impl_id>/resumo", methods=["POST"])

@login_required

@validate_api_origin

@validate_context_access(id_param="impl_id", entity_type="implantacao")

@limiter.limit("30 per minute", key_func=lambda: g.user_email or get_remote_address())

def gerar_resumo_implantacao(impl_id: int):

    try:

        val_id = validate_integer(impl_id, min_value=1)

        if val_id is None:

            return jsonify({"ok": False, "error": "ID inválido"}), 400

        impl_id = val_id

    except ValidationError as e:

        return jsonify({"ok": False, "error": f"ID inválido: {e!s}"}), 400



    try:

        from ..modules.implantacao.application.summary_service import gerar_resumo_implantacao_service



        perfil_acesso = g.perfil.get("perfil_acesso") if g.get("perfil") else None

        result = gerar_resumo_implantacao_service(

            impl_id=impl_id,

            user_email=g.user_email,

            perfil_acesso=perfil_acesso,

        )

        return jsonify({"ok": True, **result})

    except ValueError as e:

        return jsonify({"ok": False, "error": str(e)}), 400

    except Exception as e:

        api_logger.error(f"Erro ao gerar resumo da implantacao {impl_id}: {e}", exc_info=True)

        return jsonify({"ok": False, "error": "Erro interno ao gerar resumo"}), 500





@api_bp.route("/consultar_empresa", methods=["GET"])

@login_required

@validate_api_origin

@limiter.limit("20 per minute", key_func=lambda: g.user_email or get_remote_address())

def consultar_empresa():

    """

    Endpoint para consultar dados da empresa no banco externo (OAMD) via ID Favorecido (codigofinanceiro).

    """

    raw_id = request.args.get("id_favorecido")

    infra_req = request.args.get("infra") or request.args.get("zw") or request.args.get("infra_code")



    id_favorecido = None

    if raw_id:

        try:

            import re as _re



            digits_only = "".join(_re.findall(r"\d+", str(raw_id)))

            if digits_only:

                val = validate_integer(digits_only, min_value=1)

                id_favorecido = int(val) if val is not None else None

        except Exception as exc:

            api_logger.error(f"Erro ao validar ID favorecido: {exc}", exc_info=True)

            id_favorecido = None



    from ..modules.implantacao.infra.external_service import consultar_empresa_oamd



    result = consultar_empresa_oamd(id_favorecido, infra_req)



    status_code = result.pop("status_code", 200)

    return jsonify(result), status_code





@api_bp.route("/notifications", methods=["GET"])

@login_required

@validate_api_origin

@limiter.limit("60 per minute", key_func=lambda: g.user_email or get_remote_address())

def get_notifications():

    """

    Sistema completo de notificações para o implantador.

    Refatorado: Usa notification_service para a lógica de negócio.

    """

    try:

        from ..modules.notification.application.notification_service import get_user_notifications



        user_email = g.user_email

        context = request.args.get("context")



        api_logger.info(f"Buscando notificações para {user_email} no contexto {context}")



        result = get_user_notifications(user_email, context=context)



        if not result.get("ok"):

            api_logger.error(f"Erro ao buscar notificações: {result.get('error')}")

            return jsonify(result), 500



        api_logger.info(f"Notificações retornadas com sucesso: {result.get('total', 0)} notificações")

        return jsonify(result)

    except Exception as e:

        api_logger.error(f"Erro crítico ao buscar notificações: {e}", exc_info=True)

        return jsonify({"ok": False, "error": str(e), "notifications": []}), 500
