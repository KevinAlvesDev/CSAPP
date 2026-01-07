import sqlite3

conn = sqlite3.connect('backend/project/dashboard_simples.db')
cursor = conn.cursor()

print("=== TODOS os comentários ordenados por data ===\n")
cursor.execute("SELECT id, texto, tag, data_criacao FROM comentarios_h ORDER BY data_criacao DESC LIMIT 10")

for row in cursor.fetchall():
    texto = row[1][:40] if row[1] else ""
    tag = row[2] if row[2] else "(null)"
    print(f"ID: {row[0]:<3} | Tag: {tag:<20} | Data: {row[3]} | Texto: {texto}")

conn.close()
