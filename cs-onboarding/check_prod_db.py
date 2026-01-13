
import psycopg2
from psycopg2.extras import DictCursor
import sys

# Connection string
DB_URL = "postgresql://postgres:sChnKAdWRKtVXxTIDcQSPKKYrEMbTxNi@switchyard.proxy.rlwy.net:48993/railway"

def check_table(cursor, table_name, required_columns):
    print(f"\nChecking table '{table_name}'...")
    
    # Check if table exists
    cursor.execute(f"SELECT to_regclass('{table_name}')")
    if not cursor.fetchone()[0]:
        print(f"[ERROR] Table '{table_name}' does NOT exist!")
        return [f"Table {table_name}"]

    # Get existing columns
    cursor.execute(f"""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = '{table_name}'
    """)
    existing_columns = [row[0] for row in cursor.fetchall()]
    
    missing = []
    for col in required_columns:
        if col not in existing_columns:
            missing.append(col)
            print(f"[MISSING] Missing column: {col}")
        else:
            print(f"[OK] Found column: {col}")
            
    return missing

def check_database_structure():
    print(f"Connecting to database...")
    try:
        conn = psycopg2.connect(DB_URL)
        cursor = conn.cursor()
        
        missing_items = {}

        # 1. Check implantacoes
        missing_items['implantacoes'] = check_table(cursor, 'implantacoes', [
            'definicao_carteira', 
            'contexto'  # This is the one we suspect is missing
        ])

        # 2. Check comentarios_h (History)
        missing_items['comentarios_h'] = check_table(cursor, 'comentarios_h', [
            'checklist_item_id', 
            'tag', 
            'visibilidade', 
            'noshow', 
            'imagem_url'
        ])

        # 3. Check planos_sucesso
        missing_items['planos_sucesso'] = check_table(cursor, 'planos_sucesso', [
            'data_atualizacao', 
            'dias_duracao'
        ])

        # 4. Check implantacao_jira_links (Whole table)
        print(f"\nChecking table 'implantacao_jira_links'...")
        cursor.execute("SELECT to_regclass('implantacao_jira_links')")
        if not cursor.fetchone()[0]:
             print(f"[ERROR] Table 'implantacao_jira_links' does NOT exist!")
             missing_items['implantacao_jira_links'] = ['Full Table']
        else:
             print(f"[OK] Table 'implantacao_jira_links' exists.")

        conn.close()
        
        # Summary
        print("\n\n=== SUMMARY OF MISSING ITEMS ===")
        found_issues = False
        for table, items in missing_items.items():
            if items:
                found_issues = True
                print(f"Table '{table}': Missing {items}")
        
        if not found_issues:
            print("[OK] ACID TEST PASSED: All checked columns and tables are present.")

    except Exception as e:
        print(f"\n[ERROR] Error connecting or querying database: {e}")

if __name__ == "__main__":
    check_database_structure()
