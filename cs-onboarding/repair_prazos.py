import os
import sys
from datetime import datetime, date, timedelta
from pathlib import Path

# Configurar caminhos para importar o projeto
project_root = Path(__file__).resolve().parent
sys.path.append(str(project_root))

from backend.project import create_app
from backend.project.db import db_connection, query_db
from backend.project.common.date_helpers import add_business_days, adjust_to_business_day

def repair_prazos():
    app = create_app()
    with app.app_context():
        print("\n🔍 Iniciando reparo global de prazos (Padrão: Apenas Dias Úteis)...")
        
        # 1. Buscar implantações ativas
        sql_impls = """
            SELECT id, data_inicio_efetivo, data_criacao, data_atribuicao_plano, plano_sucesso_id 
            FROM implantacoes 
            WHERE status NOT IN ('concluida', 'cancelada')
        """
        impls = query_db(sql_impls)
        
        if not impls:
            print("✅ Nenhuma implantação ativa encontrada no banco de dados.")
            return

        total_itens_verificados = 0
        total_itens_ajustados = 0
        total_impls_ajustadas = 0
        
        print(f"📋 Verificando {len(impls)} implantações...")

        with db_connection() as (conn, db_type):
            cursor = conn.cursor()
            
            for impl in impls:
                impl_id = impl['id']
                plano_id = impl.get('plano_sucesso_id')
                
                # A) Definir data base
                db_val = impl.get('data_inicio_efetivo') or impl.get('data_atribuicao_plano') or impl.get('data_criacao')
                if not db_val: continue
                    
                if isinstance(db_val, str):
                    try: data_base = datetime.strptime(db_val[:10], "%Y-%m-%d").date()
                    except: continue
                elif isinstance(db_val, datetime): data_base = db_val.date()
                elif isinstance(db_val, date): data_base = db_val
                else: continue

                # B) Recalcular data_previsao_termino da Implantação
                if plano_id:
                    cursor.execute(
                        "SELECT dias_duracao FROM planos_sucesso WHERE id = " + ("?" if db_type == "sqlite" else "%s"),
                        (plano_id,)
                    )
                    p_row = cursor.fetchone()
                    d_duracao = (p_row[0] if isinstance(p_row, (tuple, list)) else p_row['dias_duracao']) if p_row else None
                    
                    if d_duracao:
                        new_impl_deadline = add_business_days(data_base, int(d_duracao))
                        cursor.execute(
                            "UPDATE implantacoes SET data_previsao_termino = " + ("?" if db_type == "sqlite" else "%s") + " WHERE id = " + ("?" if db_type == "sqlite" else "%s"),
                            (new_impl_deadline, impl_id)
                        )
                        total_impls_ajustadas += 1

                # C) Atualizar itens do checklist
                sql_items = "SELECT id, dias_offset, previsao_original, nova_previsao FROM checklist_items WHERE implantacao_id = %s"
                if db_type == "sqlite": sql_items = sql_items.replace("%s", "?")
                
                cursor.execute(sql_items, (impl_id,))
                items_rows = cursor.fetchall()
                
                for row in items_rows:
                    if hasattr(row, 'keys'): 
                        item_id, offset, p_orig_raw, n_prev_raw = row['id'], row['dias_offset'], row['previsao_original'], row['nova_previsao']
                    else:
                        item_id, offset, p_orig_raw, n_prev_raw = row[0], row[1], row[2], row[3]

                    cols_to_update = []
                    params = []

                    if offset is not None:
                        try:
                            new_p_orig = adjust_to_business_day(add_business_days(data_base, int(offset)))
                            
                            p_orig_date = None
                            if isinstance(p_orig_raw, str):
                                try: p_orig_date = datetime.strptime(p_orig_raw[:10], "%Y-%m-%d").date()
                                except: pass
                            elif isinstance(p_orig_raw, (datetime, date)):
                                p_orig_date = p_orig_raw.date() if isinstance(p_orig_raw, datetime) else p_orig_raw
                                
                            if new_p_orig != p_orig_date:
                                cols_to_update.append("previsao_original = %s")
                                params.append(new_p_orig)
                        except: pass

                    if n_prev_raw:
                        try:
                            n_prev_date = None
                            if isinstance(n_prev_raw, str):
                                try: n_prev_date = datetime.strptime(n_prev_raw[:10], "%Y-%m-%d").date()
                                except: pass
                            elif isinstance(n_prev_raw, (datetime, date)):
                                n_prev_date = n_prev_raw.date() if isinstance(n_prev_raw, datetime) else n_prev_raw
                            
                            if n_prev_date:
                                adjusted_n = adjust_to_business_day(n_prev_date)
                                if adjusted_n != n_prev_date:
                                    cols_to_update.append("nova_previsao = %s")
                                    params.append(adjusted_n)
                        except: pass

                    if cols_to_update:
                        sql_upd = f"UPDATE checklist_items SET {', '.join(cols_to_update)}, updated_at = %s WHERE id = %s"
                        if db_type == "sqlite": sql_upd = sql_upd.replace("%s", "?")
                        params.extend([datetime.now(), item_id])
                        cursor.execute(sql_upd, tuple(params))
                        total_itens_ajustados += 1
                    
                    total_itens_verificados += 1

            conn.commit()
            print(f"\n✨ Reparo concluído!")
            print(f"📊 Relatório:")
            print(f"   - Itens de checklist reajustados: {total_itens_ajustados}")
            print(f"   - Prazos de implantação atualizados: {total_impls_ajustadas}")
            print(f"\nTodos os planos em andamento agora seguem exclusivamente o calendário de dias úteis.")

if __name__ == "__main__":
    repair_prazos()
