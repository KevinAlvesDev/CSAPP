import sqlite3

conn = sqlite3.connect('backend/project/dashboard_simples.db')
cursor = conn.cursor()

# Verificar se a coluna ja existe
cursor.execute("PRAGMA table_info(comentarios_h)")
columns = [col[1] for col in cursor.fetchall()]

if 'tag' not in columns:
    print("Adicionando coluna 'tag' na tabela 'comentarios_h'...")
    cursor.execute("ALTER TABLE comentarios_h ADD COLUMN tag TEXT")
    conn.commit()
    print("[OK] Coluna 'tag' adicionada com sucesso!")
else:
    print("[INFO] Coluna 'tag' ja existe na tabela 'comentarios_h'.")

# Verificar resultado
cursor.execute("PRAGMA table_info(comentarios_h)")
cols = cursor.fetchall()
print("\nColunas atuais da tabela 'comentarios_h':")
for col in cols:
    print(f"  - {col[1]} ({col[2]})")

conn.close()
