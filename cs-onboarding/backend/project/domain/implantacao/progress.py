"""
Módulo de Progresso de Implantação
Responsável pelo cálculo de progresso e gerenciamento de cache.
Princípio SOLID: Single Responsibility
"""

from functools import wraps

from flask import current_app

from ...db import query_db

try:
    from ...config.cache_config import cache
except ImportError:
    cache = None


def cached_progress(ttl=30):
    """
    Decorator para cachear resultado de cálculo de progresso.
    TTL padrão: 30 segundos

    Args:
        ttl: Time to live em segundos (padrão: 30)

    Returns:
        Decorator function
    """

    def decorator(func):
        @wraps(func)
        def wrapper(impl_id, *args, **kwargs):
            if not cache:
                return func(impl_id, *args, **kwargs)

            cache_key = f"progresso_impl_{impl_id}"

            try:
                cached_result = cache.get(cache_key)

                if cached_result is not None:
                    return cached_result

                result = func(impl_id, *args, **kwargs)
                cache.set(cache_key, result, timeout=ttl)

                return result
            except Exception as e:
                current_app.logger.warning(f"Erro no cache de progresso para impl_id {impl_id}: {e}")
                return func(impl_id, *args, **kwargs)

        return wrapper

    return decorator


def invalidar_cache_progresso(impl_id):
    """
    Invalida o cache de progresso de uma implantação específica.
    Deve ser chamado sempre que o status de uma tarefa mudar.

    Args:
        impl_id: ID da implantação
    """
    if not cache:
        return

    try:
        cache_key = f"progresso_impl_{impl_id}"
        cache.delete(cache_key)
    except Exception as e:
        if current_app:
            current_app.logger.warning(f"Erro ao invalidar cache de progresso para impl_id {impl_id}: {e}")


def _get_progress_optimized(impl_id):
    """
    Versão otimizada que usa uma única query com checklist_items.
    Agora usa checklist_items (estrutura consolidada).

    Lógica de cálculo do progresso:
    - Conta apenas itens "folha" (que não têm filhos) para evitar dupla contagem
    - Itens folha são: subtarefas OU tarefas sem subtarefas
    - Se tipo_item não estiver preenchido, usa lógica baseada em parent_id
    """
    try:
        items_exist = query_db("SELECT id FROM checklist_items WHERE implantacao_id = %s LIMIT 1", (impl_id,), one=True)
    except Exception:
        items_exist = None

    if not items_exist:
        return 0, 0, 0

    is_sqlite = current_app.config.get("USE_SQLITE_LOCALLY", False)

    try:
        if is_sqlite:
            query = """
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN completed = 1 THEN 1 ELSE 0 END) as done
                FROM checklist_items ci
                WHERE ci.implantacao_id = ?
                AND NOT EXISTS (
                    SELECT 1 FROM checklist_items filho 
                    WHERE filho.parent_id = ci.id
                    AND filho.implantacao_id = ?
                )
            """
            result = query_db(query, (impl_id, impl_id), one=True) or {}

            total = int(result.get("total", 0) or 0)
            done = int(result.get("done", 0) or 0)
        else:
            query = """
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN completed THEN 1 ELSE 0 END) as done
                FROM checklist_items ci
                WHERE ci.implantacao_id = %s
                AND NOT EXISTS (
                    SELECT 1 FROM checklist_items filho 
                    WHERE filho.parent_id = ci.id
                    AND filho.implantacao_id = %s
                )
            """
            result = query_db(query, (impl_id, impl_id), one=True) or {}

            total = int(result.get("total", 0) or 0)
            done = int(result.get("done", 0) or 0)

        if total == 0:
            any_items = query_db(
                "SELECT COUNT(*) as count FROM checklist_items WHERE implantacao_id = %s", (impl_id,), one=True
            )
            if any_items and int(any_items.get("count", 0) or 0) > 0:
                if is_sqlite:
                    fallback_query = """
                        SELECT
                            COUNT(*) as total,
                            SUM(CASE WHEN completed = 1 THEN 1 ELSE 0 END) as done
                        FROM checklist_items
                        WHERE implantacao_id = ?
                    """
                    fallback_result = query_db(fallback_query, (impl_id,), one=True) or {}
                else:
                    fallback_query = """
                        SELECT
                            COUNT(*) as total,
                            SUM(CASE WHEN completed THEN 1 ELSE 0 END) as done
                        FROM checklist_items
                        WHERE implantacao_id = %s
                    """
                    fallback_result = query_db(fallback_query, (impl_id,), one=True) or {}

                total = int(fallback_result.get("total", 0) or 0)
                done = int(fallback_result.get("done", 0) or 0)

        return int(round((done / total) * 100)) if total > 0 else 100, total, done

    except Exception as e:
        current_app.logger.error(f"Erro ao calcular progresso otimizado para impl_id {impl_id}: {e}", exc_info=True)
        return _get_progress_legacy(impl_id)


def _get_progress_legacy(impl_id):
    """
    Versão legada usando checklist_items - mantida como fallback.
    Agora usa checklist_items (estrutura consolidada).
    """
    try:
        items_exist = query_db("SELECT id FROM checklist_items WHERE implantacao_id = %s LIMIT 1", (impl_id,), one=True)
    except Exception:
        items_exist = None

    if items_exist:
        sub = (
            query_db(
                """
            SELECT COUNT(*) as total, SUM(CASE WHEN completed THEN 1 ELSE 0 END) as done
            FROM checklist_items
            WHERE implantacao_id = %s AND tipo_item = 'subtarefa'
            """,
                (impl_id,),
                one=True,
            )
            or {}
        )

        th_no = (
            query_db(
                """
            SELECT COUNT(*) as total,
                   SUM(CASE WHEN completed THEN 1 ELSE 0 END) as done
            FROM checklist_items ci
            WHERE ci.implantacao_id = %s 
            AND ci.tipo_item = 'tarefa'
            AND NOT EXISTS (
                SELECT 1 FROM checklist_items s 
                WHERE s.parent_id = ci.id 
                AND s.tipo_item = 'subtarefa'
            )
            """,
                (impl_id,),
                one=True,
            )
            or {}
        )

        total = int(sub.get("total", 0) or 0) + int(th_no.get("total", 0) or 0)
        done = int(sub.get("done", 0) or 0) + int(th_no.get("done", 0) or 0)
        return int(round((done / total) * 100)) if total > 0 else 100, total, done

    return 0, 0, 0


@cached_progress(ttl=30)
def _get_progress(impl_id):
    """
    Calcula progresso da implantação usando apenas modelo hierárquico.
    Usa versão otimizada se habilitada via feature flag.
    """
    use_optimized = current_app.config.get("USE_OPTIMIZED_PROGRESS", True)

    if use_optimized:
        return _get_progress_optimized(impl_id)
    else:
        return _get_progress_legacy(impl_id)


# Aliases para compatibilidade
get_progress = _get_progress
invalidar_cache = invalidar_cache_progresso
