import psycopg2
import urllib.parse

# Configurações
HOST = "oamd.pactosolucoes.com.br"
PORT = "5432"
USER = "cs_pacto"
PASS = "pacto@db"
DBNAME = "OAMD"

def inspect_table(table_name):
    print(f"\n--- Inspecionando tabela: {table_name} ---")
    try:
        conn = psycopg2.connect(
            host=HOST,
            port=PORT,
            user=USER,
            password=PASS,
            dbname=DBNAME,
            connect_timeout=10
        )
        cur = conn.cursor()
        
        # Obter colunas
        cur.execute(f"""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns 
            WHERE table_name = '{table_name}' 
            ORDER BY ordinal_position;
        """)
        columns = cur.fetchall()
        
        print("Colunas:")
        for col in columns:
            print(f" - {col[0]} ({col[1]}) [Nullable: {col[2]}]")
            
        # Obter amostra de dados (primeiras 3 linhas)
        print("\nAmostra de dados (primeiras 3 linhas):")
        cur.execute(f"SELECT * FROM {table_name} LIMIT 3;")
        rows = cur.fetchall()
        
        if rows:
            for row in rows:
                print(f" {row}")
        else:
            print(" Tabela vazia.")
            
        conn.close()
    except Exception as e:
        print(f"Erro ao inspecionar tabela '{table_name}': {e}")

def main():
    print(f"Conectando ao banco '{DBNAME}' para detalhar tabelas...")
    tables = [
        "customersuccess",
        "detalheempresa",
        "empresafinanceiro",
        "planosucesso",
        "planosucessoacao"
    ]
    
    for table in tables:
        inspect_table(table)

if __name__ == "__main__":
    main()
