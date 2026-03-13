import contextlib
import uuid
from datetime import date, datetime, timedelta, timezone
import logging
logger = logging.getLogger(__name__)

import requests
from typing import Any, cast
from flask import Blueprint, current_app, flash, g, jsonify, redirect, render_template, request, session, url_for

from ....blueprints.auth import login_required
from ....config.logging_config import get_logger
from ....core.extensions import oauth

agenda_bp = Blueprint("agenda", __name__)
agenda_logger = get_logger("agenda")


def google_events_endpoint(calendar_id: str = "primary"):
    return f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events"


def _google_oauth_configured():
    return all(
        [
            current_app.config.get("GOOGLE_CLIENT_ID"),
            current_app.config.get("GOOGLE_CLIENT_SECRET"),
            current_app.config.get("GOOGLE_REDIRECT_URI"),
        ]
    )


def _get_google_access_token():
    """Valida configuração OAuth e retorna (access_token, None) ou (None, response_tuple)."""
    if not _google_oauth_configured():
        return None, (jsonify({"ok": False, "error": "Google OAuth não configurado"}), 400)
    access_token = (session.get("google_token") or {}).get("access_token")
    if not access_token:
        return None, (jsonify({"ok": False, "error": "Sessão do Google ausente"}), 401)
    return access_token, None


def _build_event_datetime_fields(payload: dict) -> tuple[dict, str | None]:
    """Constrói campos start/end para o corpo de um evento do Google Calendar.

    Returns:
        (fields_dict, error_msg) — error_msg é None se não houver erro.
        fields_dict vazio indica que nenhuma alteração de horário deve ser feita.
    """
    date_str = payload.get("date")
    start_time = payload.get("startTime")
    end_time = payload.get("endTime")
    time_zone = payload.get("timeZone") or "UTC"
    all_day = payload.get("allDay")

    if all_day is True:
        if not date_str:
            return {}, "date é obrigatório para dia inteiro"
        return {"start": {"date": date_str}, "end": {"date": date_str}}, None

    if all_day is False or (start_time and end_time):
        if not (date_str and start_time and end_time):
            missing = "startTime e endTime são obrigatórios" if date_str else "date, startTime e endTime são obrigatórios"
            return {}, missing
        start_dt = f"{date_str}T{start_time}:00"
        end_dt = f"{date_str}T{end_time}:00"
        return {
            "start": {"dateTime": start_dt, "timeZone": time_zone},
            "end": {"dateTime": end_dt, "timeZone": time_zone},
        }, None

    return {}, None  # Sem alteração de horário (PATCH parcial)


def _call_google_calendar_api(method: str, url: str, access_token: str, json_body: dict | None = None, params=None):
    """Executa requisição à API Google Calendar e retorna resposta Flask-compatível."""
    headers: dict[str, str] = {"Authorization": f"Bearer {access_token}"}
    if json_body is not None:
        headers["Content-Type"] = "application/json"
    try:
        resp = requests.request(method, url, headers=headers, json=json_body, params=params, timeout=10)
        if resp.status_code == 401:
            return jsonify({"ok": False, "error": "Token expirado. Refaça a conexão com o Google."}), 401
        if resp.status_code >= 400:
            return jsonify({"ok": False, "error": resp.text}), resp.status_code
        if resp.status_code == 204:
            return jsonify({"ok": True})
        return jsonify({"ok": True, "event": resp.json()})
    except Exception as e:
        logger.exception("Unhandled exception", exc_info=True)
        return jsonify({"ok": False, "error": str(e)}), 500


@agenda_bp.route("/agenda")
@login_required
def agenda_home():
    with contextlib.suppress(Exception):
        agenda_logger.debug(f"Google OAuth configurado: {_google_oauth_configured()}")
    if not _google_oauth_configured():
        flash(
            "Integração com Google Agenda não está configurada. Defina GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET e GOOGLE_REDIRECT_URI no .env.",
            "warning",
        )
        return render_template("pages/agenda.html", events=[], google_connected=False)

    # Usar token do banco com refresh automático
    try:
        from ..application.google_oauth_service import get_valid_token

        token = get_valid_token(g.user_email)
    except Exception as e:
        agenda_logger.error(f"Erro ao obter token válido: {e}", exc_info=True)
        token = None

    with contextlib.suppress(Exception):
        agenda_logger.debug(f"Token válido obtido: {bool(token)}")

    if not token:
        return render_template("pages/agenda.html", events=[], google_connected=False)

    access_token = token.get("access_token")
    with contextlib.suppress(Exception):
        agenda_logger.debug(f"Access token presente: {bool(access_token)}")
    if not access_token:
        return render_template("pages/agenda.html", events=[], google_connected=False)

    view = request.args.get("view", "semana")
    start_qs = request.args.get("start")
    calendar_id = request.args.get("cal", "primary")
    query_text = request.args.get("q")
    base_day = None
    try:
        base_day = date.fromisoformat(start_qs) if start_qs else date.today()
    except Exception as exc:
        logger.exception("Unhandled exception", exc_info=True)
        base_day = date.today()

    weekday = base_day.weekday()
    days_to_subtract = (weekday + 1) % 7
    week_start = base_day - timedelta(days=days_to_subtract)
    week_end = week_start + timedelta(days=6)

    time_min = f"{week_start.isoformat()}T00:00:00Z"
    time_max = f"{week_end.isoformat()}T23:59:59Z"

    params = {
        "singleEvents": "true",
        "orderBy": "startTime",
        "maxResults": 50,
        "timeMin": time_min,
        "timeMax": time_max,
    }
    if query_text:
        params["q"] = query_text
    params = {k: v for k, v in params.items() if v is not None}

    try:
        agenda_logger.info(f"Buscando eventos no Google Calendar para {g.user_email}")
        resp = requests.get(
            google_events_endpoint(calendar_id),
            headers={"Authorization": f"Bearer {access_token}"},
            params=cast(dict[str, Any], params),
            timeout=10,
        )
        agenda_logger.debug(f"Resposta Google Calendar status={resp.status_code}")
        if resp.status_code == 401:
            flash("Sessão do Google expirou. Conecte novamente a Agenda.", "warning")
            return render_template("pages/agenda.html", events=[], google_connected=False)
        resp.raise_for_status()
        data = resp.json()
        events = data.get("items", [])
        with contextlib.suppress(Exception):
            agenda_logger.info(f"Eventos carregados: {len(events)} para {g.user_email}")
        week_days = [(week_start + timedelta(days=i)).isoformat() for i in range(7)]
        return render_template(
            "pages/agenda.html",
            events=events,
            google_connected=True,
            view=view,
            week_start=week_start.isoformat(),
            week_end=week_end.isoformat(),
            week_days=week_days,
            current_calendar=calendar_id,
            search_query=query_text or "",
        )
    except Exception as e:
        agenda_logger.error(f"Erro ao buscar eventos do Google Calendar para {g.user_email}: {e}", exc_info=True)
        with contextlib.suppress(Exception):
            agenda_logger.debug(f"Corpo erro/resposta: {getattr(resp, 'text', None)}")
        flash("Falha ao carregar eventos da Agenda do Google.", "error")
        return render_template("pages/agenda.html", events=[], google_connected=False, view=view)


@agenda_bp.route("/agenda/connect")
@login_required
def agenda_connect():
    """
    Conecta com Google Calendar usando autorização incremental.
    Solicita apenas o escopo de calendar, mantendo os escopos básicos já concedidos.
    """
    if not _google_oauth_configured():
        flash("Integração com Google Agenda não está configurada.", "warning")
        return redirect(url_for("agenda.agenda_home"))

    try:
        from flask import url_for

        from ..application.google_oauth_service import SCOPE_CALENDAR, user_has_scope

        # Verificar se usuário já tem o escopo de calendar
        if user_has_scope(g.user_email, SCOPE_CALENDAR):
            agenda_logger.info(f"Usuário {g.user_email} já possui escopo de calendar")
            flash("Você já está conectado ao Google Calendar!", "info")
            return redirect(url_for("agenda.agenda_home"))

        # Solicitar escopo de calendar incrementalmente
        agenda_logger.info(f"Solicitando escopo de calendar para {g.user_email}")

        redirect_uri = url_for("agenda.agenda_callback", _external=True)

        # Forçar HTTPS fora de debug
        is_debug = current_app.config.get("DEBUG", False)
        preferred_scheme = current_app.config.get("PREFERRED_URL_SCHEME", "https")
        if preferred_scheme == "http":
            logger.info(f"Usando HTTP na redirect_uri (dev): {redirect_uri}")
        elif not is_debug and redirect_uri.startswith("http://"):
            redirect_uri = redirect_uri.replace("http://", "https://", 1)

        # Usar autorização incremental
        return oauth.google.authorize_redirect(
            redirect_uri,
            scope=SCOPE_CALENDAR,  # Apenas calendar
            access_type="offline",
            prompt="consent",
            include_granted_scopes="true",  # AUTORIZAÇÃO INCREMENTAL
        )

    except Exception as e:
        agenda_logger.error(f"Erro ao iniciar conexão com Google Calendar: {e}", exc_info=True)
        flash("Erro ao conectar com Google Calendar.", "error")
        return redirect(url_for("agenda.agenda_home"))


@agenda_bp.route("/agenda/calendars")
@login_required
def agenda_list_calendars():
    """Lista os calendários do usuário para seleção na UI."""
    if not _google_oauth_configured():
        return jsonify({"ok": False, "error": "Google OAuth não configurado"}), 400
    token = session.get("google_token") or {}
    access_token = token.get("access_token")
    if not access_token:
        return jsonify({"ok": False, "error": "Sessão do Google ausente"}), 401
    try:
        resp = requests.get(
            "https://www.googleapis.com/calendar/v3/users/me/calendarList",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10,
        )
        if resp.status_code >= 400:
            return jsonify({"ok": False, "error": resp.text}), resp.status_code
        data = resp.json()
        items = data.get("items", [])

        calendars = [
            {
                "id": it.get("id"),
                "summary": it.get("summary"),
                "primary": bool(it.get("primary")),
                "backgroundColor": it.get("backgroundColor"),
                "foregroundColor": it.get("foregroundColor"),
            }
            for it in items
        ]
        return jsonify({"ok": True, "calendars": calendars})
    except Exception as e:
        logger.exception("Unhandled exception", exc_info=True)
        return jsonify({"ok": False, "error": str(e)}), 500


@agenda_bp.route("/agenda/callback")
@login_required
def agenda_callback():
    """
    Callback do OAuth para Google Calendar.
    Salva o token com escopos combinados (básicos + calendar).
    """
    if not _google_oauth_configured():
        flash("Integração com Google Agenda não está configurada.", "warning")
        return redirect(url_for("agenda.agenda_home"))

    try:
        token = oauth.google.authorize_access_token()

        # Salvar token no banco de dados
        from ..application.google_oauth_service import save_user_google_token

        # Preparar token para salvar
        token_to_save = {
            "access_token": token.get("access_token"),
            "refresh_token": token.get("refresh_token"),
            "token_type": token.get("token_type", "Bearer"),
            "expires_at": datetime.now(timezone.utc) + timedelta(seconds=token.get("expires_in", 3600)),
            "scope": token.get("scope", ""),
        }

        save_user_google_token(g.user_email, token_to_save)

        # Também salvar na sessão para compatibilidade
        session["google_token"] = {
            "access_token": token.get("access_token"),
            "refresh_token": token.get("refresh_token"),
            "expires_at": token.get("expires_at"),
            "token_type": token.get("token_type"),
        }
        session.permanent = True

        agenda_logger.info(f"Token do Google Calendar salvo para {g.user_email}")
        flash("Conexão com Google concluída com sucesso!", "success")

    except Exception as e:
        agenda_logger.error(f"Erro no callback OAuth Google: {e}", exc_info=True)
        flash("Falha na conexão com Google.", "error")

    dest = session.pop("oauth_next", None)
    if dest:
        return redirect(dest)
    return redirect(url_for("agenda.agenda_home"))


@agenda_bp.route("/agenda/events", methods=["POST"])
@login_required
def agenda_create_event():
    """Cria um evento no calendário principal do usuário."""
    access_token, err = _get_google_access_token()
    if err:
        return err

    payload = request.get_json(silent=True) or {}
    date_str = payload.get("date")
    if not date_str:
        return jsonify({"ok": False, "error": 'Campo "date" é obrigatório'}), 400

    calendar_id = payload.get("calendarId") or "primary"
    event_body: dict[str, Any] = {"summary": (payload.get("summary") or "Compromisso").strip()}
    if payload.get("location"):
        event_body["location"] = payload["location"]
    if payload.get("description"):
        event_body["description"] = payload["description"]

    # Coerce allDay para bool: ausente/falsy → False (exige startTime+endTime)
    dt_payload = {**payload, "allDay": bool(payload.get("allDay"))}
    dt_fields, err_msg = _build_event_datetime_fields(dt_payload)
    if err_msg:
        return jsonify({"ok": False, "error": err_msg}), 400
    event_body.update(dt_fields)

    if payload.get("recurrence") is not None:
        event_body["recurrence"] = payload["recurrence"]
    if payload.get("reminders") is not None:
        event_body["reminders"] = payload["reminders"]

    extra_params = None
    if payload.get("conference") is True or payload.get("createMeetLink") is True:
        event_body["conferenceData"] = {
            "createRequest": {"requestId": str(uuid.uuid4()), "conferenceSolutionKey": {"type": "hangoutsMeet"}}
        }
        extra_params = {"conferenceDataVersion": 1}

    return _call_google_calendar_api("POST", google_events_endpoint(calendar_id), access_token, event_body, extra_params)


@agenda_bp.route("/agenda/events/<event_id>", methods=["DELETE"])
@login_required
def agenda_delete_event(event_id):
    """Exclui um evento do calendário principal do usuário."""
    access_token, err = _get_google_access_token()
    if err:
        return err
    calendar_id = request.args.get("calendarId") or "primary"
    return _call_google_calendar_api("DELETE", f"{google_events_endpoint(calendar_id)}/{event_id}", access_token)


@agenda_bp.route("/agenda/disconnect")
@login_required
def agenda_disconnect():
    try:
        session.pop("google_token", None)
        from ..infra.google_oauth_service import revoke_google_token
        revoke_google_token(g.user_email)
        flash("Agenda do Google desconectada.", "info")
    except Exception as e:
        agenda_logger.warning(f"Falha ao desconectar agenda do Google da sessão: {e}", exc_info=True)
    return redirect(url_for("agenda.agenda_home"))


@agenda_bp.route("/agenda/events/<event_id>", methods=["PUT"])
@login_required
def agenda_update_event(event_id):
    """Atualiza um evento: título, horário, local, descrição, lembretes e recorrência."""
    access_token, err = _get_google_access_token()
    if err:
        return err

    payload = request.get_json(silent=True) or {}
    calendar_id = payload.get("calendarId") or request.args.get("calendarId") or "primary"

    dt_fields, err_msg = _build_event_datetime_fields(payload)
    if err_msg:
        return jsonify({"ok": False, "error": err_msg}), 400

    event_body: dict[str, Any] = {}
    event_body.update(dt_fields)

    for field in ("summary", "description", "location"):
        if payload.get(field) is not None:
            event_body[field] = payload[field]

    if payload.get("recurrence") is not None:
        event_body["recurrence"] = payload["recurrence"]
    if payload.get("reminders") is not None:
        event_body["reminders"] = payload["reminders"]

    return _call_google_calendar_api("PATCH", f"{google_events_endpoint(calendar_id)}/{event_id}", access_token, event_body)
