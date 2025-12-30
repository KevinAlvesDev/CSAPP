import psycopg2

# Conectar ao banco de produção
conn = psycopg2.connect("postgresql://postgres:sChnKAdWRKtVXxTIDcQSPKKYrEMbTxNi@switchyard.proxy.rlwy.net:48993/railway")
cur = conn.cursor()

print("=" * 80)
print("VERIFICANDO FOREIGN KEYS DA TABELA comentarios_h")
print("=" * 80)

# Verificar constraints da tabela comentarios_h
cur.execute("""
    SELECT 
        tc.constraint_name,
        tc.table_name,
        kcu.column_name,
        ccu.table_name AS foreign_table_name,
        ccu.column_name AS foreign_column_name,
        rc.delete_rule
    FROM information_schema.table_constraints AS tc
    JOIN information_schema.key_column_usage AS kcu
        ON tc.constraint_name = kcu.constraint_name
        AND tc.table_schema = kcu.table_schema
    JOIN information_schema.constraint_column_usage AS ccu
        ON ccu.constraint_name = tc.constraint_name
        AND ccu.table_schema = tc.table_schema
    LEFT JOIN information_schema.referential_constraints AS rc
        ON tc.constraint_name = rc.constraint_name
    WHERE tc.constraint_type = 'FOREIGN KEY'
    AND tc.table_name = 'comentarios_h'
""")

constraints = cur.fetchall()

if constraints:
    for constraint in constraints:
        print(f"\nConstraint: {constraint[0]}")
        print(f"  Tabela: {constraint[1]}")
        print(f"  Coluna: {constraint[2]}")
        print(f"  Referencia: {constraint[3]}.{constraint[4]}")
        print(f"  ON DELETE: {constraint[5]}")
else:
    print("\nNenhuma foreign key encontrada!")

conn.close()
print("\n" + "=" * 80)
