import sqlite3

conn = sqlite3.connect('backend/project/dashboard_simples.db')
cursor = conn.cursor()

print("=== Últimos 3 comentários (TODOS os campos) ===\n")
cursor.execute("SELECT * FROM comentarios_h ORDER BY id DESC LIMIT 3")

col_names = [description[0] for description in cursor.description]

for row in cursor.fetchall():
    print(f"{'='*80}")
    print(f"ID: {row[0]}")
    for i, col_name in enumerate(col_names):
        print(f"  {col_name}: {row[i]}")
    print()

conn.close()
