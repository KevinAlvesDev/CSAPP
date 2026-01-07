import sqlite3

conn = sqlite3.connect('backend/project/dashboard_simples.db')
cursor = conn.cursor()

# Verificar estrutura da tabela
cursor.execute("PRAGMA table_info(comentarios_h)")
columns = cursor.fetchall()
print("=== Estrutura da tabela comentarios_h ===")
for col in columns:
    print(f"  {col[1]} ({col[2]})")

print("\n=== Últimos 5 comentários ===")
cursor.execute("""
    SELECT id, texto, tag, visibilidade, data_criacao 
    FROM comentarios_h 
    ORDER BY id DESC 
    LIMIT 5
""")

print(f"{'ID':<5} | {'Texto':<30} | {'Tag':<20} | {'Visibilidade':<12} | {'Data':<20}")
print("-" * 100)

for row in cursor.fetchall():
    texto = row[1][:27] + "..." if len(row[1]) > 30 else row[1]
    tag = row[2] if row[2] else "(null)"
    print(f"{row[0]:<5} | {texto:<30} | {tag:<20} | {row[3]:<12} | {str(row[4]):<20}")

conn.close()
