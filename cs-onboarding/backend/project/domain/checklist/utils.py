"""
Módulo de Utilitários do Checklist
Funções auxiliares para cache, formatação e listagens.
Princípio SOLID: Single Responsibility
"""
import logging
from datetime import datetime, timezone, timedelta

from flask import current_app

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
            cache_key = f'progresso_impl_{impl_id}'
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
            # Tentar parsear ISO format
            if 'T' in dt_value or '+' in dt_value or (len(dt_value) > 6 and '-' in dt_value[-6:]):
                dt_value = datetime.fromisoformat(dt_value.replace('Z', '+00:00'))
            else:
                return dt_value  # Retornar como está se não conseguir parsear
        except:
            return dt_value
    
    # Se for datetime, converter para Brasília e formatar
    if hasattr(dt_value, 'strftime'):
        # Se não tiver timezone (naive), assumir que está em UTC
        if dt_value.tzinfo is None:
            dt_value = dt_value.replace(tzinfo=timezone.utc)
        # Converter para horário de Brasília
        dt_brasilia = dt_value.astimezone(TZ_BRASILIA)
        return dt_brasilia.strftime('%d/%m/%Y às %H:%M')
    
    return str(dt_value)


def listar_usuarios_cs():
    """Retorna lista simples de usuários para atribuição."""
    rows = query_db("SELECT usuario, COALESCE(nome, usuario) as nome FROM perfil_usuario ORDER BY nome ASC") or []
    return rows

