import psycopg2
import urllib.parse

# Configurações
HOST = "oamd.pactosolucoes.com.br"
PORT = "5432"
USER = "cs_pacto"
PASS = "pacto@db"

def list_tables(dbname):
    print(f"\n--- Tentando conectar ao banco: {dbname} ---")
    try:
        conn = psycopg2.connect(
            host=HOST,
            port=PORT,
            user=USER,
            password=PASS,
            dbname=dbname,
            connect_timeout=10
        )
        print(f"Conexão bem-sucedida ao banco '{dbname}'!")
        
        cur = conn.cursor()
        
        # Listar tabelas
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name;
        """)
        tables = cur.fetchall()
        
        if tables:
            print(f"Tabelas encontradas ({len(tables)}):")
            for table in tables:
                print(f" - {table[0]}")
        else:
            print("Nenhuma tabela encontrada no schema public.")
            
        conn.close()
        return True
    except Exception as e:
        print(f"Erro ao conectar em '{dbname}': {e}")
        return False

def main():
    # Tentar conectar no banco padrão 'postgres' para listar outros bancos
    try:
        print("Conectando ao 'postgres' para listar bancos...")
        conn = psycopg2.connect(
            host=HOST,
            port=PORT,
            user=USER,
            password=PASS,
            dbname="postgres",
            connect_timeout=10
        )
        cur = conn.cursor()
        cur.execute("SELECT datname FROM pg_database WHERE datistemplate = false;")
        dbs = cur.fetchall()
        print("\nBancos de dados disponíveis:")
        valid_dbs = []
        for db in dbs:
            print(f" - {db[0]}")
            valid_dbs.append(db[0])
        conn.close()
        
        # Se encontrou bancos, tentar listar tabelas do primeiro que não seja postgres/sistema
        # Ou tentar adivinhar qual é o interessante
        target_dbs = [db for db in valid_dbs if db not in ('postgres', 'rdsadmin')]
        
        if target_dbs:
            print(f"\nInvestigando bancos encontrados: {target_dbs}")
            for db in target_dbs:
                list_tables(db)
        else:
            print("\nNenhum banco de usuário óbvio encontrado. Listando tabelas do 'postgres'...")
            list_tables('postgres')

    except Exception as e:
        print(f"Erro ao listar bancos: {e}")
        # Se falhar em conectar no postgres, tenta conectar num banco com mesmo nome do user ou 'pacto'
        print("\nTentando adivinhar nome do banco...")
        candidates = ['pacto', 'oamd', 'cs_pacto']
        for db in candidates:
            if list_tables(db):
                break

if __name__ == "__main__":
    main()
