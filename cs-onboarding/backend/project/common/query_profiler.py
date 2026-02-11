"""
Query Profiler — Monitora e loga queries lentas.

Identifica automaticamente queries que excedem o threshold configurado
e loga informações detalhadas para otimização.

Uso:
    from backend.project.common.query_profiler import QueryProfiler, profile_query

    # Contexto automático
    with QueryProfiler("buscar_implantacoes"):
        result = query_db("SELECT * FROM implantacoes WHERE ...")

    # Decorator
    @profile_query("get_dashboard")
    def get_dashboard_data():
        ...
"""

from __future__ import annotations

import functools
import logging
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger("database")

# Threshold padrão: queries acima de 100ms são logadas como WARNING
DEFAULT_SLOW_QUERY_THRESHOLD_MS = 100

# Threshold crítico: queries acima de 500ms são logadas como ERROR
DEFAULT_CRITICAL_QUERY_THRESHOLD_MS = 500


@dataclass
class QueryStats:
    """Estatísticas de uma query executada."""

    operation: str
    duration_ms: float
    query_preview: str = ""
    params_count: int = 0
    result_count: int = 0
    is_slow: bool = False
    is_critical: bool = False
    timestamp: float = field(default_factory=time.time)


class QueryProfiler:
    """
    Context manager para profile de queries.

    Exemplo:
        with QueryProfiler("buscar_implantacoes") as profiler:
            result = query_db("SELECT ...")
            profiler.set_result_count(len(result))
    """

    _stats_history: ClassVar[list[QueryStats]] = []
    _max_history: ClassVar[int] = 1000

    def __init__(
        self,
        operation: str,
        slow_threshold_ms: float = DEFAULT_SLOW_QUERY_THRESHOLD_MS,
        critical_threshold_ms: float = DEFAULT_CRITICAL_QUERY_THRESHOLD_MS,
    ):
        self.operation = operation
        self.slow_threshold_ms = slow_threshold_ms
        self.critical_threshold_ms = critical_threshold_ms
        self._start_time: float = 0
        self._result_count: int = 0
        self._query_preview: str = ""

    def set_result_count(self, count: int) -> None:
        """Define o número de resultados retornados."""
        self._result_count = count

    def set_query_preview(self, query: str, max_length: int = 200) -> None:
        """Define um preview da query executada."""
        self._query_preview = query[:max_length] + ("..." if len(query) > max_length else "")

    def __enter__(self) -> QueryProfiler:
        self._start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        duration_ms = (time.perf_counter() - self._start_time) * 1000

        stats = QueryStats(
            operation=self.operation,
            duration_ms=round(duration_ms, 2),
            query_preview=self._query_preview,
            result_count=self._result_count,
            is_slow=duration_ms >= self.slow_threshold_ms,
            is_critical=duration_ms >= self.critical_threshold_ms,
        )

        # Armazenar no histórico
        QueryProfiler._stats_history.append(stats)
        if len(QueryProfiler._stats_history) > QueryProfiler._max_history:
            QueryProfiler._stats_history = QueryProfiler._stats_history[-QueryProfiler._max_history :]

        # Logar se necessário
        if stats.is_critical:
            logger.error(
                f"🔴 CRITICAL SLOW QUERY [{self.operation}]: "
                f"{duration_ms:.1f}ms | "
                f"results={self._result_count} | "
                f"query={self._query_preview}"
            )
        elif stats.is_slow:
            logger.warning(
                f"🟡 SLOW QUERY [{self.operation}]: "
                f"{duration_ms:.1f}ms | "
                f"results={self._result_count} | "
                f"query={self._query_preview}"
            )

    @classmethod
    def get_stats_summary(cls) -> dict[str, Any]:
        """Retorna resumo das estatísticas de queries."""
        if not cls._stats_history:
            return {"total": 0, "slow": 0, "critical": 0}

        durations = [s.duration_ms for s in cls._stats_history]
        slow_count = sum(1 for s in cls._stats_history if s.is_slow)
        critical_count = sum(1 for s in cls._stats_history if s.is_critical)

        # Top 5 operações mais lentas
        sorted_stats = sorted(cls._stats_history, key=lambda s: s.duration_ms, reverse=True)
        top_slow = [{"operation": s.operation, "duration_ms": s.duration_ms} for s in sorted_stats[:5]]

        return {
            "total": len(cls._stats_history),
            "slow": slow_count,
            "critical": critical_count,
            "avg_ms": round(sum(durations) / len(durations), 2),
            "max_ms": round(max(durations), 2),
            "min_ms": round(min(durations), 2),
            "p95_ms": round(sorted(durations)[int(len(durations) * 0.95)], 2) if len(durations) > 1 else durations[0],
            "top_slow": top_slow,
        }

    @classmethod
    def reset_stats(cls) -> None:
        """Limpa o histórico de estatísticas."""
        cls._stats_history.clear()


def profile_query(
    operation: str,
    slow_threshold_ms: float = DEFAULT_SLOW_QUERY_THRESHOLD_MS,
    critical_threshold_ms: float = DEFAULT_CRITICAL_QUERY_THRESHOLD_MS,
) -> Callable:
    """
    Decorator para profile automático de funções que executam queries.

    Exemplo:
        @profile_query("get_dashboard_data")
        def get_dashboard_data(user_email):
            ...
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            with QueryProfiler(operation, slow_threshold_ms, critical_threshold_ms):
                return func(*args, **kwargs)

        return wrapper

    return decorator


@contextmanager
def profiled_section(name: str):
    """
    Context manager simples para medir tempo de qualquer seção de código.

    Exemplo:
        with profiled_section("processar_dados"):
            resultado = processar_dados_complexos()
    """
    start = time.perf_counter()
    try:
        yield
    finally:
        duration_ms = (time.perf_counter() - start) * 1000
        if duration_ms > DEFAULT_SLOW_QUERY_THRESHOLD_MS:
            logger.warning(f"⏱️ Section [{name}]: {duration_ms:.1f}ms")
        else:
            logger.debug(f"⏱️ Section [{name}]: {duration_ms:.1f}ms")
