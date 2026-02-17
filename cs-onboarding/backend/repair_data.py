import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

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
                cursor.execute(sql_reset, [now, *in_params])

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


def repair_planos_concluidos_invalidos(dry_run: bool = True):
    """
    Repara planos concluídos inválidos (sem qualquer item de checklist).
    Regras:
    - Considera inválido plano com status='concluido', processo_id preenchido e sem checklist_items.
    - Reabre (status='em_andamento') apenas o mais recente inválido por implantação.
    - Se não houver plano ativo na implantação, atualiza implantacoes.plano_sucesso_id para o reaberto.
    """
    rows = query_db(
        """
        SELECT p.id, p.processo_id, p.data_atualizacao, p.data_criacao
        FROM planos_sucesso p
        WHERE p.status = 'concluido'
          AND p.processo_id IS NOT NULL
          AND NOT EXISTS (
            SELECT 1
            FROM checklist_items ci
            WHERE ci.plano_id = p.id
          )
        ORDER BY p.processo_id, p.data_atualizacao DESC, p.id DESC
        """
    ) or []

    if not rows:
        print("Nenhum plano concluído inválido encontrado.")
        return

    latest_by_processo = {}
    for row in rows:
        proc_id = row["processo_id"]
        if proc_id not in latest_by_processo:
            latest_by_processo[proc_id] = row

    targets = list(latest_by_processo.values())
    print(f"Planos concluídos inválidos encontrados: {len(rows)}")
    print(f"Planos selecionados para reabrir (1 por implantação): {len(targets)}")

    with db_connection() as (conn, db_type):
        cursor = conn.cursor()
        reopened = 0
        relinked = 0

        for target in targets:
            plano_id = target["id"]
            impl_id = target["processo_id"]

            ativo = query_db(
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

            if ativo and ativo.get("id"):
                print(f"{'[dry-run] ' if dry_run else ''}Implantação {impl_id}: já possui ativo {ativo['id']} (skip reabertura)")
                continue

            if dry_run:
                print(f"[dry-run] Reabrir plano inválido {plano_id} da implantação {impl_id}")
                reopened += 1
                continue

            sql_reopen = "UPDATE planos_sucesso SET status = 'em_andamento', data_atualizacao = %s WHERE id = %s"
            if db_type == "sqlite":
                sql_reopen = sql_reopen.replace("%s", "?")
            cursor.execute(sql_reopen, (datetime.now(), plano_id))
            reopened += 1

            impl = query_db("SELECT plano_sucesso_id FROM implantacoes WHERE id = %s", (impl_id,), one=True) or {}
            if not impl.get("plano_sucesso_id"):
                sql_link = "UPDATE implantacoes SET plano_sucesso_id = %s WHERE id = %s"
                if db_type == "sqlite":
                    sql_link = sql_link.replace("%s", "?")
                cursor.execute(sql_link, (plano_id, impl_id))
                relinked += 1

        if dry_run:
            print(f"[dry-run] Reabriria: {reopened}, relink: {relinked}")
        else:
            conn.commit()
            print(f"Reabertos: {reopened}, relinkados: {relinked}")


def main():
    dry_run = "--dry-run" in sys.argv
    app = create_app()
    with app.app_context():
        repair_planos_concluidos_templates(dry_run=dry_run)


if __name__ == "__main__":
    main()
