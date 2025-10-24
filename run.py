import os
# REMOVIDO: Linha incorreta -> from ..blueprints.auth import login_required
from project import create_app

# Cria a instância da aplicação usando a factory
app = create_app()

if __name__ == '__main__':
    print("Iniciando app Flask a partir de run.py...")

    # O init_db agora é um comando do Flask, execute com "flask init-db" no terminal
    # Mas podemos chamar na primeira execução para garantir, se não estiver usando comandos
    with app.app_context():
        from project.db import init_db
        try:
            init_db()
        except Exception as e:
            print(f"ERRO CRÍTICO init_db: {e}")

    # Importa o r2_client aqui, após a app ser criada e as extensões inicializadas
    from project.extensions import r2_client
    if not r2_client:
        print("\n!!! ATENÇÃO: Cliente R2 não inicializado. Uploads R2 não funcionarão. Verifique .env !!!\n")

    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host='0.0.0.0', port=port)

