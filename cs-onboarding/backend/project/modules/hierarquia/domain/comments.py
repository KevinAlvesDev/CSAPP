"""
Módulo de Comentários Hierárquicos
Adicionar e listar comentários em tarefas.
Princípio SOLID: Single Responsibility
"""

from ....db import execute_db, query_db


def adicionar_comentario_tarefa(tarefa_h_id, usuario_cs, texto, visibilidade="interno", imagem_url=None):
    """
    Adiciona um comentário a uma tarefa hierárquica.

    Returns:
        dict: Dados do comentário criado ou erro
    """

    tarefa = query_db("SELECT id FROM checklist_items WHERE id = %s AND tipo_item = 'tarefa'", (tarefa_h_id,), one=True)

    if not tarefa:
        return {"ok": False, "error": "Tarefa não encontrada"}

    comentario_id = execute_db(
        """
        INSERT INTO comentarios_h (checklist_item_id, usuario_cs, texto, visibilidade, imagem_url)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id
        """,
        (tarefa_h_id, usuario_cs, texto, visibilidade, imagem_url),
    )

    if not comentario_id:
        execute_db(
            """
            INSERT INTO comentarios_h (checklist_item_id, usuario_cs, texto, visibilidade, imagem_url)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (tarefa_h_id, usuario_cs, texto, visibilidade, imagem_url),
        )
        comentario = query_db(
            "SELECT id FROM comentarios_h WHERE checklist_item_id = %s AND usuario_cs = %s ORDER BY id DESC LIMIT 1",
            (tarefa_h_id, usuario_cs),
            one=True,
        )
        comentario_id = comentario["id"] if comentario else None

    if not comentario_id:
        return {"ok": False, "error": "Erro ao criar comentário"}

    comentario = query_db(
        """
        SELECT id, checklist_item_id, usuario_cs, texto, visibilidade, imagem_url, data_criacao
        FROM comentarios_h
        WHERE id = %s
        """,
        (comentario_id,),
        one=True,
    )

    return {"ok": True, "comentario": comentario}


def get_comentarios_tarefa(tarefa_h_id):
    """
    Retorna todos os comentários de uma tarefa hierárquica.

    Returns:
        list: Lista de comentários
    """

    comentarios = query_db(
        """
        SELECT id, checklist_item_id, usuario_cs, texto, visibilidade, imagem_url, data_criacao
        FROM comentarios_h
        WHERE checklist_item_id = %s
        ORDER BY data_criacao ASC
        """,
        (tarefa_h_id,),
    )

    return comentarios or []
