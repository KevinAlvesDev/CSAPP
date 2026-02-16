import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from project import create_app
from project.db import db_connection, query_db
from project.modules.planos.domain.aplicar import criar_instancia_plano_para_implantacao


def _build_in_clause(values, db_type):
    if not values:
        return "", []
    placeholder = "%s" if db_type == "postgres" else "?"
    return ",".join([placeholder] * len(values)), list(values)


def repair_planos_concluidos_templates(dry_run: bool = True):
    """
    Repara implantacoes que apontam para templates (processo_id IS NULL).
    - Reverte templates concluídos para em_andamento se estiverem vinculados a implantacoes.
    - Cria instancias por implantacao e atualiza implantacoes.plano_sucesso_id.
    """
    # Buscar implantacoes com plano template (processo_id IS NULL)
    rows = query_db(
        """
        SELECT i.id AS implantacao_id, i.plano_sucesso_id AS template_id
        FROM implantacoes i
        JOIN planos_sucesso p ON p.id = i.plano_sucesso_id
        WHERE p.processo_id IS NULL
        """,
    )

    if not rows:
        print("Nenhuma implantacao vinculada a template encontrada.")
        return

    template_ids = sorted({r["template_id"] for r in rows if r.get("template_id")})
    print(f"Implantacoes a reparar: {len(rows)}")
    print(f"Templates envolvidos: {len(template_ids)} -> {template_ids}")

    with db_connection() as (conn, db_type):
        cursor = conn.cursor()

        # Reverter templates concluídos usados por implantacoes
        if template_ids:
            in_clause, in_params = _build_in_clause(template_ids, db_type)
            sql_reset = f"""
                UPDATE planos_sucesso
                SET status = 'em_andamento', data_atualizacao = %s
                WHERE id IN ({in_clause}) AND status = 'concluido'
            """
            if db_type == "sqlite":
                sql_reset = sql_reset.replace("%s", "?")
            if dry_run:
                print("[dry-run] Reset templates concluídos -> em_andamento")
            else:
                now = datetime.now()
                cursor.execute(sql_reset, [now] + in_params)

        # Criar instancias por implantacao (se ainda não existe)
        repaired = 0
        skipped = 0
        for row in rows:
            impl_id = row["implantacao_id"]
            template_id = row["template_id"]

            # Verificar se já existe instancia em andamento para a implantacao
            existing = query_db(
                """
                SELECT id
                FROM planos_sucesso
                WHERE processo_id = %s AND status = 'em_andamento'
                ORDER BY data_criacao DESC
                LIMIT 1
                """,
                (impl_id,),
                one=True,
            )
            if existing and existing.get("id"):
                if dry_run:
                    print(f"[dry-run] Implantacao {impl_id}: instancia existente {existing['id']} (skip)")
                else:
                    # Garante que a implantacao aponta para a instancia ativa
                    sql_update = "UPDATE implantacoes SET plano_sucesso_id = %s WHERE id = %s"
                    if db_type == "sqlite":
                        sql_update = sql_update.replace("%s", "?")
                    cursor.execute(sql_update, (existing["id"], impl_id))
                skipped += 1
                continue

            if dry_run:
                print(f"[dry-run] Implantacao {impl_id}: criar instancia a partir do template {template_id}")
                repaired += 1
                continue

            new_id = criar_instancia_plano_para_implantacao(
                plano_id=template_id,
                implantacao_id=impl_id,
                usuario="sistema",
                cursor=cursor,
                db_type=db_type,
            )
            sql_update = "UPDATE implantacoes SET plano_sucesso_id = %s WHERE id = %s"
            if db_type == "sqlite":
                sql_update = sql_update.replace("%s", "?")
            cursor.execute(sql_update, (new_id, impl_id))
            repaired += 1

        if dry_run:
            print(f"[dry-run] Criaria instancias para {repaired}, skipped {skipped}")
        else:
            conn.commit()
            print(f"Instancias criadas: {repaired}, skipped {skipped}")


def main():
    dry_run = "--dry-run" in sys.argv
    app = create_app()
    with app.app_context():
        repair_planos_concluidos_templates(dry_run=dry_run)


if __name__ == "__main__":
    main()
