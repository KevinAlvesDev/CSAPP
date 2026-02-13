import sqlite3
import os
from datetime import datetime

db_path = 'c:/Users/kevinpereira/Documents/app/CSAPP/cs-onboarding/backend/project/dashboard_simples.db'
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

try:
    # 1. Encontrar planos que foram "concluídos" por engano (templates que perderam o status)
    headless_plans = cursor.execute("SELECT id, nome, descricao FROM planos_sucesso WHERE status = 'concluido' AND processo_id IS NULL").fetchall()
    
    for plan in headless_plans:
        old_id = plan['id']
        nome = plan['nome']
        desc = plan['descricao']
        
        # 2. Criar um novo plano DE VERDADE para a implantação 1 (assumindo que é a que o usuário está testando)
        cursor.execute(
            "INSERT INTO planos_sucesso (nome, descricao, status, processo_id, contexto, data_atualizacao) VALUES (?, ?, ?, ?, ?, ?)",
            (f"{nome} (Concluído - Recuperado)", desc, 'concluido', 1, 'onboarding', datetime.now())
        )
        new_id = cursor.lastrowid
        
        # 3. Mover os itens do checklist para o novo plano
        cursor.execute("UPDATE checklist_items SET plano_id = ? WHERE plano_id = ?", (new_id, old_id))
        
        # 4. Restaurar o plano original como template
        cursor.execute("UPDATE planos_sucesso SET status = 'em_andamento' WHERE id = ?", (old_id,))
        
        print(f"Recuperado plano {old_id} -> novo ID {new_id} para implantação 1. Template restaurado.")

    conn.commit()
    print("Cleanup concluído com sucesso.")
except Exception as e:
    conn.rollback()
    print(f"Erro no cleanup: {e}")
finally:
    conn.close()
