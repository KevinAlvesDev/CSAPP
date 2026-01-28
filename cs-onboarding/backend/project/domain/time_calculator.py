"""
Módulo para calcular corretamente os tempos de implantação considerando mudanças de status.
"""

from datetime import date, datetime

from ..db import query_db


def parse_datetime(dt_obj):
    """Converte vários formatos de data/datetime para datetime naive."""
    if not dt_obj:
        return None

    if isinstance(dt_obj, datetime):
        return dt_obj.replace(tzinfo=None) if dt_obj.tzinfo else dt_obj
    elif isinstance(dt_obj, date) and not isinstance(dt_obj, datetime):
        return datetime.combine(dt_obj, datetime.min.time())
    elif isinstance(dt_obj, str):
        try:
            return datetime.fromisoformat(dt_obj.replace("Z", "+00:00")).replace(tzinfo=None)
        except ValueError:
            try:
                if "." in dt_obj:
                    return datetime.strptime(dt_obj, "%Y-%m-%d %H:%M:%S.%f")
                else:
                    return datetime.strptime(dt_obj, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                try:
                    return datetime.strptime(dt_obj, "%Y-%m-%d")
                except ValueError:
                    return None
    return None


def get_status_history(impl_id):
    """
    Obtém o histórico de mudanças de status da implantação a partir do timeline_log.
    Retorna lista de tuplas (data, status_anterior, status_novo, detalhes).
    """
    logs = query_db(
        """
        SELECT data_criacao, detalhes
        FROM timeline_log
        WHERE implantacao_id = %s
        AND tipo_evento = 'status_alterado'
        ORDER BY data_criacao ASC
        """,
        (impl_id,),
    )

    history = []
    import re

    for log in logs or []:
        dt = parse_datetime(log.get("data_criacao"))
        detalhes = log.get("detalhes", "").lower()

        if dt:
            # Parada (pode ser retroativa)
            if "parada" in detalhes or "retroativamente" in detalhes:
                # Procurar data no texto (formato: YYYY-MM-DD)
                date_match = re.search(r"(\d{4}-\d{2}-\d{2})", log.get("detalhes", ""))
                if date_match:
                    parada_date = parse_datetime(date_match.group(1))
                    if parada_date:
                        history.append((parada_date, "andamento", "parada", log.get("detalhes", "")))
                else:
                    # Se não tem data no texto, usar a data do log
                    history.append((dt, "andamento", "parada", log.get("detalhes", "")))
            # Retomada
            elif "retomada" in detalhes or "reaberta" in detalhes:
                history.append((dt, "parada", "andamento", log.get("detalhes", "")))
            # Finalizada
            elif "finalizada" in detalhes:
                history.append((dt, "andamento", "finalizada", log.get("detalhes", "")))

    return history


def calculate_total_days_in_status(impl_id, target_status="andamento"):
    """
    Calcula o total de dias que a implantação passou em um status específico,
    considerando todos os períodos (não apenas o atual).

    Args:
        impl_id: ID da implantação
        target_status: 'andamento' ou 'parada'

    Returns:
        Total de dias no status especificado
    """
    impl = query_db(
        "SELECT data_inicio_efetivo, data_finalizacao, status FROM implantacoes WHERE id = %s", (impl_id,), one=True
    )

    if not impl:
        return 0

    agora = datetime.now()
    status_history = get_status_history(impl_id)
    current_status = impl.get("status")
    inicio_efetivo = parse_datetime(impl.get("data_inicio_efetivo"))

    if not inicio_efetivo:
        return 0

    # Se não há histórico, usar cálculo simples baseado no status atual
    if not status_history:
        if target_status == "andamento":
            if current_status == "andamento":
                delta = agora - inicio_efetivo
                return max(0, delta.days)
            elif current_status == "parada":
                # Estava em andamento até entrar em parada
                parada_inicio = parse_datetime(impl.get("data_finalizacao"))
                if parada_inicio and parada_inicio > inicio_efetivo:
                    delta = parada_inicio - inicio_efetivo
                    return max(0, delta.days)
            return 0
        elif target_status == "parada":
            if current_status == "parada":
                parada_inicio = parse_datetime(impl.get("data_finalizacao"))
                if parada_inicio:
                    delta = agora - parada_inicio
                    return max(0, delta.days)
            return 0

    # Calcular períodos usando histórico
    total_days = 0
    status_history.sort(key=lambda x: x[0])

    periods = []
    current_start = inicio_efetivo
    status_before_history = "andamento"  # Assumir que começou em andamento

    # Processar histórico
    for hist_date, _old_status, new_status, _ in status_history:
        # Se o status antes desta mudança era o alvo, adicionar período
        if status_before_history == target_status:
            if hist_date > current_start:
                periods.append((current_start, hist_date))
        status_before_history = new_status
        current_start = hist_date

    # Adicionar período atual se estiver no status alvo
    if current_status == target_status:
        if target_status == "parada":
            # Se tem histórico, o período começa na última mudança (current_start)
            # Se não tem, usa data_finalizacao como fallback
            parada_inicio = current_start if status_history else parse_datetime(impl.get("data_finalizacao"))
            
            if parada_inicio:
                if agora > parada_inicio:
                    periods.append((parada_inicio, agora))
        elif target_status == "andamento":
            if current_status == "andamento":
                # Se está em andamento, o período atual começa na última mudança ou no início efetivo
                start_date = current_start if status_history else inicio_efetivo
                if agora > start_date:
                    periods.append((start_date, agora))

    # Somar todos os períodos
    for start, end in periods:
        delta = end - start
        days = delta.days
        if days > 0:
            total_days += days

    return total_days


def calculate_days_passed(impl_id):
    """
    Calcula dias passados em andamento (excluindo períodos de parada).
    """
    return calculate_total_days_in_status(impl_id, "andamento")


def calculate_days_parada(impl_id):
    """
    Calcula total de dias parados (acumulando todos os períodos de parada).
    """
    return calculate_total_days_in_status(impl_id, "parada")
