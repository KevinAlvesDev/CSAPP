import sqlite3
import os

db_path = os.path.join('backend', 'dashboard_simples.db')
if not os.path.exists(db_path):
    print(f"Database not found at {db_path}")
else:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print("Tables:", [t[0] for t in tables])
    
    # Check if hierarchy tables have data
    for table in ['fases', 'grupos', 'tarefas_h', 'subtarefas_h']:
        if (table,) in tables:
            cursor.execute(f"SELECT count(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"{table}: {count} rows")
        else:
            print(f"{table}: MISSING")
    
    conn.close()
