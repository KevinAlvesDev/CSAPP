import sys
sys.path.insert(0, 'backend')

from project.database.migrations.fix_timezone_comentarios import migrate_comentarios_timezone
import psycopg2

# Conectar ao banco de produção
print("Conectando ao banco de producao...")
conn = psycopg2.connect("postgresql://postgres:sChnKAdWRKtVXxTIDcQSPKKYrEMbTxNi@switchyard.proxy.rlwy.net:48993/railway")

try:
    print("\n" + "=" * 80)
    print("EXECUTANDO MIGRATION: Fix Timezone")
    print("=" * 80 + "\n")
    
    migrate_comentarios_timezone(conn)
    
    print("\n" + "=" * 80)
    print("SUCESSO! Migration executada.")
    print("=" * 80)
    
except Exception as e:
    print(f"\nERRO: {e}")
    import traceback
    traceback.print_exc()
finally:
    conn.close()
    print("\nConexao fechada.")
