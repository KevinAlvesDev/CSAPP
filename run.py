# run.py
import os
from project import create_app

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

    from project.extensions import r2_client

    if not r2_client:

        print("\n!!! ATENÇÃO: Cliente R2 não inicializado. Uploads não funcionarão. !!!\n")



    port = int(os.environ.get("PORT", 5000))

    # Para uso local, se quiser inicializar automaticamente, descomente:

    # with app.app_context():

    #     from project.db import init_db

    #     init_db()

        

    app.run(debug=True, host='0.0.0.0', port=port)