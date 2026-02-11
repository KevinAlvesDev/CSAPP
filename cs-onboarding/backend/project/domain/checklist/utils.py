"""
Módulo de Utilitários do Checklist
Funções auxiliares para cache, formatação e listagens.
Princípio SOLID: Single Responsibility
"""

import logging
from datetime import UTC, datetime, timedelta, timezone

from ...db import query_db

logger = logging.getLogger(__name__)

# Timezone de Brasília (UTC-3)
TZ_BRASILIA = timezone(timedelta(hours=-3))


def _invalidar_cache_progresso_local(impl_id):
    """
    Invalida o cache de progresso de uma implantação.
    Versão local para evitar importação circular.
    """
    try:
        from ...config.cache_config import cache

        if cache:
            cache_key = f"progresso_impl_{impl_id}"
            cache.delete(cache_key)
    except Exception as e:
        logger.warning(f"Erro ao invalidar cache de progresso para impl_id {impl_id}: {e}")


def _format_datetime(dt_value):
    """Formata datetime para string no formato brasileiro: dd/mm/yyyy às HH:MM

    SEMPRE converte para horário de Brasília (UTC-3) para garantir consistência.
    """
    if not dt_value:
        return None

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
    rows = query_db("SELECT usuario, COALESCE(nome, usuario) as nome FROM perfil_usuario ORDER BY nome ASC") or []
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
