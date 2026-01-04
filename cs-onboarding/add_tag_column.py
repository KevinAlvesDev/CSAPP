import sqlite3

# Conectar ao banco
conn = sqlite3.connect('backend/project/dashboard_simples.db')
cursor = conn.cursor()

# Verificar se a coluna já existe
cursor.execute("PRAGMA table_info(checklist_items)")
columns = [col[1] for col in cursor.fetchall()]

if 'tag' not in columns:
    print("Adicionando coluna 'tag' na tabela 'checklist_items'...")
    cursor.execute("ALTER TABLE checklist_items ADD COLUMN tag TEXT")
    conn.commit()
    print("[OK] Coluna 'tag' adicionada com sucesso!")
else:
    print("[INFO] Coluna 'tag' ja existe na tabela 'checklist_items'.")

# Verificar resultado
cursor.execute("PRAGMA table_info(checklist_items)")
cols = cursor.fetchall()
print("\nColunas atuais da tabela 'checklist_items':")
for col in cols:
    print(f"  - {col[1]} ({col[2]})")

conn.close()
