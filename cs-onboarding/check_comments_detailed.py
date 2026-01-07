import sqlite3

conn = sqlite3.connect('backend/project/dashboard_simples.db')
cursor = conn.cursor()

# Verificar TODAS as colunas
cursor.execute("PRAGMA table_info(comentarios_h)")
columns = cursor.fetchall()
print("=== TODAS as colunas da tabela comentarios_h ===")
for col in columns:
    print(f"  Col {col[0]}: {col[1]} ({col[2]}) - NotNull:{col[3]}, Default:{col[4]}, PK:{col[5]}")

print("\n=== Últimos 10 comentários (com TODAS as colunas) ===")
cursor.execute("SELECT * FROM comentarios_h ORDER BY id DESC LIMIT 10")

# Pegar nomes das colunas
col_names = [description[0] for description in cursor.description]
print("Colunas:", col_names)
print("-" * 150)

for row in cursor.fetchall():
    print(f"ID: {row[0]}")
    for i, col_name in enumerate(col_names):
        if row[i] is not None:
            print(f"  {col_name}: {row[i]}")
    print()

conn.close()
