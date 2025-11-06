import sys
import os

# --- CORREÇÃO DE PATH ---
# Adiciona o diretório atual (CSAPP) ao sys.path
# Isso garante que o Python encontre o pacote 'project'
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)
# -------------------------

# Importa o create_app DEPOIS de ajustar o path
from project import create_app

# --- Captura de falhas ---
try:
    app = create_app()
except ValueError as e:
    print(f"\n--- ERRO CRÍTICO DE CONFIGURAÇÃO ---\nFalha ao iniciar a aplicação: {e}\nVerifique o arquivo .env e config.py.\n--------------------------------------\n")
    app = None
except Exception as e:
    print(f"\n--- ERRO CRÍTICO INESPERADO ---\nFalha ao iniciar a aplicação: {e}\n--------------------------------------\n")
    app = None
# -----------------------------------------------------------------------


# --- INÍCIO DA CORREÇÃO (Auto-criação do DB) ---
# Move a inicialização do DB para fora do 'if __name__ == "__main__"'
# Isso garante que o Gunicorn (produção) execute este bloco ao iniciar.
if app:
    with app.app_context():
        from project.db import init_db
        try:
            # Esta função agora vai rodar em produção
            init_db() 
            print("Verificação do banco de dados (init_db) concluída.")
        except Exception as e:
            print(f"AVISO: Falha ao inicializar o esquema do banco de dados (init_db): {e}")
# --- FIM DA CORREÇÃO ---


if __name__ == '__main__':
    print("Iniciando app Flask a partir de run.py...")

    if app is None:
        exit(1)

    # A verificação do DB já foi movida para cima e não precisa estar aqui

    from project.extensions import r2_client
    if not r2_client:
        print("\n!!! ATENÇÃO: Cliente R2 não inicializado. Uploads R2 não funcionarão. Verifique .env !!!\n")

    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host='0.0.0.0', port=port)