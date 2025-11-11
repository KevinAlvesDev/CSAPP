from datetime import datetime, date

def _convert_to_date_or_datetime(dt_obj):
    """Tenta converter uma string ISO para objeto date ou datetime."""
    if not dt_obj or not isinstance(dt_obj, str):
        return dt_obj
    original_str = dt_obj
    try:
        # Tenta formato com tempo
        if ' ' in dt_obj or 'T' in dt_obj:
             dt_obj = dt_obj.replace('Z', '').split('+')[0].split('.')[0]
             for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%dT%H:%M:%S'):
                try:
                    return datetime.strptime(dt_obj, fmt)
                except ValueError:
                    continue
             # Fallback se a hora falhar, tenta só a data
             return datetime.strptime(original_str.split()[0], '%Y-%m-%d').date()
        # Tenta formato só de data
        return datetime.strptime(dt_obj, '%Y-%m-%d').date()
    except Exception:
        return original_str # Retorna a string original se falhar

def format_date_br(dt_obj, include_time=False):
    """Formata um objeto date/datetime ou string ISO para o padrão BR."""
    if not dt_obj:
        return 'N/A'
    
    dt_obj = _convert_to_date_or_datetime(dt_obj)
    
    if not isinstance(dt_obj, (datetime, date)):
        return 'Data Inválida'
        
    output_fmt = '%d/%m/%Y %H:%M:%S' if include_time and isinstance(dt_obj, datetime) else '%d/%m/%Y'
    try:
        return dt_obj.strftime(output_fmt)
    except ValueError:
        return 'Data Inválida'

def format_date_iso_for_json(dt_obj, only_date=False):
    """Formata um objeto date/datetime para ISO, para JSON ou campos de formulário."""
    if not dt_obj:
        return None
        
    dt_obj = _convert_to_date_or_datetime(dt_obj)

    if not isinstance(dt_obj, (datetime, date)):
        return None

    if only_date:
        output_fmt = '%Y-%m-%d'
    else:
        # Garante que é um datetime para o formato completo
        if isinstance(dt_obj, date) and not isinstance(dt_obj, datetime):
            dt_obj = datetime.combine(dt_obj, datetime.min.time())
        output_fmt = '%Y-%m-%d %H:%M:%S'
        
    try:
        return dt_obj.strftime(output_fmt)
    except ValueError:
        return None

def allowed_file(filename):
    """Verifica se a extensão do arquivo é permitida."""
    from .constants import ALLOWED_EXTENSIONS
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- Funções de apoio para gestão de usuários ---
def load_profiles_list(exclude_self=True):
    """Carrega lista de perfis de usuários com contagens de implantações.

    Retorna uma lista de dicts com chaves:
    - usuario, nome, cargo, perfil_acesso
    - impl_andamento_total, impl_finalizadas
    Opcionalmente exclui o usuário atual (g.user_email) quando exclude_self=True.
    """
    try:
        from flask import g
        from .db import query_db

        users = query_db(
            "SELECT usuario, nome, cargo, perfil_acesso FROM perfil_usuario ORDER BY usuario",
            (), one=False
        ) or []

        enriched = []
        for u in users:
            email = u.get('usuario')
            counts = query_db(
                (
                    "SELECT "
                    "SUM(CASE WHEN status = 'andamento' THEN 1 ELSE 0 END) AS impl_andamento_total, "
                    "SUM(CASE WHEN status = 'finalizada' THEN 1 ELSE 0 END) AS impl_finalizadas "
                    "FROM implantacoes WHERE usuario_cs = %s"
                ),
                (email,), one=True
            ) or {}

            u['impl_andamento_total'] = counts.get('impl_andamento_total') or 0
            u['impl_finalizadas'] = counts.get('impl_finalizadas') or 0

            if not (exclude_self and getattr(g, 'user_email', None) == email):
                enriched.append(u)

        return enriched
    except Exception:
        # Fallback simples em caso de erro no DB: retorna lista vazia
        return []