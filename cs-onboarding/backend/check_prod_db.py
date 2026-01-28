"""
Script para verificar estrutura do banco de produção.
"""
import psycopg2

conn = psycopg2.connect("postgresql://postgres:sChnKAdWRKtVXxTIDcQSPKKYrEMbTxNi@switchyard.proxy.rlwy.net:48993/railway")
cursor = conn.cursor()

print("COLUNAS DA TABELA comentarios_h:")
cursor.execute("""
    SELECT column_name FROM information_schema.columns 
    WHERE table_name = 'comentarios_h' ORDER BY ordinal_position
""")
cols = [row[0] for row in cursor.fetchall()]
print(cols)

print()
has_impl_id = 'implantacao_id' in cols
has_item_id = 'checklist_item_id' in cols
print(f"implantacao_id existe: {has_impl_id}")
print(f"checklist_item_id existe: {has_item_id}")

cursor.execute("SELECT COUNT(*) FROM comentarios_h")
print(f"Total comentarios: {cursor.fetchone()[0]}")

conn.close()
