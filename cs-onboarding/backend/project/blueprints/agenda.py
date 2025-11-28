from flask import Blueprint, render_template, g, session, redirect, url_for, current_app, request, flash, jsonify
from urllib.parse import urlencode
from ..blueprints.auth import login_required
from ..core.extensions import oauth
from ..config.logging_config import get_logger
import requests
from datetime import datetime, date, timedelta
import uuid

agenda_bp = Blueprint('agenda', __name__)
agenda_logger = get_logger('agenda')

def google_events_endpoint(calendar_id: str = 'primary'):
    return f'https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events'


def _google_oauth_configured():
    return all([
        current_app.config.get('GOOGLE_CLIENT_ID'),
        current_app.config.get('GOOGLE_CLIENT_SECRET'),
        current_app.config.get('GOOGLE_REDIRECT_URI'),
    ])


@agenda_bp.route('/agenda')
@login_required
def agenda_home():

    try:
        agenda_logger.debug(f"Google OAuth configurado: {_google_oauth_configured()}")
    except Exception:
        pass
    if not _google_oauth_configured():
        flash('Integração com Google Agenda não está configurada. Defina GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET e GOOGLE_REDIRECT_URI no .env.', 'warning')
        return render_template('agenda.html', events=[], google_connected=False)

    token = session.get('google_token')
    try:
        agenda_logger.debug(f"Token na sessão: {bool(token)}; chaves={list(token.keys()) if token else None}")
    except Exception:
        pass
    if not token:
        return render_template('agenda.html', events=[], google_connected=False)

    access_token = token.get('access_token')
    try:
        agenda_logger.debug(f"Access token presente: {bool(access_token)}")
    except Exception:
        pass
    if not access_token:
        return render_template('agenda.html', events=[], google_connected=False)

    view = request.args.get('view', 'semana')
    start_qs = request.args.get('start')
    calendar_id = request.args.get('cal', 'primary')
    query_text = request.args.get('q')
    base_day = None
    try:
        base_day = date.fromisoformat(start_qs) if start_qs else date.today()
    except Exception:
        base_day = date.today()

    weekday = base_day.weekday()                  
    days_to_subtract = (weekday + 1) % 7
    week_start = base_day - timedelta(days=days_to_subtract)
    week_end = week_start + timedelta(days=6)

    time_min = f"{week_start.isoformat()}T00:00:00Z"
    time_max = f"{week_end.isoformat()}T23:59:59Z"

    params = {
        'singleEvents': 'true',
        'orderBy': 'startTime',
        'maxResults': 50,
        'timeMin': time_min,
        'timeMax': time_max,
    }
    if query_text:
        params['q'] = query_text
    params = {k: v for k, v in params.items() if v is not None}

    try:
        agenda_logger.info(f"Buscando eventos no Google Calendar para {g.user_email}")
        resp = requests.get(
            google_events_endpoint(calendar_id),
            headers={'Authorization': f'Bearer {access_token}'},
            params=params,
            timeout=10,
        )
        agenda_logger.debug(f"Resposta Google Calendar status={resp.status_code}")
        if resp.status_code == 401:

            flash('Sessão do Google expirou. Conecte novamente a Agenda.', 'warning')
            return render_template('agenda.html', events=[], google_connected=False)
        resp.raise_for_status()
        data = resp.json()
        events = data.get('items', [])
        try:
            agenda_logger.info(f"Eventos carregados: {len(events)} para {g.user_email}")
        except Exception:
            pass
        week_days = [(week_start + timedelta(days=i)).isoformat() for i in range(7)]
        return render_template(
            'agenda.html',
            events=events,
            google_connected=True,
            view=view,
            week_start=week_start.isoformat(),
            week_end=week_end.isoformat(),
            week_days=week_days,
            current_calendar=calendar_id,
            search_query=query_text or '',
        )
    except Exception as e:
        agenda_logger.error(f"Erro ao buscar eventos do Google Calendar para {g.user_email}: {e}", exc_info=True)
        try:
            agenda_logger.debug(f"Corpo erro/resposta: {getattr(resp, 'text', None)}")
        except Exception:
            pass
        flash('Falha ao carregar eventos da Agenda do Google.', 'error')
        return render_template('agenda.html', events=[], google_connected=False, view=view)


@agenda_bp.route('/agenda/connect')
@login_required
def agenda_connect():

    if not _google_oauth_configured():
        flash('Integração com Google Agenda não está configurada.', 'warning')
        return redirect(url_for('agenda.agenda_home'))

    redirect_uri = current_app.config['GOOGLE_REDIRECT_URI']
    return oauth.google.authorize_redirect(redirect_uri)




@agenda_bp.route('/agenda/calendars')
@login_required
def agenda_list_calendars():
    """Lista os calendários do usuário para seleção na UI."""
    if not _google_oauth_configured():
        return jsonify({'ok': False, 'error': 'Google OAuth não configurado'}), 400
    token = session.get('google_token') or {}
    access_token = token.get('access_token')
    if not access_token:
        return jsonify({'ok': False, 'error': 'Sessão do Google ausente'}), 401
    try:
        resp = requests.get(
            'https://www.googleapis.com/calendar/v3/users/me/calendarList',
            headers={'Authorization': f'Bearer {access_token}'},
            timeout=10,
        )
        if resp.status_code >= 400:
            return jsonify({'ok': False, 'error': resp.text}), resp.status_code
        data = resp.json()
        items = data.get('items', [])

        calendars = [
            {
                'id': it.get('id'),
                'summary': it.get('summary'),
                'primary': bool(it.get('primary')),
                'backgroundColor': it.get('backgroundColor'),
                'foregroundColor': it.get('foregroundColor'),
            }
            for it in items
        ]
        return jsonify({'ok': True, 'calendars': calendars})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@agenda_bp.route('/agenda/callback')
def agenda_callback():
    if not _google_oauth_configured():
        flash('Integração com Google Agenda não está configurada.', 'warning')
        return redirect(url_for('agenda.agenda_home'))

    try:
        token = oauth.google.authorize_access_token()
        session['google_token'] = {
            'access_token': token.get('access_token'),
            'refresh_token': token.get('refresh_token'),
            'expires_at': token.get('expires_at'),
            'token_type': token.get('token_type'),
        }
        session.permanent = True
        flash('Conexão com Google concluída com sucesso!', 'success')
    except Exception as e:
        agenda_logger.error(f"Erro no callback OAuth Google: {e}", exc_info=True)
        flash('Falha na conexão com Google.', 'error')

    dest = session.pop('oauth_next', None)
    if dest:
        return redirect(dest)
    return redirect(url_for('agenda.agenda_home'))


@agenda_bp.route('/agenda/events', methods=['POST'])
@login_required
def agenda_create_event():
    """Cria um evento no calendário principal do usuário."""
    if not _google_oauth_configured():
        return jsonify({'ok': False, 'error': 'Google OAuth não configurado'}), 400

    token = session.get('google_token') or {}
    access_token = token.get('access_token')
    if not access_token:
        return jsonify({'ok': False, 'error': 'Sessão do Google ausente'}), 401

    payload = request.get_json(silent=True) or {}
    summary = (payload.get('summary') or 'Compromisso').strip()
    date_str = payload.get('date')              
    start_time = payload.get('startTime')         
    end_time = payload.get('endTime')             
    time_zone = payload.get('timeZone') or 'UTC'
    location = payload.get('location')
    all_day = bool(payload.get('allDay'))
    description = payload.get('description')
    calendar_id = payload.get('calendarId') or 'primary'

    if not date_str:
        return jsonify({'ok': False, 'error': 'Campo "date" é obrigatório'}), 400

    event_body = {'summary': summary}
    if location:
        event_body['location'] = location
    if description:
        event_body['description'] = description

    if all_day:

        event_body['start'] = { 'date': date_str }
        event_body['end'] = { 'date': date_str }
    else:
        if not (start_time and end_time):
            return jsonify({'ok': False, 'error': 'startTime e endTime são obrigatórios'}), 400
        start_dt = f"{date_str}T{start_time}:00"
        end_dt = f"{date_str}T{end_time}:00"
        event_body['start'] = { 'dateTime': start_dt, 'timeZone': time_zone }
        event_body['end']   = { 'dateTime': end_dt,   'timeZone': time_zone }

    recurrence = payload.get('recurrence')
    reminders = payload.get('reminders')

    if recurrence is not None:
        event_body['recurrence'] = recurrence
    if reminders is not None:
        event_body['reminders'] = reminders

    conference = bool((payload.get('conference') is True) or (payload.get('createMeetLink') is True))
    extra_params = None
    if conference:
        event_body['conferenceData'] = {
            'createRequest': {
                'requestId': str(uuid.uuid4()),
                'conferenceSolutionKey': { 'type': 'hangoutsMeet' }
            }
        }

        extra_params = { 'conferenceDataVersion': 1 }

    try:
        resp = requests.post(
            google_events_endpoint(calendar_id),
            headers={'Authorization': f'Bearer {access_token}', 'Content-Type': 'application/json'},
            json=event_body,
            params=extra_params,
            timeout=10,
        )
        if resp.status_code == 401:
            return jsonify({'ok': False, 'error': 'Token expirado. Refaça a conexão com o Google.'}), 401
        if resp.status_code >= 400:
            return jsonify({'ok': False, 'error': resp.text}), resp.status_code
        return jsonify({'ok': True, 'event': resp.json()})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@agenda_bp.route('/agenda/events/<event_id>', methods=['DELETE'])
@login_required
def agenda_delete_event(event_id):
    """Exclui um evento do calendário principal do usuário."""
    if not _google_oauth_configured():
        return jsonify({'ok': False, 'error': 'Google OAuth não configurado'}), 400

    token = session.get('google_token') or {}
    access_token = token.get('access_token')
    if not access_token:
        return jsonify({'ok': False, 'error': 'Sessão do Google ausente'}), 401

    calendar_id = request.args.get('calendarId') or 'primary'
    try:
        resp = requests.delete(
            f"{google_events_endpoint(calendar_id)}/{event_id}",
            headers={'Authorization': f'Bearer {access_token}'},
            timeout=10,
        )
        if resp.status_code == 401:
            return jsonify({'ok': False, 'error': 'Token expirado. Refaça a conexão com o Google.'}), 401
        if resp.status_code >= 400:
            return jsonify({'ok': False, 'error': resp.text}), resp.status_code
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@agenda_bp.route('/agenda/disconnect')
@login_required
def agenda_disconnect():
    try:
        session.pop('google_token', None)
        flash('Agenda do Google desconectada.', 'info')
    except Exception:
        pass
    return redirect(url_for('agenda.agenda_home'))
@agenda_bp.route('/agenda/events/<event_id>', methods=['PUT'])
@login_required
def agenda_update_event(event_id):
    """Atualiza um evento: título, horário, local, descrição, lembretes e recorrência."""
    if not _google_oauth_configured():
        return jsonify({'ok': False, 'error': 'Google OAuth não configurado'}), 400

    token = session.get('google_token') or {}
    access_token = token.get('access_token')
    if not access_token:
        return jsonify({'ok': False, 'error': 'Sessão do Google ausente'}), 401

    payload = request.get_json(silent=True) or {}
    calendar_id = payload.get('calendarId') or request.args.get('calendarId') or 'primary'

    summary = payload.get('summary')
    description = payload.get('description')
    location = payload.get('location')
    date_str = payload.get('date')
    start_time = payload.get('startTime')
    end_time = payload.get('endTime')
    time_zone = payload.get('timeZone') or 'UTC'
    all_day = payload.get('allDay')
    recurrence = payload.get('recurrence')
    reminders = payload.get('reminders')

    event_body = {}
    if summary is not None:
        event_body['summary'] = summary
    if description is not None:
        event_body['description'] = description
    if location is not None:
        event_body['location'] = location

    if all_day is True:
        if not date_str:
            return jsonify({'ok': False, 'error': 'date é obrigatório para dia inteiro'}), 400
        event_body['start'] = { 'date': date_str }
        event_body['end'] = { 'date': date_str }
    elif all_day is False or (start_time and end_time):
        if not (date_str and start_time and end_time):
            return jsonify({'ok': False, 'error': 'date, startTime e endTime são obrigatórios'}), 400
        start_dt = f"{date_str}T{start_time}:00"
        end_dt = f"{date_str}T{end_time}:00"
        event_body['start'] = { 'dateTime': start_dt, 'timeZone': time_zone }
        event_body['end']   = { 'dateTime': end_dt,   'timeZone': time_zone }

    if recurrence is not None:
        event_body['recurrence'] = recurrence
    if reminders is not None:
        event_body['reminders'] = reminders

    try:
        resp = requests.patch(
            f"{google_events_endpoint(calendar_id)}/{event_id}",
            headers={'Authorization': f'Bearer {access_token}', 'Content-Type': 'application/json'},
            json=event_body,
            timeout=10,
        )
        if resp.status_code == 401:
            return jsonify({'ok': False, 'error': 'Token expirado. Refaça a conexão com o Google.'}), 401
        if resp.status_code >= 400:
            return jsonify({'ok': False, 'error': resp.text}), resp.status_code
        return jsonify({'ok': True, 'event': resp.json()})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500
