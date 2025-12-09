import psycopg2
import json
from datetime import datetime

# Configurações
HOST = "oamd.pactosolucoes.com.br"
PORT = "5432"
USER = "cs_pacto"
PASS = "pacto@db"
DBNAME = "OAMD"

def get_table_schema(cur, table_name):
    print(f"\n--- Analisando Tabela: {table_name} ---")
    
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
        print(f"  - {col[0]} ({col[1]}) {'NULL' if col[2] == 'YES' else 'NOT NULL'}")
        
    # Obter contagem de linhas
    try:
        cur.execute(f'SELECT COUNT(*) FROM "{table_name}"')
        count = cur.fetchone()[0]
        print(f"Total de registros: {count}")
    except Exception as e:
        print(f"Erro ao contar registros: {e}")

    # Obter amostra (primeira linha)
    try:
        cur.execute(f'SELECT * FROM "{table_name}" LIMIT 1')
        sample = cur.fetchone()
        if sample:
            print("Amostra (1º registro):")
            # Mapear valores com nomes das colunas para facilitar leitura
            col_names = [desc[0] for desc in cur.description]
            sample_dict = dict(zip(col_names, sample))
            
            # Converter datas para string para visualização limpa
            for k, v in sample_dict.items():
                if isinstance(v, datetime):
                    sample_dict[k] = v.isoformat()
                    
            print(json.dumps(sample_dict, indent=2, default=str, ensure_ascii=False))
        else:
            print("Tabela vazia.")
    except Exception as e:
        print(f"Erro ao obter amostra: {e}")

def main():
    print(f"Conectando ao banco '{DBNAME}' para análise de schema (APENAS LEITURA)...")
    try:
        conn = psycopg2.connect(
            host=HOST,
            port=PORT,
            user=USER,
            password=PASS,
            dbname=DBNAME,
            connect_timeout=10
        )
        
        # Garantir modo de leitura (embora só vamos fazer selects)
        conn.set_session(readonly=True)
        
        cur = conn.cursor()
        
        tables = [
            "customersuccess",
            "detalheempresa",
            "empresafinanceiro",
            "planosucesso",
            "planosucessoacao"
        ]
        
        for table in tables:
            get_table_schema(cur, table)
            
        conn.close()
        print("\nAnálise concluída.")
        
    except Exception as e:
        print(f"Erro fatal: {e}")

if __name__ == "__main__":
    main()
