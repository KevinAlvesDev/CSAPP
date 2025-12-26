"""
Módulo de Utilitários do Checklist
Funções auxiliares para cache, formatação e listagens.
Princípio SOLID: Single Responsibility
"""
import logging

from flask import current_app

from ...db import query_db

logger = logging.getLogger(__name__)


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
    """Formata datetime para string ISO, compatível com PostgreSQL e SQLite."""
    if not dt_value:
        return None
    if isinstance(dt_value, str):
        return dt_value
    if hasattr(dt_value, 'isoformat'):
        return dt_value.isoformat()
    return str(dt_value)


def listar_usuarios_cs():
    """Retorna lista simples de usuários para atribuição."""
    rows = query_db("SELECT usuario, COALESCE(nome, usuario) as nome FROM perfil_usuario ORDER BY nome ASC") or []
    return rows
