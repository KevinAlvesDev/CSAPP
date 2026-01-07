import sqlite3

conn = sqlite3.connect('backend/project/dashboard_simples.db')
cursor = conn.cursor()

try:
    # Adicionar coluna tag
    print("Adicionando coluna 'tag' à tabela comentarios_h...")
    cursor.execute("ALTER TABLE comentarios_h ADD COLUMN tag TEXT")
    conn.commit()
    print("✅ Coluna 'tag' adicionada com sucesso!")
    
    # Adicionar coluna visibilidade se não existir
    print("\nVerificando coluna 'visibilidade'...")
    cursor.execute("PRAGMA table_info(comentarios_h)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'visibilidade' not in columns:
        print("Adicionando coluna 'visibilidade'...")
        cursor.execute("ALTER TABLE comentarios_h ADD COLUMN visibilidade TEXT DEFAULT 'interno'")
        conn.commit()
        print("✅ Coluna 'visibilidade' adicionada com sucesso!")
    else:
        print("✅ Coluna 'visibilidade' já existe")
    
    # Adicionar coluna noshow se não existir
    print("\nVerificando coluna 'noshow'...")
    cursor.execute("PRAGMA table_info(comentarios_h)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'noshow' not in columns:
        print("Adicionando coluna 'noshow'...")
        cursor.execute("ALTER TABLE comentarios_h ADD COLUMN noshow INTEGER DEFAULT 0")
        conn.commit()
        print("✅ Coluna 'noshow' adicionada com sucesso!")
    else:
        print("✅ Coluna 'noshow' já existe")
    
    # Mostrar estrutura atualizada
    print("\n=== Estrutura atualizada da tabela comentarios_h ===")
    cursor.execute("PRAGMA table_info(comentarios_h)")
    for col in cursor.fetchall():
        print(f"  {col[1]} ({col[2]})")
    
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e):
        print(f"⚠️ Coluna já existe: {e}")
    else:
        print(f"❌ Erro: {e}")
finally:
    conn.close()

print("\n✅ Migração concluída!")
