from datetime import datetime

from ..config.logging_config import get_logger
from ..db import execute_db, query_db

logger = get_logger('hierarquia_service')


def get_hierarquia_implantacao(implantacao_id):
    """
    Retorna a estrutura hierárquica completa de uma implantação.
    Agora usa checklist_items (estrutura consolidada).

    Returns:
        dict: {
            'fases': [
                {
                    'id': int,
                    'nome': str,
                    'ordem': int,
                    'grupos': [
                        {
                            'id': int,
                            'nome': str,
                            'tarefas': [
                                {
                                    'id': int,
                                    'nome': str,
                                    'status': str,
                                    'percentual_conclusao': int,
                                    'ordem': int,
                                    'subtarefas': [
                                        {
                                            'id': int,
                                            'nome': str,
                                            'concluido': bool,
                                            'ordem': int
                                        }
                                    ]
                                }
                            ]
                        }
                    ]
                }
            ]
        }
    """

    try:
        items = query_db(
            """
            SELECT id, parent_id, title, completed, comment, level, ordem, tipo_item, 
                   status, percentual_conclusao, responsavel, tag, data_conclusao, descricao
            FROM checklist_items 
            WHERE implantacao_id = %s
            ORDER BY ordem, id
            """,
            (implantacao_id,)
        )
    except Exception as e:
        logger.error(f"[GET_HIERARQUIA] Erro ao buscar itens: {e}")
        return {'fases': []}

    if not items:
        return {'fases': []}

    items_map = {item['id']: item for item in items}

    fases_items = [item for item in items if item['tipo_item'] == 'fase' and item['parent_id'] is None]
    grupos_items = {}
    tarefas_items = {}
    subtarefas_items = {}

    for item in items:
        parent_id = item.get('parent_id')
        tipo = item.get('tipo_item', '')

        if tipo == 'grupo' and parent_id:
            if parent_id not in grupos_items:
                grupos_items[parent_id] = []
            grupos_items[parent_id].append(item)
        elif tipo == 'tarefa' and parent_id:
            if parent_id not in tarefas_items:
                tarefas_items[parent_id] = []
            tarefas_items[parent_id].append(item)
        elif tipo == 'subtarefa' and parent_id:
            if parent_id not in subtarefas_items:
                subtarefas_items[parent_id] = []
            subtarefas_items[parent_id].append(item)

    resultado = {'fases': []}

    for fase_item in sorted(fases_items, key=lambda x: x.get('ordem', 0)):
        fase_dict = {
            'id': fase_item['id'],
            'nome': fase_item['title'],
            'ordem': fase_item.get('ordem', 0),
            'responsavel': fase_item.get('responsavel'),
            'grupos': []
        }

        grupos_fase = sorted(grupos_items.get(fase_item['id'], []), key=lambda x: x.get('ordem', 0))

        for grupo_item in grupos_fase:
            grupo_dict = {
                'id': grupo_item['id'],
                'nome': grupo_item['title'],
                'responsavel': grupo_item.get('responsavel'),
                'tarefas': []
            }

            tarefas_grupo = sorted(tarefas_items.get(grupo_item['id'], []), key=lambda x: x.get('ordem', 0))

            for tarefa_item in tarefas_grupo:
                status_raw = tarefa_item.get('status') or 'pendente'
                status_normalizado = str(status_raw).lower().strip()

                if status_normalizado == 'concluida' or status_normalizado == 'concluido' or 'conclui' in status_normalizado:
                    status_normalizado = 'concluida'
                else:
                    status_normalizado = 'pendente'

                tarefa_dict = {
                    'id': tarefa_item['id'],
                    'nome': tarefa_item['title'],
                    'status': status_normalizado,
                    'percentual_conclusao': tarefa_item.get('percentual_conclusao', 0),
                    'ordem': tarefa_item.get('ordem', 0),
                    'responsavel': tarefa_item.get('responsavel'),
                    'subtarefas': []
                }

                subtarefas_tarefa = sorted(subtarefas_items.get(tarefa_item['id'], []), key=lambda x: x.get('ordem', 0))

                for subtarefa_item in subtarefas_tarefa:
                    subtarefa_dict = {
                        'id': subtarefa_item['id'],
                        'nome': subtarefa_item['title'],
                        'concluido': subtarefa_item.get('completed', False),
                        'ordem': subtarefa_item.get('ordem', 0),
                        'responsavel': subtarefa_item.get('responsavel')
                    }
                    if subtarefa_item.get('tag'):
                        subtarefa_dict['tag'] = subtarefa_item.get('tag')
                    if subtarefa_item.get('data_conclusao'):
                        subtarefa_dict['data_conclusao'] = subtarefa_item.get('data_conclusao')

                    tarefa_dict['subtarefas'].append(subtarefa_dict)

                grupo_dict['tarefas'].append(tarefa_dict)

            fase_dict['grupos'].append(grupo_dict)

        resultado['fases'].append(fase_dict)

    return resultado


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
        one=True
    )

    if not subtarefa:
        return {'ok': False, 'error': 'Subtarefa não encontrada'}

    novo_estado = not subtarefa.get('completed', False)
    tarefa_id = subtarefa.get('parent_id')

    if not tarefa_id:
        return {'ok': False, 'error': 'Tarefa pai não encontrada'}

    if novo_estado:
        execute_db(
            "UPDATE checklist_items SET completed = %s, data_conclusao = %s WHERE id = %s",
            (True, datetime.now(), subtarefa_id)
        )
    else:
        execute_db(
            "UPDATE checklist_items SET completed = %s, data_conclusao = NULL WHERE id = %s",
            (False, subtarefa_id)
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
        one=True
    )

    if stats and stats['total'] > 0:
        percentual = int((stats['concluidas'] / stats['total']) * 100)
    else:
        percentual = 0

    novo_status = 'concluida' if percentual == 100 else ('em_andamento' if percentual > 0 else 'pendente')

    execute_db(
        "UPDATE checklist_items SET percentual_conclusao = %s, status = %s, completed = %s WHERE id = %s",
        (percentual, novo_status, percentual == 100, tarefa_id)
    )

    return {
        'ok': True,
        'concluido': novo_estado,
        'percentual_tarefa': percentual,
        'status_tarefa': novo_status
    }


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
        one=True
    )

    if not stats or not stats['total_subtarefas'] or stats['total_subtarefas'] == 0:
        return 0

    percentual = int((stats['subtarefas_concluidas'] / stats['total_subtarefas']) * 100)
    return percentual


def adicionar_comentario_tarefa(tarefa_h_id, usuario_cs, texto, visibilidade='interno', imagem_url=None):
    """
    Adiciona um comentário a uma tarefa hierárquica.

    Returns:
        dict: Dados do comentário criado ou erro
    """

    tarefa = query_db(
        "SELECT id FROM checklist_items WHERE id = %s AND tipo_item = 'tarefa'",
        (tarefa_h_id,),
        one=True
    )

    if not tarefa:
        return {'ok': False, 'error': 'Tarefa não encontrada'}

    comentario_id = execute_db(
        """
        INSERT INTO comentarios_h (checklist_item_id, usuario_cs, texto, visibilidade, imagem_url)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id
        """,
        (tarefa_h_id, usuario_cs, texto, visibilidade, imagem_url)
    )

    if not comentario_id:
        execute_db(
            """
            INSERT INTO comentarios_h (checklist_item_id, usuario_cs, texto, visibilidade, imagem_url)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (tarefa_h_id, usuario_cs, texto, visibilidade, imagem_url)
        )
        comentario = query_db(
            "SELECT id FROM comentarios_h WHERE checklist_item_id = %s AND usuario_cs = %s ORDER BY id DESC LIMIT 1",
            (tarefa_h_id, usuario_cs),
            one=True
        )
        comentario_id = comentario['id'] if comentario else None

    if not comentario_id:
        return {'ok': False, 'error': 'Erro ao criar comentário'}

    comentario = query_db(
        """
        SELECT id, checklist_item_id, usuario_cs, texto, visibilidade, imagem_url, data_criacao
        FROM comentarios_h
        WHERE id = %s
        """,
        (comentario_id,),
        one=True
    )

    return {'ok': True, 'comentario': comentario}


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
        (tarefa_h_id,)
    )

    return comentarios or []
