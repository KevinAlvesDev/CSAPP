import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from project import create_app
from project.db import query_db, execute_db
from project.task_definitions import (
    MODULO_OBRIGATORIO,
    MODULO_PENDENCIAS,
    CHECKLIST_OBRIGATORIO_ITEMS,
    TAREFAS_TREINAMENTO_PADRAO,
)

app = create_app()

def _expected_by_module():
    expected = {}
    expected[MODULO_OBRIGATORIO] = [(name, "Ação interna") for name in CHECKLIST_OBRIGATORIO_ITEMS]
    for modulo, itens in TAREFAS_TREINAMENTO_PADRAO.items():
        expected[modulo] = [(it["nome"], it.get("tag", "")) for it in itens]
    return expected

def sync_implantacao_tasks(impl_id):
    expected = _expected_by_module()
    for modulo, items in expected.items():
        nomes_esperados = [n for n, _ in items]
        existentes = query_db(
            "SELECT id, tarefa_filho, concluida FROM tarefas WHERE implantacao_id = %s AND tarefa_pai = %s ORDER BY ordem",
            (impl_id, modulo),
        ) or []
        nomes_existentes = {t["tarefa_filho"] for t in existentes}
        for t in existentes:
            nome = t["tarefa_filho"]
            if nome not in nomes_esperados and not t.get("concluida"):
                execute_db("DELETE FROM tarefas WHERE id = %s", (t["id"],))
        for i, (nome, tag) in enumerate(items, 1):
            if nome not in nomes_existentes:
                execute_db(
                    "INSERT INTO tarefas (implantacao_id, tarefa_pai, tarefa_filho, ordem, tag) VALUES (%s, %s, %s, %s, %s)",
                    (impl_id, modulo, nome, i, tag),
                )

def seed_hierarquia_from_legacy(impl_id):
    try:
        fase = query_db("SELECT id FROM fases WHERE implantacao_id = %s LIMIT 1", (impl_id,), one=True)
    except Exception:
        fase = None
    if fase:
        return
    grupos_leg = query_db(
        "SELECT DISTINCT tarefa_pai FROM tarefas WHERE implantacao_id = %s AND tarefa_pai NOT IN (%s, %s)",
        (impl_id, MODULO_OBRIGATORIO, MODULO_PENDENCIAS)
    ) or []
    if not grupos_leg:
        return
    execute_db("INSERT INTO fases (implantacao_id, nome, ordem) VALUES (%s, %s, %s)", (impl_id, 'Treinamentos', 1000))
    fase = query_db("SELECT id FROM fases WHERE implantacao_id = %s ORDER BY id DESC LIMIT 1", (impl_id,), one=True)
    fase_id = fase['id']
    for g in grupos_leg:
        nome_grupo = g['tarefa_pai']
        execute_db("INSERT INTO grupos (fase_id, nome) VALUES (%s, %s)", (fase_id, nome_grupo))
        grp = query_db("SELECT id FROM grupos WHERE fase_id = %s AND nome = %s", (fase_id, nome_grupo), one=True)
        gid = grp['id']
        tasks = query_db(
            "SELECT tarefa_filho, concluida, ordem FROM tarefas WHERE implantacao_id = %s AND tarefa_pai = %s ORDER BY ordem",
            (impl_id, nome_grupo)
        ) or []
        for t in tasks:
            status = 'concluida' if t.get('concluida') else 'pendente'
            ordem = t.get('ordem') or 0
            execute_db("INSERT INTO tarefas_h (grupo_id, nome, status, ordem) VALUES (%s, %s, %s, %s)", (gid, t['tarefa_filho'], status, ordem))

if __name__ == "__main__":
    with app.app_context():
        impls = query_db("SELECT id FROM implantacoes", ()) or []
        for row in impls:
            sync_implantacao_tasks(row["id"]) 
            seed_hierarquia_from_legacy(row["id"]) 
        print("Atualização de tarefas concluída.")
