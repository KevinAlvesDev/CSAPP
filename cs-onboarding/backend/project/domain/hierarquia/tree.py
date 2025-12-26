"""
Módulo de Árvore Hierárquica
Estrutura hierárquica completa da implantação.
Princípio SOLID: Single Responsibility
"""
from ...config.logging_config import get_logger
from ...db import query_db

logger = get_logger('hierarquia_tree')


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
