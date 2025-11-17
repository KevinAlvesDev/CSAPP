# testo/CSAPP/run.py
import os
import sys

# --- CORREÇÃO DE IMPORTAÇÃO ---
# Adiciona o diretório 'backend' ao path do Python
# para que possamos importar 'project' de dentro dele.
backend_dir = os.path.join(os.path.dirname(__file__), 'backend')
if backend_dir not in sys.path:
    # Insere no início da lista para ter prioridade
    sys.path.insert(0, backend_dir)

# Importa 'create_app' de 'backend.project'
try:
    from backend.project import create_app
except ImportError:
    print("\n--- ERRO DE IMPORTAÇÃO ---")
    print(f"Não foi possível encontrar 'backend.project.create_app'.")
    print(f"Certifique-se que o seu código principal está em: {os.path.join(backend_dir, 'project')}")
    print("--------------------------\n")
    sys.exit(1)
# --- FIM DA CORREÇÃO ---


# --- Captura de falhas ---
try:
    app = create_app()
except ValueError as e:
    print(f"\n--- ERRO CRÍTICO DE CONFIGURAÇÃO ---\nFalha ao iniciar a aplicação: {e}\nVerifique as variáveis de ambiente.\n--------------------------------------\n")
    app = None
except Exception as e:
    print(f"\n--- ERRO CRÍTICO INESPERADO ---\nFalha ao iniciar a aplicação: {e}\n--------------------------------------\n")
    app = None

if __name__ == '__main__':

    if app is None:

        exit(1)

    # Verifica R2 apenas no arranque local para aviso
    try:
        from project.extensions import r2_client
        if not r2_client:
            print("\n!!! ATENÇÃO: Cliente R2 não inicializado. Uploads não funcionarão. !!!\n")
    except ImportError:
        print("\nAviso: Não foi possível importar 'project.extensions' para verificar R2.")
    except Exception:
        pass # Falha silenciosa se r2_client não estiver no contexto

    port = int(os.environ.get("PORT", 5000))

    # Para uso local, se quiser inicializar automaticamente, descomente:
    # with app.app_context():
    #     from project.db import init_db
    #     init_db()
        
    app.run(debug=True, host='0.0.0.0', port=port)
