"""
Cria ou atualiza um usuário administrador com permissões totais.

Uso:
    python backend/tools/create_or_update_admin.py

Lê o e-mail e a senha diretamente deste arquivo (ajuste abaixo conforme necessário).
"""

import os
import sys
from werkzeug.security import generate_password_hash

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(CURRENT_DIR)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from project import create_app

EMAIL = "suporte01.cs@gmail.com"
PLAIN_PASSWORD = "323397041"


def main():
    app = create_app()
    with app.app_context():
        from project.db import query_db, execute_db
        from project.constants import PERFIL_ADMIN

        print(f"[Admin Seed] Processando usuário: {EMAIL}")
        senha_hash = generate_password_hash(PLAIN_PASSWORD)

        usuario = query_db("SELECT usuario FROM usuarios WHERE usuario = %s", (EMAIL,), one=True)
        if usuario:
            execute_db("UPDATE usuarios SET senha = %s WHERE usuario = %s", (senha_hash, EMAIL))
            print("[Admin Seed] Senha atualizada.")
        else:
            execute_db("INSERT INTO usuarios (usuario, senha) VALUES (%s, %s)", (EMAIL, senha_hash))
            print("[Admin Seed] Usuário criado.")

        perfil = query_db("SELECT usuario, perfil_acesso FROM perfil_usuario WHERE usuario = %s", (EMAIL,), one=True)
        if perfil:
            execute_db("UPDATE perfil_usuario SET perfil_acesso = %s WHERE usuario = %s", (PERFIL_ADMIN, EMAIL))
            print("[Admin Seed] Perfil atualizado para Administrador.")
        else:

            nome = EMAIL.split('@')[0].replace('.', ' ').title()
            execute_db(
                "INSERT INTO perfil_usuario (usuario, nome, perfil_acesso) VALUES (%s, %s, %s)",
                (EMAIL, nome, PERFIL_ADMIN)
            )
            print("[Admin Seed] Perfil criado como Administrador.")

        print("[Admin Seed] Concluído com sucesso.")


if __name__ == "__main__":
    main()