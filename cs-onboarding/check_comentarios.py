import sqlite3

conn = sqlite3.connect('backend/project/dashboard_simples.db')
cursor = conn.cursor()

cursor.execute("PRAGMA table_info(comentarios_h)")
cols = cursor.fetchall()

print("Colunas da tabela 'comentarios_h':")
for col in cols:
    print(f"  - {col[1]} ({col[2]})")

conn.close()
