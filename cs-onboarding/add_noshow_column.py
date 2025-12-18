import psycopg2

conn = psycopg2.connect('postgresql://postgres:sChnKAdWRKtVXxTIDcQSPKKYrEMbTxNi@switchyard.proxy.rlwy.net:48993/railway')
cur = conn.cursor()

# Adicionar coluna noshow à tabela comentarios_h
cur.execute("""
    ALTER TABLE comentarios_h ADD COLUMN IF NOT EXISTS noshow BOOLEAN DEFAULT FALSE
""")
print("Coluna 'noshow' adicionada à tabela comentarios_h!")

conn.commit()
conn.close()
print("Sucesso!")
