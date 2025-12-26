"""
Módulo de Gamificação para Analytics
Ranking de gamificação por mês/ano.
Princípio SOLID: Single Responsibility
"""
from datetime import datetime

from ...db import query_db


def get_gamification_rank(month=None, year=None):
    """Ranking de gamificação por mês/ano, usando tabela de métricas mensais."""
    agora = datetime.now()
    m = month or agora.month
    y = year or agora.year
    query = """
        SELECT gm.usuario_cs,
               COALESCE(p.nome, gm.usuario_cs) AS nome,
               COALESCE(gm.pontuacao_calculada, 0) AS pontos
        FROM gamificacao_metricas_mensais gm
        LEFT JOIN perfil_usuario p ON gm.usuario_cs = p.usuario
        WHERE gm.mes = %s AND gm.ano = %s
        ORDER BY gm.pontuacao_calculada DESC, nome ASC
    """
    rows = query_db(query, (m, y)) or []
    labels = [r.get('nome') for r in rows]
    data = [r.get('pontos', 0) for r in rows]
    return { 'labels': labels, 'data': data, 'month': m, 'year': y }
