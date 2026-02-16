import csv
import io
import os
import shutil
import zipfile
from datetime import datetime

from flask import current_app

from ....config.logging_config import management_logger
from ....db import db_connection


def perform_backup():
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    backup_dir = os.path.join(base_dir, "backups")
    os.makedirs(backup_dir, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d-%H%M%S")

    with db_connection() as (conn, db_type):
        if db_type == "sqlite":
            sqlite_base = os.path.abspath(os.path.dirname(base_dir))
            is_testing = current_app.config.get("TESTING", False)
            db_filename = "dashboard_simples_test.db" if is_testing else "dashboard_simples.db"
            db_path = os.path.join(sqlite_base, db_filename)
            if not os.path.exists(db_path):
                raise FileNotFoundError(f"Arquivo SQLite não encontrado: {db_path}")

            target = os.path.join(backup_dir, f"db-sqlite-{ts}.sqlite")
            shutil.copy2(db_path, target)
            management_logger.info(f"SQLite backup criado: {target}")
            return {"type": "sqlite", "backup_file": target.replace(base_dir + os.sep, "")}

        if db_type == "postgres":
            tables = [
                "usuarios",
                "perfil_usuario",
                "implantacoes",
                "tarefas",
                "comentarios",
                "timeline_log",
                "gamificacao_regras",
                "gamificacao_metricas_mensais",
            ]
            zip_path = os.path.join(backup_dir, f"db-postgres-{ts}.zip")
            with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                cur = conn.cursor()
                for tbl in tables:
                    try:
                        cur.execute(f"SELECT * FROM {tbl}")
                        rows = cur.fetchall() or []
                        if hasattr(cur, "description") and cur.description:
                            headers = [col.name if hasattr(col, "name") else col[0] for col in cur.description]
                        else:
                            headers = []
                        buf = io.StringIO()
                        writer = csv.writer(buf)
                        if headers:
                            writer.writerow(headers)
                        for r in rows:
                            writer.writerow(list(r))
                        zf.writestr(f"{tbl}.csv", buf.getvalue())
                    except Exception as te:
                        management_logger.error(f"Falha ao exportar tabela {tbl}: {te}")
                cur.close()
            management_logger.info(f"PostgreSQL backup criado: {zip_path}")
            return {"type": "postgres", "backup_file": zip_path.replace(base_dir + os.sep, "")}

        raise RuntimeError(f"Tipo de banco desconhecido: {db_type}")
