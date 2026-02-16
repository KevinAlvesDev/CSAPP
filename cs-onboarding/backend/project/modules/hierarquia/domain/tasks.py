"""
Módulo de Tarefas Hierárquicas
Toggle de subtarefas e cálculo de progresso.
Princípio SOLID: Single Responsibility
"""

from datetime import datetime

from ....config.logging_config import get_logger
from ....db import execute_db, query_db

logger = get_logger("hierarquia_tasks")


def toggle_subtarefa(subtarefa_id):
    """
    Alterna o estado de conclusão de uma subtarefa.
    Atualiza o percentual de conclusão da tarefa pai.
    Agora usa checklist_items (estrutura consolidada).

    Returns:
        dict: {'ok': bool, 'concluido': bool, 'percentual_tarefa': int}
    """

    subtarefa = query_db(
        "SELECT id, parent_id, completed FROM checklist_items WHERE id = %s AND tipo_item = 'subtarefa'",
        (subtarefa_id,),
        one=True,
    )

    if not subtarefa:
        return {"ok": False, "error": "Subtarefa não encontrada"}

    novo_estado = not subtarefa.get("completed", False)
    tarefa_id = subtarefa.get("parent_id")

    if not tarefa_id:
        return {"ok": False, "error": "Tarefa pai não encontrada"}

    if novo_estado:
        execute_db(
            "UPDATE checklist_items SET completed = %s, data_conclusao = %s WHERE id = %s",
            (True, datetime.now(), subtarefa_id),
        )
    else:
        execute_db(
            "UPDATE checklist_items SET completed = %s, data_conclusao = NULL WHERE id = %s", (False, subtarefa_id)
        )

    stats = query_db(
        """
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN completed = true THEN 1 ELSE 0 END) as concluidas
        FROM checklist_items
        WHERE parent_id = %s AND tipo_item = 'subtarefa'
        """,
        (tarefa_id,),
        one=True,
    )

    percentual = int(stats["concluidas"] / stats["total"] * 100) if stats and stats["total"] > 0 else 0

    novo_status = "concluida" if percentual == 100 else ("em_andamento" if percentual > 0 else "pendente")

    execute_db(
        "UPDATE checklist_items SET percentual_conclusao = %s, status = %s, completed = %s WHERE id = %s",
        (percentual, novo_status, percentual == 100, tarefa_id),
    )

    # Registrar atividade na timeline
    try:
        from ....db import logar_timeline

        # Buscar implantacao_id da tarefa
        tarefa_info = query_db(
            "SELECT implantacao_id, title FROM checklist_items WHERE id = %s", (tarefa_id,), one=True
        )
        if tarefa_info:
            from flask import g

            usuario = g.get("user_email", "sistema")
            acao = "concluiu" if novo_estado else "reabriu"
            logar_timeline(
                tarefa_info["implantacao_id"],
                usuario,
                "tarefa_atualizada",
                f'{acao.capitalize()} subtarefa em "{tarefa_info["title"]}"',
            )
    except Exception as e:
        logger.warning(f"Erro ao registrar timeline: {e}")

    return {"ok": True, "concluido": novo_estado, "percentual_tarefa": percentual, "status_tarefa": novo_status}


def calcular_progresso_implantacao(implantacao_id):
    """
    Calcula o progresso geral da implantação baseado nas subtarefas.
    Agora usa checklist_items (estrutura consolidada).

    Returns:
        int: Percentual de 0 a 100
    """

    stats = query_db(
        """
        SELECT
            COUNT(*) as total_subtarefas,
            SUM(CASE WHEN completed = true THEN 1 ELSE 0 END) as subtarefas_concluidas
        FROM checklist_items
        WHERE implantacao_id = %s AND tipo_item = 'subtarefa'
        """,
        (implantacao_id,),
        one=True,
    )

    if not stats or not stats["total_subtarefas"] or stats["total_subtarefas"] == 0:
        return 0

    percentual = int((stats["subtarefas_concluidas"] / stats["total_subtarefas"]) * 100)
    return percentual
