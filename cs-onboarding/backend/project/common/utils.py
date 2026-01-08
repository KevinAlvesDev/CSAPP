from datetime import date, datetime, timezone, timedelta

# Timezone de Brasília (UTC-3)
TZ_BRASILIA = timezone(timedelta(hours=-3))


def _convert_to_date_or_datetime(dt_obj):
    if not dt_obj or not isinstance(dt_obj, str):
        return dt_obj
    original_str = dt_obj
    try:
        if ' ' in dt_obj or 'T' in dt_obj:
            dt_obj = dt_obj.replace('Z', '').split('+')[0].split('.')[0]
            for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%dT%H:%M:%S'):
                try:
                    return datetime.strptime(dt_obj, fmt)
                except ValueError:
                    continue
            return datetime.strptime(original_str.split()[0], '%Y-%m-%d').date()
        return datetime.strptime(dt_obj, '%Y-%m-%d').date()
    except Exception:
        return original_str


def format_date_br(dt_obj, include_time=False):
    """Formata data para o formato brasileiro, convertendo para horário de Brasília se necessário."""
    if not dt_obj:
        return 'N/A'
    dt_obj = _convert_to_date_or_datetime(dt_obj)
    if not isinstance(dt_obj, (datetime, date)):
        return 'Data Inválida'
    
    # Se for datetime e incluir hora, converter para horário de Brasília
    if include_time and isinstance(dt_obj, datetime):
        # Se não tiver timezone (naive), assumir que está em UTC
        if dt_obj.tzinfo is None:
            dt_obj = dt_obj.replace(tzinfo=timezone.utc)
        # Converter para horário de Brasília
        dt_obj = dt_obj.astimezone(TZ_BRASILIA)
        output_fmt = '%d/%m/%Y às %H:%M'
    else:
        output_fmt = '%d/%m/%Y'
    
    try:
        return dt_obj.strftime(output_fmt)
    except ValueError:
        return 'Data Inválida'


def format_date_iso_for_json(dt_obj, only_date=False):
    if not dt_obj:
        return None

    if isinstance(dt_obj, str):
        if len(dt_obj) >= 10 and dt_obj[4] == '-' and dt_obj[7] == '-':
            if only_date:
                return dt_obj[:10]
            return dt_obj
        try:
            dt_obj = _convert_to_date_or_datetime(dt_obj)
        except Exception:
            return None

    dt_obj = _convert_to_date_or_datetime(dt_obj)
    if not isinstance(dt_obj, (datetime, date)):
        return None
    if only_date:
        output_fmt = '%Y-%m-%d'
    else:
        if isinstance(dt_obj, date) and not isinstance(dt_obj, datetime):
            dt_obj = datetime.combine(dt_obj, datetime.min.time())
        output_fmt = '%Y-%m-%d %H:%M:%S'
    try:
        return dt_obj.strftime(output_fmt)
    except ValueError:
        return None


def allowed_file(filename):
    from ..constants import ALLOWED_EXTENSIONS
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def calcular_progresso(concluidas, total):
    if total == 0:
        return 0
    return round((concluidas / total) * 100)


def calcular_dias_decorridos(data_inicio):
    if not data_inicio:
        return 0
    if isinstance(data_inicio, str):
        data_inicio = _convert_to_date_or_datetime(data_inicio)
    if isinstance(data_inicio, date) and not isinstance(data_inicio, datetime):
        data_inicio = datetime.combine(data_inicio, datetime.min.time())
    agora = datetime.now()
    if isinstance(data_inicio, datetime):
        agora_naive = agora.replace(tzinfo=None) if agora.tzinfo else agora
        inicio_naive = data_inicio.replace(tzinfo=None) if data_inicio.tzinfo else data_inicio
        delta = agora_naive - inicio_naive
        return max(0, delta.days)
    return 0


def gerar_cor_status(status):
    cores = {
        'andamento': '#3498db',
        'finalizada': '#2ecc71',
        'pausada': '#f39c12',
        'parada': '#f39c12',
        'cancelada': '#e74c3c',
        'nova': '#9b59b6',
        'futura': '#1abc9c',
    }
    return cores.get(status.lower() if status else '', '#95a5a6')


def load_profiles_list(exclude_self=True):
    try:
        from flask import g

        from ..db import query_db
        users = query_db(
            """
            SELECT
                p.usuario,
                p.nome,
                p.cargo,
                p.perfil_acesso,
                COALESCE(SUM(CASE WHEN i.status = 'andamento' THEN 1 ELSE 0 END), 0) AS impl_andamento_total,
                COALESCE(SUM(CASE WHEN i.status = 'finalizada' THEN 1 ELSE 0 END), 0) AS impl_finalizadas
            FROM perfil_usuario p
            LEFT JOIN implantacoes i ON p.usuario = i.usuario_cs
            GROUP BY p.usuario, p.nome, p.cargo, p.perfil_acesso
            ORDER BY p.usuario
            """,
            (), one=False
        ) or []
        if exclude_self:
            current_user = getattr(g, 'user_email', None)
            users = [u for u in users if u.get('usuario') != current_user]
        return users
    except Exception:
        return []
