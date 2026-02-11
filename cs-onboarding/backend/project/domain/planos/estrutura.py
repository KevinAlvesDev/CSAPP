"""
Módulo de Estrutura de Planos
Criação e atualização da estrutura hierárquica de planos.
Princípio SOLID: Single Responsibility
"""

from flask import current_app

from ...common.exceptions import DatabaseError, ValidationError
from ...db import db_connection
from .validacao import validar_estrutura_checklist


def atualizar_estrutura_plano(plano_id: int, estrutura: dict) -> bool:
    """
    Atualiza a estrutura do plano (itens) removendo os antigos e criando os novos.
    """
    if not plano_id:
        raise ValidationError("ID do plano é obrigatório")

    if not estrutura:
        raise ValidationError("Estrutura é obrigatória")

    validar_estrutura_checklist(estrutura)

    with db_connection() as (conn, db_type):
        cursor = conn.cursor()
        try:
            sql_delete = "DELETE FROM checklist_items WHERE plano_id = %s"
            if db_type == "sqlite":
                sql_delete = sql_delete.replace("%s", "?")
            cursor.execute(sql_delete, (plano_id,))

            _criar_estrutura_plano_checklist(cursor, db_type, plano_id, estrutura)

            conn.commit()
            current_app.logger.info(f"Estrutura do plano {plano_id} atualizada com sucesso")
            return True
        except Exception as e:
            conn.rollback()
            current_app.logger.error(f"Erro ao atualizar estrutura do plano {plano_id}: {e}", exc_info=True)
            raise DatabaseError(f"Erro ao atualizar estrutura do plano: {e}") from e


def _criar_estrutura_plano(cursor, db_type: str, plano_id: int, estrutura: dict):
    """
    Cria estrutura do plano usando checklist_items (consolidado).
    """
    fases = estrutura.get("fases", [])

    for fase_data in fases:
        sql_fase = """
            INSERT INTO checklist_items
            (parent_id, title, completed, comment, level, ordem, plano_id, tipo_item, descricao, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """
        if db_type == "sqlite":
            sql_fase = sql_fase.replace("%s", "?")

        cursor.execute(
            sql_fase,
            (
                None,  # parent_id (fase é raiz)
                fase_data["nome"],
                False,  # completed
                fase_data.get("descricao", ""),  # comment
                0,  # level (fase é nível 0)
                fase_data.get("ordem", 0),
                plano_id,
                "plano_fase",  # tipo_item
                fase_data.get("descricao", ""),  # descricao
            ),
        )

        if db_type == "postgres":
            cursor.execute("SELECT lastval()")
            fase_id = cursor.fetchone()[0]
        else:
            fase_id = cursor.lastrowid

        grupos = fase_data.get("grupos", [])
        for grupo_data in grupos:
            sql_grupo = """
                INSERT INTO checklist_items
                (parent_id, title, completed, comment, level, ordem, plano_id, tipo_item, descricao, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """
            if db_type == "sqlite":
                sql_grupo = sql_grupo.replace("%s", "?")

            cursor.execute(
                sql_grupo,
                (
                    fase_id,  # parent_id (grupo pertence à fase)
                    grupo_data["nome"],
                    False,  # completed
                    grupo_data.get("descricao", ""),  # comment
                    1,  # level (grupo é nível 1)
                    grupo_data.get("ordem", 0),
                    plano_id,
                    "plano_grupo",  # tipo_item
                    grupo_data.get("descricao", ""),  # descricao
                ),
            )

            if db_type == "postgres":
                cursor.execute("SELECT lastval()")
                grupo_id = cursor.fetchone()[0]
            else:
                grupo_id = cursor.lastrowid

            tarefas = grupo_data.get("tarefas", [])
            for tarefa_data in tarefas:
                sql_tarefa = """
                    INSERT INTO checklist_items
                    (parent_id, title, completed, comment, level, ordem, plano_id, tipo_item, descricao, obrigatoria, status, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """
                if db_type == "sqlite":
                    sql_tarefa = sql_tarefa.replace("%s", "?")

                cursor.execute(
                    sql_tarefa,
                    (
                        grupo_id,  # parent_id (tarefa pertence ao grupo)
                        tarefa_data["nome"],
                        False,  # completed
                        tarefa_data.get("descricao", ""),  # comment
                        2,  # level (tarefa é nível 2)
                        tarefa_data.get("ordem", 0),
                        plano_id,
                        "plano_tarefa",  # tipo_item
                        tarefa_data.get("descricao", ""),  # descricao
                        tarefa_data.get("obrigatoria", False),  # obrigatoria
                        "pendente",  # status padrão
                    ),
                )

                if db_type == "postgres":
                    cursor.execute("SELECT lastval()")
                    tarefa_id = cursor.fetchone()[0]
                else:
                    tarefa_id = cursor.lastrowid

                subtarefas = tarefa_data.get("subtarefas", [])
                for subtarefa_data in subtarefas:
                    sql_subtarefa = """
                        INSERT INTO checklist_items
                        (parent_id, title, completed, comment, level, ordem, plano_id, tipo_item, descricao, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """
                    if db_type == "sqlite":
                        sql_subtarefa = sql_subtarefa.replace("%s", "?")

                    cursor.execute(
                        sql_subtarefa,
                        (
                            tarefa_id,  # parent_id (subtarefa pertence à tarefa)
                            subtarefa_data["nome"],
                            False,  # completed
                            subtarefa_data.get("descricao", ""),  # comment
                            3,  # level (subtarefa é nível 3)
                            subtarefa_data.get("ordem", 0),
                            plano_id,
                            "plano_subtarefa",  # tipo_item
                            subtarefa_data.get("descricao", ""),  # descricao
                        ),
                    )


def _criar_estrutura_plano_checklist(cursor, db_type: str, plano_id: int, estrutura: dict):
    """
    Cria a estrutura do plano na tabela checklist_items.
    Usa campo 'plano_id' para vincular itens ao plano.
    Usa campo 'implantacao_id' como NULL (é um plano, não uma implantação).
    """
    if "items" in estrutura:
        _criar_items_recursivo(cursor, db_type, plano_id, estrutura["items"], None, 0)
    else:
        fases = estrutura.get("fases", [])
        parent_map = {}
        ordem_global = 0

        for fase_data in fases:
            ordem_global += 1
            sql_item = """
                INSERT INTO checklist_items (parent_id, title, completed, comment, level, ordem, implantacao_id, plano_id, obrigatoria)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            if db_type == "sqlite":
                sql_item = sql_item.replace("%s", "?")

            cursor.execute(
                sql_item,
                (
                    None,
                    fase_data["nome"],
                    False,
                    fase_data.get("descricao", ""),
                    0,
                    fase_data.get("ordem", ordem_global),
                    None,
                    plano_id,
                    fase_data.get("obrigatoria", False),
                ),
            )

            if db_type == "postgres":
                cursor.execute("SELECT lastval()")
                fase_id = cursor.fetchone()[0]
            else:
                fase_id = cursor.lastrowid

            parent_map["fase_" + str(fase_data.get("ordem", ordem_global))] = fase_id

            grupos = fase_data.get("grupos", [])
            for grupo_data in grupos:
                ordem_global += 1
                cursor.execute(
                    sql_item,
                    (
                        fase_id,
                        grupo_data["nome"],
                        False,
                        grupo_data.get("descricao", ""),
                        1,
                        grupo_data.get("ordem", ordem_global),
                        None,
                        plano_id,
                        grupo_data.get("obrigatoria", False),
                    ),
                )

                if db_type == "postgres":
                    cursor.execute("SELECT lastval()")
                    grupo_id = cursor.fetchone()[0]
                else:
                    grupo_id = cursor.lastrowid

                tarefas = grupo_data.get("tarefas", [])
                for tarefa_data in tarefas:
                    ordem_global += 1
                    cursor.execute(
                        sql_item,
                        (
                            grupo_id,
                            tarefa_data["nome"],
                            False,
                            tarefa_data.get("descricao", ""),
                            2,
                            tarefa_data.get("ordem", ordem_global),
                            None,
                            plano_id,
                            tarefa_data.get("obrigatoria", False),
                        ),
                    )

                    if db_type == "postgres":
                        cursor.execute("SELECT lastval()")
                        tarefa_id = cursor.fetchone()[0]
                    else:
                        tarefa_id = cursor.lastrowid

                    subtarefas = tarefa_data.get("subtarefas", [])
                    for subtarefa_data in subtarefas:
                        ordem_global += 1
                        cursor.execute(
                            sql_item,
                            (
                                tarefa_id,
                                subtarefa_data["nome"],
                                False,
                                subtarefa_data.get("descricao", ""),
                                3,
                                subtarefa_data.get("ordem", ordem_global),
                                None,
                                plano_id,
                                subtarefa_data.get("obrigatoria", False),
                            ),
                        )


def _criar_items_recursivo(
    cursor, db_type: str, plano_id: int, items: list[dict], parent_id: int | None, current_level: int
):
    """
    Cria itens recursivamente para suportar hierarquia infinita.
    """
    ordem = 0
    for item_data in items:
        ordem += 1
        tipo_item = item_data.get("tipo_item")
        if not tipo_item:
            if current_level == 0:
                tipo_item = "plano_fase"
            elif current_level == 1:
                tipo_item = "plano_grupo"
            elif current_level == 2:
                tipo_item = "plano_tarefa"
            else:
                tipo_item = "plano_subtarefa"

        sql_item = """
            INSERT INTO checklist_items (parent_id, title, completed, comment, level, ordem, implantacao_id, plano_id, obrigatoria, tipo_item, tag)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        if db_type == "sqlite":
            sql_item = sql_item.replace("%s", "?")

        cursor.execute(
            sql_item,
            (
                parent_id,
                item_data.get("title", item_data.get("nome", "")),
                False,
                item_data.get("comment", item_data.get("descricao", "")),
                item_data.get("level", current_level),
                item_data.get("ordem", ordem),
                None,
                plano_id,
                item_data.get("obrigatoria", False),
                tipo_item,
                item_data.get("tag"),
            ),
        )

        if db_type == "postgres":
            cursor.execute("SELECT lastval()")
            item_id = cursor.fetchone()[0]
        else:
            item_id = cursor.lastrowid

        children = item_data.get("children", [])
        if children:
            _criar_items_recursivo(cursor, db_type, plano_id, children, item_id, current_level + 1)


def converter_estrutura_editor_para_checklist(estrutura_editor: dict) -> list[dict]:
    """
    Converte estrutura do editor (fases/grupos OU items aninhados) para formato plano de checklist_items.
    Retorna lista plana com parent_id, level, ordem.
    """
    resultado = []

    if "items" in estrutura_editor:
        items = estrutura_editor["items"]
        _converter_items_para_plano(items, None, 0, 0, resultado)
    elif "fases" in estrutura_editor:
        fases = estrutura_editor["fases"]
        ordem_global = 0

        for fase in fases:
            ordem_global += 1
            fase_item = {
                "title": fase.get("nome", ""),
                "comment": fase.get("descricao", ""),
                "level": 0,
                "ordem": fase.get("ordem", ordem_global),
                "parent_id": None,
            }
            resultado.append(fase_item)

            grupos = fase.get("grupos", [])
            for grupo in grupos:
                ordem_global += 1
                grupo_item = {
                    "title": grupo.get("nome", ""),
                    "comment": grupo.get("descricao", ""),
                    "level": 1,
                    "ordem": grupo.get("ordem", ordem_global),
                    "parent_id": fase_item.get("temp_id"),
                }
                resultado.append(grupo_item)

                tarefas = grupo.get("tarefas", [])
                for tarefa in tarefas:
                    ordem_global += 1
                    tarefa_item = {
                        "title": tarefa.get("nome", ""),
                        "comment": tarefa.get("descricao", ""),
                        "level": 2,
                        "ordem": tarefa.get("ordem", ordem_global),
                        "parent_id": grupo_item.get("temp_id"),
                    }
                    resultado.append(tarefa_item)

                    subtarefas = tarefa.get("subtarefas", [])
                    for subtarefa in subtarefas:
                        ordem_global += 1
                        subtarefa_item = {
                            "title": subtarefa.get("nome", ""),
                            "comment": subtarefa.get("descricao", ""),
                            "level": 3,
                            "ordem": subtarefa.get("ordem", ordem_global),
                            "parent_id": tarefa_item.get("temp_id"),
                        }
                        resultado.append(subtarefa_item)
    else:
        raise ValidationError("Estrutura deve conter 'items' ou 'fases'")

    return resultado


def _converter_items_para_plano(
    items: list[dict], parent_id: int | None, current_level: int, ordem_start: int, resultado: list[dict]
):
    """
    Converte items aninhados para formato plano recursivamente.
    """
    ordem = ordem_start
    for item in items:
        ordem += 1
        item_plano = {
            "title": item.get("title", item.get("nome", "")),
            "comment": item.get("comment", item.get("descricao", "")),
            "level": item.get("level", current_level),
            "ordem": item.get("ordem", ordem),
            "parent_id": parent_id,
            "obrigatoria": item.get("obrigatoria", False),
            "tag": item.get("tag"),
            "children": [],
        }
        resultado.append(item_plano)

        children = item.get("children", [])
        if children:
            _converter_items_para_plano(children, None, current_level + 1, ordem, resultado)
