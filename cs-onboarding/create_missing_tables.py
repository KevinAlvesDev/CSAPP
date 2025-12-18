import psycopg2

conn = psycopg2.connect('postgresql://postgres:sChnKAdWRKtVXxTIDcQSPKKYrEMbTxNi@switchyard.proxy.rlwy.net:48993/railway')
cur = conn.cursor()

# Criar tabela checklist_status_history
cur.execute("""
    CREATE TABLE IF NOT EXISTS checklist_status_history (
        id SERIAL PRIMARY KEY,
        checklist_item_id INTEGER NOT NULL,
        old_status VARCHAR(50),
        new_status VARCHAR(50),
        changed_by VARCHAR(255),
        changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (checklist_item_id) REFERENCES checklist_items(id) ON DELETE CASCADE
    )
""")
print("Tabela checklist_status_history criada!")

# Criar tabela checklist_prazos_history
cur.execute("""
    CREATE TABLE IF NOT EXISTS checklist_prazos_history (
        id SERIAL PRIMARY KEY,
        checklist_item_id INTEGER NOT NULL,
        old_previsao TIMESTAMP,
        new_previsao TIMESTAMP,
        changed_by VARCHAR(255),
        changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (checklist_item_id) REFERENCES checklist_items(id) ON DELETE CASCADE
    )
""")
print("Tabela checklist_prazos_history criada!")

conn.commit()
conn.close()

print("\nTabelas criadas com sucesso!")
