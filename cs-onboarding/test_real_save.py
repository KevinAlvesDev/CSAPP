import psycopg2
import json

conn_str = "postgresql://postgres:sChnKAdWRKtVXxTIDcQSPKKYrEMbTxNi@switchyard.proxy.rlwy.net:48993/railway"

try:
    print("=== TESTE REAL DE SAVE ===\n")
    conn = psycopg2.connect(conn_str)
    cursor = conn.cursor()
    
    # 1. Pegar uma implantacao existente
    cursor.execute("SELECT id, nome_empresa, chave_oamd, tela_apoio_link FROM implantacoes WHERE id = 74")
    impl = cursor.fetchone()
    
    print(f"ANTES DO UPDATE:")
    print(f"  ID: {impl[0]}")
    print(f"  Empresa: {impl[1]}")
    print(f"  Chave OAMD: {impl[2]}")
    print(f"  Tela Apoio: {impl[3]}")
    
    # 2. Tentar fazer UPDATE (simulando o que o backend faz)
    print("\n=== EXECUTANDO UPDATE ===")
    
    new_chave = "TESTE_123_MANUAL"
    new_tela = "https://teste.com/manual"
    
    update_query = """
        UPDATE implantacoes 
        SET chave_oamd = %s, tela_apoio_link = %s 
        WHERE id = %s
    """
    
    cursor.execute(update_query, (new_chave, new_tela, impl[0]))
    conn.commit()
    
    print(f"UPDATE executado com sucesso!")
    print(f"  Rows affected: {cursor.rowcount}")
    
    # 3. Verificar se salvou
    cursor.execute("SELECT id, nome_empresa, chave_oamd, tela_apoio_link FROM implantacoes WHERE id = 74")
    impl_after = cursor.fetchone()
    
    print(f"\nDEPOIS DO UPDATE:")
    print(f"  ID: {impl_after[0]}")
    print(f"  Empresa: {impl_after[1]}")
    print(f"  Chave OAMD: {impl_after[2]}")
    print(f"  Tela Apoio: {impl_after[3]}")
    
    # 4. Reverter para não bagunçar
    cursor.execute(update_query, (impl[2], impl[3], impl[0]))
    conn.commit()
    print("\n=== DADOS REVERTIDOS ===")
    
    cursor.close()
    conn.close()
    
    print("\n=== CONCLUSAO ===")
    if impl_after[2] == new_chave and impl_after[3] == new_tela:
        print("SUCESSO: O banco ESTA salvando os dados corretamente!")
        print("PROBLEMA: Deve estar no FRONTEND ou CACHE")
    else:
        print("ERRO: O banco NAO esta salvando!")
        
except Exception as e:
    print(f"\nERRO: {e}")
    import traceback
    traceback.print_exc()
