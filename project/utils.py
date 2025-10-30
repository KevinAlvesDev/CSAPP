from datetime import datetime, timezone, timedelta
# A importação do dateutil é necessária para lidar com fusos horários mais complexos
from dateutil import tz 
import os 

# --- CORREÇÃO: Adicionando extensões permitidas e função de validação de arquivo ---
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    """Verifica se a extensão do arquivo é permitida para upload."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
# ----------------------------------------------------------------------------------

# Define o fuso horário de Brasília (BRT/BRST)
try:
    # Tenta usar a definição IANA, que lida com Horário de Verão se necessário
    BRT = tz.gettz("America/Sao_Paulo")
except:
    # Fallback simples (GMT-3)
    BRT = timezone(timedelta(hours=-3)) 

# --- CORREÇÃO DO ERRO: Função get_now_utc() adicionada ---
def get_now_utc():
    """Retorna o datetime atual em UTC (timezone-aware)."""
    # É crucial usar o timezone.utc para garantir que o timestamp seja sempre armazenado
    # no banco de dados em UTC, seguindo o padrão correto.
    return datetime.now(timezone.utc)
# --------------------------------------------------------

def convert_utc_to_brt(dt_obj):
    """Converte um objeto datetime timezone-aware de UTC para o fuso horário BRT."""
    if dt_obj is None or not isinstance(dt_obj, datetime):
        return None
    
    # Se o objeto não for timezone-aware, assumimos que é UTC (Padrão para DB)
    if dt_obj.tzinfo is None or dt_obj.tzinfo.utcoffset(dt_obj) is None:
        dt_obj = dt_obj.replace(tzinfo=timezone.utc)
    
    # Converte para BRT
    return dt_obj.astimezone(BRT)

def format_date_br(dt_obj, include_time=False):
    """Formata um objeto datetime em string PT-BR (dd/mm/aaaa [hh:mm])."""
    if dt_obj is None:
        return 'N/A'
    
    # Lida com objetos date que não são datetime
    if not isinstance(dt_obj, datetime):
        # Para objetos date puros, apenas formata a data
        try:
            return dt_obj.strftime('%d/%m/%Y')
        except:
             return 'N/A'


    dt_brt = convert_utc_to_brt(dt_obj)
    
    if include_time:
        return dt_brt.strftime('%d/%m/%Y %H:%M')
    else:
        return dt_brt.strftime('%d/%m/%Y')

def format_date_iso_for_json(dt_obj, only_date=False):
    """Formata um objeto datetime ou date para string ISO 8601 (para uso em JSON/data-* HTML)."""
    if dt_obj is None:
        return ''
    
    # Se for um objeto date (não datetime)
    if not isinstance(dt_obj, datetime):
        try:
            # Retorna a string de data (YYYY-MM-DD)
            return dt_obj.isoformat()
        except:
            return ''
            
    dt_brt = convert_utc_to_brt(dt_obj)
    
    if only_date:
        return dt_brt.strftime('%Y-%m-%d')
    else:
        # Retorna o formato completo ISO 8601 com timezone
        return dt_brt.isoformat()
