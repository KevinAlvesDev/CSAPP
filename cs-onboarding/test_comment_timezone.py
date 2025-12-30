import sys
sys.path.insert(0, 'backend')

from datetime import datetime, timezone, timedelta
import psycopg2

# Conectar ao banco de produção
conn = psycopg2.connect("postgresql://postgres:sChnKAdWRKtVXxTIDcQSPKKYrEMbTxNi@switchyard.proxy.rlwy.net:48993/railway")
cur = conn.cursor()

print("=" * 80)
print("TESTE DE TIMEZONE - CRIANDO COMENTÁRIO")
print("=" * 80)

# 1. Horário atual
tz_brasilia = timezone(timedelta(hours=-3))
now_brasilia = datetime.now(tz_brasilia)
now_utc = datetime.now(timezone.utc)

print(f"\nHorário atual:")
print(f"  Brasília (UTC-3): {now_brasilia}")
print(f"  UTC: {now_utc}")

# 2. Buscar um checklist_item para testar
cur.execute("SELECT id FROM checklist_items WHERE implantacao_id = 80 LIMIT 1")
item = cur.fetchone()

if not item:
    print("\nERRO: Nenhum checklist_item encontrado!")
    conn.close()
    exit(1)

item_id = item[0]
print(f"\nUsando checklist_item ID: {item_id}")

# 3. Inserir comentário com horário de Brasília
print(f"\nInserindo comentário com timestamp: {now_brasilia}")
cur.execute("""
    INSERT INTO comentarios_h (checklist_item_id, usuario_cs, texto, data_criacao, visibilidade)
    VALUES (%s, %s, %s, %s, %s)
    RETURNING id, data_criacao
""", (item_id, 'kevinpereira@pactosolucoes.com.br', 'Teste de timezone', now_brasilia, 'interno'))

result = cur.fetchone()
comentario_id = result[0]
data_salva = result[1]

print(f"\nComentário criado:")
print(f"  ID: {comentario_id}")
print(f"  Data salva no banco: {data_salva}")
print(f"  Tipo: {type(data_salva)}")

# 4. Buscar de volta
cur.execute("SELECT data_criacao FROM comentarios_h WHERE id = %s", (comentario_id,))
data_lida = cur.fetchone()[0]

print(f"\nData lida do banco: {data_lida}")
print(f"  Tipo: {type(data_lida)}")

# 5. Comparar
print(f"\nComparação:")
print(f"  Enviado: {now_brasilia}")
print(f"  Salvo: {data_salva}")
print(f"  Lido: {data_lida}")
print(f"  São iguais? {data_salva == data_lida}")

# 6. Deletar comentário de teste
cur.execute("DELETE FROM comentarios_h WHERE id = %s", (comentario_id,))
conn.commit()

print(f"\nComentário de teste deletado.")

conn.close()
print("\n" + "=" * 80)
