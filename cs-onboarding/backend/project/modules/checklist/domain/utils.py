"""
Módulo de Utilitários do Checklist
Funções auxiliares para cache, formatação e listagens.
Princípio SOLID: Single Responsibility
"""

import logging
from datetime import UTC, date, datetime, timedelta, timezone

from ....common.context_profiles import resolve_context
from ....db import query_db

logger = logging.getLogger(__name__)

# Timezone de Brasília (UTC-3)
TZ_BRASILIA = timezone(timedelta(hours=-3))


def _invalidar_cache_progresso_local(impl_id):
    """
    Invalida o cache de progresso de uma implantação.
    Versão local para evitar importação circular.
    """
    try:
        from ....config.cache_config import cache

        if cache:
            cache_key = f"progresso_impl_{impl_id}"
            cache.delete(cache_key)
    except Exception as e:
        logger.warning(f"Erro ao invalidar cache de progresso para impl_id {impl_id}: {e}")


def _format_datetime(dt_value, only_date=False):
    """Formata datetime para string no formato brasileiro.

    Args:
        dt_value: Valor datetime ou string ISO
        only_date: Se True, retorna apenas dd/mm/yyyy

    SEMPRE converte para horário de Brasília (UTC-3) para garantir consistência.
    """
    # ESTRATÉGIA DEFINITIVA "BALA DE PRATA":
    # Se queremos APENAS data (only_date=True), ignoramos qualquer timezone ou hora.
    # Tratamos o valor como uma string de data local ou objeto data puro.
    
    if only_date:
        if not dt_value:
            return None
            
        str_val = str(dt_value)
        
        # Caso 1: String ISO ou similar (YYYY-MM-DD...)
        # Pega apenas os primeiros 10 chars (YYYY-MM-DD) e inverte para DD/MM/YYYY
        # Isso resolve datas como "2026-02-18 00:00:00" ou "2026-02-18T00:00:00Z"
        # SEM tentar converter fuso (que transformaria dia 18 00h em dia 17 21h)
        if len(str_val) >= 10:
            # Tenta encontrar padrão YYYY-MM-DD no início da string
            if str_val[4] == '-' and str_val[7] == '-':
                parts = str_val[:10].split('-')
                return f"{parts[2]}/{parts[1]}/{parts[0]}"
        
        # Caso 2: Objeto date ou datetime
        if hasattr(dt_value, 'day'):
            return dt_value.strftime("%d/%m/%Y")
            
        return str_val[:10] # Fallback bruto

    # Lógica original APENAS para quando queremos HORA (only_date=False)
    # Aqui a conversão de fuso é desejada para mostrar a hora correta no Brasil
    
    # Se já for string, tentar parsear
    if isinstance(dt_value, str):
        try:
            if "T" in dt_value or "+" in dt_value or (len(dt_value) > 6 and "-" in dt_value[-6:]):
                dt_value = datetime.fromisoformat(dt_value.replace("Z", "+00:00"))
            else:
                return dt_value
        except Exception:
            return dt_value

    # Se for datetime, converter para Brasília e formatar
    if hasattr(dt_value, "strftime"):
        # Se não tiver timezone (naive), assumir que está em UTC
        if dt_value.tzinfo is None:
            dt_value = dt_value.replace(tzinfo=UTC)
        # Converter para horário de Brasília
        dt_brasilia = dt_value.astimezone(TZ_BRASILIA)
        return dt_brasilia.strftime("%d/%m/%Y às %H:%M")

    return str(dt_value)


def listar_usuarios_cs():
    """Retorna lista simples de usuários para atribuição."""
    ctx = resolve_context()
    rows = (
        query_db(
            """
            SELECT pu.usuario, COALESCE(pu.nome, pu.usuario) as nome
            FROM perfil_usuario pu
            LEFT JOIN perfil_usuario_contexto puc ON pu.usuario = puc.usuario AND puc.contexto = %s
            WHERE COALESCE(puc.perfil_acesso, pu.perfil_acesso) IS NOT NULL
                AND COALESCE(puc.perfil_acesso, pu.perfil_acesso) != ''
            ORDER BY pu.nome ASC
            """,
            (ctx,),
        )
        or []
    )
    return rows


def plano_permite_excluir_tarefas(item_id):
    try:
        item_id = int(item_id)
    except (TypeError, ValueError) as err:
        raise ValueError("item_id deve ser um inteiro válido") from err

    try:
        item = (
            query_db(
                "SELECT implantacao_id, plano_id FROM checklist_items WHERE id = %s",
                (item_id,),
                one=True,
            )
            or {}
        )

        implantacao_id = item.get("implantacao_id")
        plano_id = item.get("plano_id")

        if implantacao_id:
            plano_info = query_db(
                """
                SELECT ps.permite_excluir_tarefas
                FROM implantacoes i
                JOIN planos_sucesso ps ON i.plano_sucesso_id = ps.id
                WHERE i.id = %s
                """,
                (implantacao_id,),
                one=True,
            )
            if plano_info:
                return bool(plano_info.get("permite_excluir_tarefas"))

        if plano_id:
            plano_info = query_db(
                """
                SELECT permite_excluir_tarefas
                FROM planos_sucesso
                WHERE id = %s
                """,
                (plano_id,),
                one=True,
            )
            if plano_info:
                return bool(plano_info.get("permite_excluir_tarefas"))

        return False
    except Exception as e:
        logger.warning(f"Erro ao verificar permissão do plano para item {item_id}: {e}")
        return False
