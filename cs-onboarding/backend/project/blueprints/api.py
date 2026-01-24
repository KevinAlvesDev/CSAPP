# -*- coding: utf-8 -*-


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
from ..domain.implantacao_service import _get_progress
from ..security.api_security import validate_api_origin
from ..security.context_validator import validate_context_access

api_bp = Blueprint("api", __name__, url_prefix="/api")


@api_bp.before_request
def _api_origin_guard():
    return validate_api_origin(lambda: None)()


@api_bp.route("/progresso_implantacao/<int:impl_id>", methods=["GET"])
@validate_api_origin
def progresso_implantacao(impl_id):
    try:
        impl_id = validate_integer(impl_id, min_value=1)
    except ValidationError as e:
        return jsonify({"ok": False, "error": f"ID inválido: {str(e)}"}), 400
    try:
        pct, total, done = _get_progress(impl_id)
        return jsonify({"ok": True, "progresso": pct, "total": total, "concluidas": done})
    except Exception as e:
        api_logger.error(f"Erro ao obter progresso da implantação {impl_id}: {e}", exc_info=True)
        return jsonify({"ok": False, "error": "Erro interno"}), 500


@api_bp.route("/implantacao/<int:impl_id>/timeline", methods=["GET"])
@login_required
@validate_api_origin
@validate_context_access(id_param='impl_id', entity_type='implantacao')
@limiter.limit("200 per minute", key_func=lambda: g.user_email or get_remote_address())
def get_timeline(impl_id: int):
    try:
        impl_id = validate_integer(impl_id, min_value=1)
    except ValidationError as e:
        return jsonify({"ok": False, "error": f"ID inválido: {str(e)}"}), 400

    page = request.args.get("page", type=int) or 1
    per_page = request.args.get("per_page", type=int) or 50
    if per_page > 200:
        per_page = 200
    types_param = request.args.get("types", "")
    q = request.args.get("q", "")
    dt_from = request.args.get("from", "")
    dt_to = request.args.get("to", "")

    try:
        from ..domain.timeline_service import get_timeline_logs

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
@validate_context_access(id_param='impl_id', entity_type='implantacao')
@limiter.limit("30 per minute", key_func=lambda: g.user_email or get_remote_address())
def export_timeline(impl_id: int):
    try:
        impl_id = validate_integer(impl_id, min_value=1)
    except ValidationError as e:
        return jsonify({"ok": False, "error": f"ID inválido: {str(e)}"}), 400

    types_param = request.args.get("types", "")
    q = request.args.get("q", "")
    dt_from = request.args.get("from", "")
    dt_to = request.args.get("to", "")

    try:
        from ..domain.timeline_service import export_timeline_csv

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
                id_favorecido = validate_integer(digits_only, min_value=1)
        except Exception:
            id_favorecido = None

    from ..domain.external_service import consultar_empresa_oamd

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
        from ..domain.notification_service import get_user_notifications

        user_email = g.user_email
        context = request.args.get("context")
        
        api_logger.info(f"Buscando notificações para {user_email} no contexto {context}")
        
        # TEMPORÁRIO: Retornar dados mockados para debug
        # return jsonify({
        #     "ok": True,
        #     "notifications": [
        #         {"type": "info", "title": "Teste", "message": "Notificação de teste", "priority": 1, "action_url": "#"}
        #     ],
        #     "total": 1,
        #     "timestamp": datetime.now().isoformat()
        # })
        
        result = get_user_notifications(user_email, context=context)

        if not result.get("ok"):
            api_logger.error(f"Erro ao buscar notificações: {result.get('error')}")
            return jsonify(result), 500

        api_logger.info(f"Notificações retornadas com sucesso: {result.get('total', 0)} notificações")
        return jsonify(result)
    except Exception as e:
        api_logger.error(f"Erro crítico ao buscar notificações: {e}", exc_info=True)
        return jsonify({"ok": False, "error": str(e), "notifications": []}), 500


@api_bp.route("/notifications/test", methods=["GET"])
@login_required
@validate_api_origin
def test_notifications():
    """
    Endpoint de teste para visualizar todos os tipos de notificações.
    Acesse: /api/notifications/test
    """
    from datetime import datetime

    # Simula todos os 9 tipos de notificações
    test_notifications = [
        {"type": "danger", "title": "🔥 Academia XYZ - 5 tarefas críticas", "message": "3 atrasadas, 2 vencem hoje"},
        {
            "type": "danger",
            "title": "⏸️ Gym ABC parada há 14 dias",
            "message": "Motivo: Aguardando documentação do cliente",
        },
        {"type": "warning", "title": "⏰ Studio Fit - 3 tarefas urgentes", "message": "Vence em 1-2 dias"},
        {"type": "warning", "title": "📅 Crossfit Pro inicia em 7 dias", "message": "Prepare-se para o início!"},
        {
            "type": "warning",
            "title": "⏳ Pilates Center há 37 dias sem previsão",
            "message": "Defina uma data de início",
        },
        {"type": "info", "title": "⚠️ Yoga Studio - 2 tarefas próximas", "message": "Vence em 3-7 dias"},
        {"type": "info", "title": "📋 3 implantações aguardando início", "message": "Na aba 'Novas' do dashboard"},
        {"type": "info", "title": "📊 Resumo da semana", "message": "23 tarefas pendentes em 4 implantações"},
        {
            "type": "success",
            "title": "✅ 2 implantações concluídas esta semana",
            "message": "Parabéns pelo progresso! 🎉",
        },
    ]

    return jsonify(
        {
            "ok": True,
            "notifications": test_notifications,
            "total": len(test_notifications),
            "timestamp": datetime.now().isoformat(),
            "test_mode": True,
        }
    )
