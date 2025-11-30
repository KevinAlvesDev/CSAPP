import sqlite3
import os

# Path calculation
# The script is in backend/, so project is in backend/project
base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'project'))
db_path = os.path.join(base_dir, 'dashboard_simples.db')

print(f"Checking database at: {db_path}")

if not os.path.exists(db_path):
    print("Database file not found!")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Check checklist_items columns
cursor.execute("PRAGMA table_info(checklist_items)")
columns = [col[1] for col in cursor.fetchall()]
print(f"Existing columns in checklist_items: {columns}")

if 'obrigatoria' not in columns:
    try:
        cursor.execute("ALTER TABLE checklist_items ADD COLUMN obrigatoria INTEGER DEFAULT 0")
        conn.commit()
        print("✅ Column 'obrigatoria' added successfully.")
    except Exception as e:
        print(f"❌ Error adding column: {e}")
else:
    print("ℹ️ Column 'obrigatoria' already exists.")

conn.close()
