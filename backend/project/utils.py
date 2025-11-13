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


def calcular_progresso(concluidas, total):
    """Calcula o progresso percentual de tarefas concluídas.

    Args:
        concluidas: Número de tarefas concluídas
        total: Número total de tarefas

    Returns:
        int: Percentual de progresso (0-100)
    """
    if total == 0:
        return 0
    return round((concluidas / total) * 100)


def calcular_dias_decorridos(data_inicio):
    """Calcula quantos dias se passaram desde uma data.

    Args:
        data_inicio: Data de início (datetime, date ou string ISO)

    Returns:
        int: Número de dias decorridos
    """
    if not data_inicio:
        return 0

    # Converte para datetime se necessário
    if isinstance(data_inicio, str):
        data_inicio = _convert_to_date_or_datetime(data_inicio)

    # Converte date para datetime
    if isinstance(data_inicio, date) and not isinstance(data_inicio, datetime):
        data_inicio = datetime.combine(data_inicio, datetime.min.time())

    # Calcula diferença
    agora = datetime.now()
    if isinstance(data_inicio, datetime):
        # Remove timezone info para comparação
        agora_naive = agora.replace(tzinfo=None) if agora.tzinfo else agora
        inicio_naive = data_inicio.replace(tzinfo=None) if data_inicio.tzinfo else data_inicio
        delta = agora_naive - inicio_naive
        return max(0, delta.days)

    return 0


def gerar_cor_status(status):
    """Gera cor hexadecimal baseada no status.

    Args:
        status: Status da implantação

    Returns:
        str: Código de cor hexadecimal
    """
    cores = {
        'andamento': '#3498db',  # Azul
        'finalizada': '#2ecc71',  # Verde
        'pausada': '#f39c12',     # Laranja
        'parada': '#f39c12',      # Laranja
        'cancelada': '#e74c3c',   # Vermelho
        'nova': '#9b59b6',        # Roxo
        'futura': '#1abc9c',      # Turquesa
    }
    return cores.get(status.lower() if status else '', '#95a5a6')  # Cinza como padrão

# --- Funções de apoio para gestão de usuários ---
def load_profiles_list(exclude_self=True):
    """Carrega lista de perfis de usuários com contagens de implantações.

    Retorna uma lista de dicts com chaves:
    - usuario, nome, cargo, perfil_acesso
    - impl_andamento_total, impl_finalizadas
    Opcionalmente exclui o usuário atual (g.user_email) quando exclude_self=True.

    OTIMIZAÇÃO: Usa uma única query com JOIN para evitar problema N+1.
    """
    try:
        from flask import g
        from .db import query_db

        # Uma única query com JOIN e GROUP BY (resolve problema N+1)
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

        # Filtra o usuário atual se necessário
        if exclude_self:
            current_user = getattr(g, 'user_email', None)
            users = [u for u in users if u.get('usuario') != current_user]

        return users
    except Exception:
        # Fallback simples em caso de erro no DB: retorna lista vazia
        return []