import sqlite3

conn = sqlite3.connect('backend/project/dashboard_simples.db')
cursor = conn.cursor()

print("=== Comentários com tag 'Simples registro' ===")
cursor.execute("SELECT id, texto, tag, visibilidade FROM comentarios_h WHERE tag = 'Simples registro'")
results = cursor.fetchall()

if results:
    for row in results:
        print(f"ID: {row[0]}, Texto: {row[1][:50]}, Tag: {row[2]}, Visibilidade: {row[3]}")
else:
    print("❌ Nenhum comentário encontrado com tag 'Simples registro'")

print("\n=== Todas as tags únicas no banco ===")
cursor.execute("SELECT DISTINCT tag FROM comentarios_h WHERE tag IS NOT NULL")
tags = cursor.fetchall()
for tag in tags:
    print(f"  - {tag[0]}")

conn.close()
