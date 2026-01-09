
import sys
import os
import json
from datetime import date, datetime

# Adicionar diretório raiz ao path
sys.path.append(os.getcwd())

from flask import Flask
from project.domain.external.query import execute_oamd_search
from project.domain.external.mapper import map_oamd_to_frontend

def json_serial(obj):
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    return str(obj)

app = Flask(__name__)

def diagnose(id_favorecido):
    print(f"\n--- DIAGNÓSTICO PARA ID: {id_favorecido} ---\n")
    try:
        from project.db import get_db_connection_oamd
        conn = get_db_connection_oamd()
        if not conn:
            print("ERRO: Não foi possível conectar ao banco OAMD")
            return

        # Consulta BRUTA direta para ver todas as colunas
        with conn.cursor() as cur:
            cur.execute(f"SELECT * FROM v_cs_implantacao_detalhes WHERE idfavorecido = {id_favorecido}")
            columns = [desc[0] for desc in cur.description]
            row = cur.fetchone()
            
            if not row:
                print("Nenhum registro encontrado na view v_cs_implantacao_detalhes")
                return

            data = dict(zip(columns, row))
            
            print("DADOS BRUTOS DO BANCO:")
            keys_of_interest = [
                'inicioimplantacao', 'datacadastro', 'inicioproducao', 
                'finalimplantacao', 'dtatv', 'data_ativacao'
            ]
            
            for k, v in data.items():
                if k in keys_of_interest or 'data' in k or 'inicio' in k:
                    print(f"  {k}: {v} (Type: {type(v)})")

            print("\n------------------------------------------------\n")
            
            # Testar Mapper
            mapped = map_oamd_to_frontend(data, id_favorecido)
            print("DADOS MAPEADOS (FRONTEND):")
            print(f"  data_inicio_efetivo (inicioimplantacao): {mapped.get('data_inicio_efetivo')}")
            print(f"  data_cadastro (datacadastro): {mapped.get('data_cadastro')}")

    except Exception as e:
        print(f"ERRO CRÍTICO: {e}")

if __name__ == "__main__":
    with app.app_context():
        diagnose(11404)
