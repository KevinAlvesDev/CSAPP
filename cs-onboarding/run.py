import os
import sys

backend_dir = os.path.join(os.path.dirname(__file__), 'backend')
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

try:
    from project import create_app
except ImportError:
    print("\n--- ERRO DE IMPORTAÇÃO ---")
    print(f"Não foi possível encontrar 'project.create_app'.")
    print(f"Certifique-se que o seu código principal está em: {os.path.join(backend_dir, 'project')}")
    print("--------------------------\n")
    sys.exit(1)

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

    try:
        from project.extensions import r2_client
        if not r2_client:
            print("\n!!! ATENÇÃO: Cliente R2 não inicializado. Uploads não funcionarão. !!!\n")
    except ImportError:
        print("\nAviso: Não foi possível importar 'project.extensions' para verificar R2.")
    except Exception:
        pass

    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host='0.0.0.0', port=port, use_reloader=False)
