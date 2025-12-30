import psycopg2
from datetime import datetime

# Conectar ao banco de produção
conn = psycopg2.connect("postgresql://postgres:sChnKAdWRKtVXxTIDcQSPKKYrEMbTxNi@switchyard.proxy.rlwy.net:48993/railway")
cur = conn.cursor()

print("=" * 80)
print("DIAGNÓSTICO DO PROBLEMA DE TIMESTAMP")
print("=" * 80)

# 1. Buscar a implantação WFIT
print("\n1. BUSCANDO IMPLANTAÇÃO WFIT...")
cur.execute("""
    SELECT id, nome_empresa 
    FROM implantacoes 
    WHERE nome_empresa LIKE %s
""", ('%WFIT%',))
impl = cur.fetchone()

if not impl:
    print("[ERRO] Implantacao WFIT nao encontrada!")
    conn.close()
    exit(1)

impl_id, impl_nome = impl
print(f"[OK] Encontrada: ID={impl_id}, Nome={impl_nome}")

# 2. Horário atual do servidor
print(f"\n2. HORÁRIO ATUAL DO SERVIDOR PYTHON:")
now_python = datetime.now()
print(f"   {now_python} (timezone: {now_python.tzinfo})")

# 3. Horário atual do PostgreSQL
print(f"\n3. HORÁRIO ATUAL DO POSTGRESQL:")
cur.execute("SELECT NOW() as now, CURRENT_TIMESTAMP as ts, timezone('America/Sao_Paulo', NOW()) as sp_time")
db_time = cur.fetchone()
print(f"   NOW(): {db_time[0]}")
print(f"   CURRENT_TIMESTAMP: {db_time[1]}")
print(f"   America/Sao_Paulo: {db_time[2]}")

# 4. Últimos 5 comentários desta implantação
print(f"\n4. ÚLTIMOS 5 COMENTÁRIOS DA IMPLANTAÇÃO (ID={impl_id}):")
cur.execute("""
    SELECT 
        ch.id,
        ch.data_criacao,
        ch.texto,
        ch.usuario_cs,
        ci.title as tarefa_nome,
        NOW() - ch.data_criacao as tempo_decorrido
    FROM comentarios_h ch
    INNER JOIN checklist_items ci ON ch.checklist_item_id = ci.id
    WHERE ci.implantacao_id = %s
    ORDER BY ch.data_criacao DESC
    LIMIT 5
""", (impl_id,))

comentarios = cur.fetchall()
if comentarios:
    for i, (cid, data_criacao, texto, usuario, tarefa, tempo_dec) in enumerate(comentarios, 1):
        print(f"\n   Comentário #{i}:")
        print(f"   - ID: {cid}")
        print(f"   - Data criação: {data_criacao}")
        print(f"   - Tipo data: {type(data_criacao)}")
        print(f"   - Texto: {texto[:50]}...")
        print(f"   - Usuário: {usuario}")
        print(f"   - Tarefa: {tarefa}")
        print(f"   - Tempo decorrido (PostgreSQL): {tempo_dec}")
else:
    print("   [ERRO] Nenhum comentario encontrado!")

# 5. Query exata do dashboard
print(f"\n5. QUERY EXATA DO DASHBOARD (MAX data_criacao):")
cur.execute("""
    SELECT 
        ci.implantacao_id,
        MAX(ch.data_criacao) as ultima_atividade,
        COUNT(ch.id) as total_comentarios
    FROM comentarios_h ch
    INNER JOIN checklist_items ci ON ch.checklist_item_id = ci.id
    WHERE ci.implantacao_id = %s
    GROUP BY ci.implantacao_id
""", (impl_id,))

dashboard_result = cur.fetchone()
if dashboard_result:
    _, ultima_atividade, total = dashboard_result
    print(f"   Última atividade: {ultima_atividade}")
    print(f"   Tipo: {type(ultima_atividade)}")
    print(f"   Total comentários: {total}")
    
    # Calcular diferença
    if ultima_atividade:
        cur.execute("SELECT NOW() - %s as diff", (ultima_atividade,))
        diff = cur.fetchone()[0]
        print(f"   Diferença (PostgreSQL): {diff}")
        
        # Calcular em Python
        diff_python = now_python - ultima_atividade.replace(tzinfo=None)
        print(f"   Diferença (Python): {diff_python}")
        print(f"   Diferença em horas: {diff_python.total_seconds() / 3600:.2f}h")
        print(f"   Diferença em dias: {diff_python.days} dias")
else:
    print("   [ERRO] Nenhum resultado da query do dashboard!")

# 6. Verificar timezone da coluna
print(f"\n6. VERIFICANDO TIMEZONE DA COLUNA data_criacao:")
cur.execute("""
    SELECT 
        column_name, 
        data_type, 
        datetime_precision,
        is_nullable
    FROM information_schema.columns 
    WHERE table_name = 'comentarios_h' 
    AND column_name = 'data_criacao'
""")
col_info = cur.fetchone()
if col_info:
    print(f"   Coluna: {col_info[0]}")
    print(f"   Tipo: {col_info[1]}")
    print(f"   Precisão: {col_info[2]}")
    print(f"   Nullable: {col_info[3]}")

print("\n" + "=" * 80)
print("FIM DO DIAGNÓSTICO")
print("=" * 80)

conn.close()
