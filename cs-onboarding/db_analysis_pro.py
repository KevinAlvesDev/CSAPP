"""
Análise Profissional de Performance - Nível Senior
Análise completa de banco de dados, queries e arquitetura
"""

import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL = "postgresql://postgres:sChnKAdWRKtVXxTIDcQSPKKYrEMbTxNi@switchyard.proxy.rlwy.net:48993/railway"

def analyze_database():
    """Análise profissional do banco de dados."""
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    print("=" * 80)
    print("ANALISE PROFISSIONAL DE PERFORMANCE - NIVEL SENIOR")
    print("=" * 80)
    
    # 1. Tamanho das tabelas
    print("\n1. TAMANHO DAS TABELAS (Top 10):")
    print("-" * 80)
    cur.execute("""
        SELECT 
            schemaname,
            tablename,
            pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size,
            pg_total_relation_size(schemaname||'.'||tablename) as bytes
        FROM pg_tables
        WHERE schemaname = 'public'
        ORDER BY bytes DESC
        LIMIT 10
    """)
    for row in cur.fetchall():
        print(f"  {row['tablename']:30s} {row['size']:>15s}")
    
    # 2. Índices faltantes (queries sequenciais)
    print("\n2. TABELAS SEM INDICES SUFICIENTES:")
    print("-" * 80)
    cur.execute("""
        SELECT 
            schemaname,
            tablename,
            seq_scan,
            idx_scan,
            CASE 
                WHEN seq_scan + idx_scan > 0 
                THEN ROUND(100.0 * seq_scan / (seq_scan + idx_scan), 2)
                ELSE 0
            END as seq_scan_percent
        FROM pg_stat_user_tables
        WHERE seq_scan > 1000
        ORDER BY seq_scan DESC
        LIMIT 10
    """)
    for row in cur.fetchall():
        print(f"  {row['tablename']:30s} Seq Scans: {row['seq_scan']:>8d} ({row['seq_scan_percent']:>6.2f}%)")
    
    # 3. Cache hit ratio
    print("\n3. CACHE HIT RATIO (deve ser > 99%):")
    print("-" * 80)
    cur.execute("""
        SELECT 
            SUM(heap_blks_read) as heap_read,
            SUM(heap_blks_hit) as heap_hit,
            CASE 
                WHEN SUM(heap_blks_hit) + SUM(heap_blks_read) > 0
                THEN ROUND(100.0 * SUM(heap_blks_hit) / (SUM(heap_blks_hit) + SUM(heap_blks_read)), 2)
                ELSE 0
            END as cache_hit_ratio
        FROM pg_statio_user_tables
    """)
    row = cur.fetchone()
    ratio = row['cache_hit_ratio']
    status = "OK" if ratio > 99 else "ATENCAO" if ratio > 95 else "CRITICO"
    print(f"  Cache Hit Ratio: {ratio:>6.2f}% {status}")
    
    cur.close()
    conn.close()
    
    print("\n" + "=" * 80)
    print("ANALISE CONCLUIDA")
    print("=" * 80)


if __name__ == '__main__':
    analyze_database()
