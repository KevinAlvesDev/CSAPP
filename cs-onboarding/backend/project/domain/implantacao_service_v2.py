"""
Implantação Service Otimizado - Versão COMPLETA sem N+1
Elimina TODOS os loops com queries individuais

IMPORTANTE: Versão alternativa com feature toggle
"""

from collections import OrderedDict
from typing import Any, Dict, List, Tuple

from flask import g

from ...common.utils import format_date_br
from ...constants import MODULO_PENDENCIAS, PERFIS_COM_GESTAO
from ...db import query_db


def get_checklist_tree_complete(impl_id: int) -> Dict[str, Any]:
    """
    Busca TODA a árvore de checklist em UMA ÚNICA QUERY.
    Elimina N+1 de buscar fases -> grupos -> tarefas -> subtarefas.

    Returns:
        {
            'fases': [...],
            'grupos_por_fase': {fase_id: [...]},
            'tarefas_por_grupo': {grupo_id: [...]},
            'subtarefas_por_tarefa': {tarefa_id: [...]}
        }
    """

    # UMA query para buscar TUDO
    all_items = (
        query_db(
            """
        SELECT 
            ci.*,
            -- Contadores de filhos (evita subqueries)
            COUNT(sub.id) as total_filhos,
            SUM(CASE WHEN sub.completed THEN 1 ELSE 0 END) as filhos_concluidos
        FROM checklist_items ci
        LEFT JOIN checklist_items sub ON sub.parent_id = ci.id
        WHERE ci.implantacao_id = %s
        GROUP BY ci.id
        ORDER BY 
            CASE ci.tipo_item
                WHEN 'fase' THEN 1
                WHEN 'grupo' THEN 2
                WHEN 'tarefa' THEN 3
                WHEN 'subtarefa' THEN 4
            END,
            ci.ordem DESC, ci.id
    """,
            (impl_id,),
        )
        or []
    )

    # Organizar em estrutura hierárquica
    fases = []
    grupos_por_fase = {}
    tarefas_por_grupo = {}
    subtarefas_por_tarefa = {}

    for item in all_items:
        tipo = item.get("tipo_item")

        if tipo == "fase":
            fases.append(item)
        elif tipo == "grupo":
            parent_id = item.get("parent_id")
            if parent_id not in grupos_por_fase:
                grupos_por_fase[parent_id] = []
            grupos_por_fase[parent_id].append(item)
        elif tipo == "tarefa":
            parent_id = item.get("parent_id")
            if parent_id not in tarefas_por_grupo:
                tarefas_por_grupo[parent_id] = []
            tarefas_por_grupo[parent_id].append(item)
        elif tipo == "subtarefa":
            parent_id = item.get("parent_id")
            if parent_id not in subtarefas_por_tarefa:
                subtarefas_por_tarefa[parent_id] = []
            subtarefas_por_tarefa[parent_id].append(item)

    return {
        "fases": fases,
        "grupos_por_fase": grupos_por_fase,
        "tarefas_por_grupo": tarefas_por_grupo,
        "subtarefas_por_tarefa": subtarefas_por_tarefa,
    }


def get_comentarios_complete(impl_id: int, is_owner: bool = False, is_manager: bool = False) -> Dict[int, List[Dict]]:
    """
    Busca TODOS os comentários em UMA query.
    Retorna dicionário indexado por checklist_item_id.
    """

    query = """
        SELECT 
            c.*,
            COALESCE(p.nome, c.usuario_cs) as usuario_nome,
            ci.id as checklist_item_id
        FROM comentarios_h c
        INNER JOIN checklist_items ci ON c.checklist_item_id = ci.id
        LEFT JOIN perfil_usuario p ON c.usuario_cs = p.usuario
        WHERE ci.implantacao_id = %s
        ORDER BY c.data_criacao DESC
    """

    comentarios_raw = query_db(query, (impl_id,)) or []

    # Organizar por item_id
    comentarios_map = {}

    for c in comentarios_raw:
        # Filtrar por visibilidade
        if not (is_owner or is_manager):
            if c.get("visibilidade") == "interno":
                continue

        item_id = c.get("checklist_item_id")
        if not item_id:
            continue

        # Formatar
        c_formatado = {
            **c,
            "data_criacao_fmt_d": format_date_br(c.get("data_criacao")),
            "delete_url": f"/api/checklist/comment/{c['id']}",
            "email_url": f"/api/checklist/comment/{c['id']}/email",
        }

        if item_id not in comentarios_map:
            comentarios_map[item_id] = []
        comentarios_map[item_id].append(c_formatado)

    return comentarios_map


def build_tarefas_agrupadas_optimized(
    tree: Dict[str, Any], comentarios_map: Dict[int, List[Dict]]
) -> Tuple[OrderedDict, OrderedDict, OrderedDict, List[str]]:
    """
    Constrói estrutura de tarefas agrupadas SEM queries adicionais.
    Usa apenas os dados já carregados.
    """

    tarefas_agrupadas_treinamento = OrderedDict()
    todos_modulos_temp = set()

    fases = tree["fases"]
    grupos_por_fase = tree["grupos_por_fase"]
    tarefas_por_grupo = tree["tarefas_por_grupo"]
    subtarefas_por_tarefa = tree["subtarefas_por_tarefa"]

    modulo_ordem_map = {}

    for fase in fases:
        fase_id = fase["id"]
        grupos = grupos_por_fase.get(fase_id, [])

        for grupo in grupos:
            grupo_id = grupo["id"]
            modulo_nome = grupo.get("title") or grupo.get("nome") or f"Grupo {grupo_id}"
            todos_modulos_temp.add(modulo_nome)

            tarefas = tarefas_por_grupo.get(grupo_id, [])

            ordem_c = 1
            for tarefa in tarefas:
                tarefa_id = tarefa["id"]
                subtarefas = subtarefas_por_tarefa.get(tarefa_id, [])

                if subtarefas:
                    # Tarefa com subtarefas
                    for sub in subtarefas:
                        comentarios_sub = comentarios_map.get(sub["id"], [])

                        tarefas_agrupadas_treinamento.setdefault(modulo_nome, []).append(
                            {
                                "id": sub["id"],
                                "tarefa_filho": sub.get("title") or sub.get("nome"),
                                "concluida": bool(sub.get("completed")),
                                "tag": sub.get("tag", ""),
                                "ordem": sub.get("ordem", ordem_c),
                                "comentarios": comentarios_sub,
                                "toggle_url": f"/api/checklist/toggle/{sub['id']}",
                                "comment_url": f"/api/checklist/comment/{sub['id']}",
                                "delete_url": f"/api/checklist/delete/{sub['id']}",
                            }
                        )
                        ordem_c += 1
                else:
                    # Tarefa sem subtarefas
                    comentarios_th = comentarios_map.get(tarefa_id, [])

                    tarefas_agrupadas_treinamento.setdefault(modulo_nome, []).append(
                        {
                            "id": tarefa_id,
                            "tarefa_filho": tarefa.get("title") or tarefa.get("nome"),
                            "concluida": bool(tarefa.get("completed", False)),
                            "tag": "",
                            "ordem": tarefa.get("ordem", ordem_c),
                            "comentarios": comentarios_th,
                            "toggle_url": f"/api/checklist/toggle/{tarefa_id}",
                            "comment_url": f"/api/checklist/comment/{tarefa_id}",
                            "delete_url": f"/api/checklist/delete/{tarefa_id}",
                        }
                    )
                    ordem_c += 1

            # Ordenar tarefas do módulo
            if modulo_nome in tarefas_agrupadas_treinamento:
                tarefas_agrupadas_treinamento[modulo_nome].sort(key=lambda x: x.get("ordem", 0))

                # Guardar ordem mínima do módulo
                try:
                    modulo_ordem_map[modulo_nome] = min(
                        [t.get("ordem", 0) for t in tarefas_agrupadas_treinamento[modulo_nome]]
                    )
                except:
                    modulo_ordem_map[modulo_nome] = 0

    # Ordenar módulos
    ordered_treinamento = OrderedDict()
    for modulo in sorted(modulo_ordem_map.keys(), key=lambda m: (modulo_ordem_map.get(m, 0), m), reverse=True):
        ordered_treinamento[modulo] = tarefas_agrupadas_treinamento.get(modulo, [])

    # Lista de módulos
    todos_modulos_lista = sorted(list(todos_modulos_temp), key=lambda m: modulo_ordem_map.get(m, 0), reverse=True)
    if MODULO_PENDENCIAS not in todos_modulos_lista:
        todos_modulos_lista.append(MODULO_PENDENCIAS)

    # Retornar (obrigatório vazio, treinamento, pendências vazio, lista)
    return OrderedDict(), ordered_treinamento, OrderedDict(), todos_modulos_lista


def get_implantacao_details_v2(impl_id: int, usuario_cs_email: str, user_perfil: Dict) -> Dict[str, Any]:
    """
    Versão COMPLETA otimizada de get_implantacao_details.

    ANTES: 50-100+ queries
    DEPOIS: 5-10 queries

    Elimina TODOS os N+1:
    - Busca checklist completo em 1 query
    - Busca comentários em 1 query
    - Constrói estrutura sem queries adicionais
    """

    from ...config.logging_config import get_logger

    logger = get_logger("implantacao")

    if user_perfil is None:
        user_perfil = {}

    # Validar acesso
    user_perfil_acesso = user_perfil.get("perfil_acesso")
    implantacao = query_db("SELECT * FROM implantacoes WHERE id = %s", (impl_id,), one=True)

    if not implantacao:
        raise ValueError("Implantação não encontrada.")

    is_owner = implantacao.get("usuario_cs") == usuario_cs_email
    is_manager = user_perfil_acesso in PERFIS_COM_GESTAO

    if not is_owner and not is_manager:
        if implantacao.get("status") == "nova":
            raise ValueError("Esta implantação ainda não foi iniciada.")
        else:
            raise ValueError("Implantação não encontrada ou não pertence a você.")

    if implantacao.get("status") == "nova" and is_owner and not is_manager:
        raise ValueError("Esta implantação está aguardando início.")

    # Formatar datas
    from .implantacao.details import _format_implantacao_dates

    implantacao = _format_implantacao_dates(implantacao)

    # Buscar TUDO em queries otimizadas
    tree = get_checklist_tree_complete(impl_id)
    comentarios_map = get_comentarios_complete(impl_id, is_owner, is_manager)

    # Construir estrutura SEM queries adicionais
    (tarefas_agrupadas_obrigatorio, ordered_treinamento, tarefas_agrupadas_pendencias, todos_modulos_lista) = (
        build_tarefas_agrupadas_optimized(tree, comentarios_map)
    )

    # Calcular progresso (já otimizado em outro módulo)
    from .implantacao.progress import _get_progress

    progresso, _, _ = _get_progress(impl_id)

    # Timeline
    from .implantacao.details import _get_timeline_logs

    logs_timeline = _get_timeline_logs(impl_id)

    # Hierarquia
    from ..hierarquia_service import get_hierarquia_implantacao

    try:
        hierarquia = get_hierarquia_implantacao(impl_id)
    except Exception as e:
        logger.warning(f"Erro ao carregar hierarquia: {e}")
        hierarquia = {"fases": []}

    # CS users
    all_cs_users = (
        query_db(
            "SELECT usuario, nome FROM perfil_usuario WHERE perfil_acesso IS NOT NULL AND perfil_acesso != '' ORDER BY nome"
        )
        or []
    )

    # Plano de sucesso
    plano_sucesso_info = None
    if implantacao.get("plano_sucesso_id"):
        plano_sucesso_info = query_db(
            "SELECT * FROM planos_sucesso WHERE id = %s", (implantacao["plano_sucesso_id"],), one=True
        )

    # Checklist nested
    checklist_nested = None
    try:
        from ..checklist_service import build_nested_tree, get_checklist_tree

        checklist_flat = get_checklist_tree(implantacao_id=impl_id, include_progress=True)
        if checklist_flat:
            checklist_nested = build_nested_tree(checklist_flat)
    except Exception as e:
        logger.warning(f"Erro ao carregar checklist: {e}")
        checklist_nested = []

    # User info
    try:
        user_info = getattr(g, "user", None) or {
            "email": usuario_cs_email,
            "nome": user_perfil.get("nome", usuario_cs_email),
        }
    except:
        user_info = {"email": usuario_cs_email, "nome": user_perfil.get("nome", usuario_cs_email)}

    # Importar constantes
    from ...constants import (
        CARGOS_RESPONSAVEL,
        FORMAS_PAGAMENTO,
        HORARIOS_FUNCIONAMENTO,
        JUSTIFICATIVAS_PARADA,
        MODALIDADES_LIST,
        NIVEIS_RECEITA,
        RECORRENCIA_USADA,
        SEGUIMENTOS_LIST,
        SIM_NAO_OPTIONS,
        SISTEMAS_ANTERIORES,
        TIPOS_PLANOS,
    )
    from ..task_definitions import TASK_TIPS

    return {
        "user_info": user_info,
        "implantacao": implantacao,
        "hierarquia": hierarquia,
        "tarefas_agrupadas_obrigatorio": tarefas_agrupadas_obrigatorio,
        "tarefas_agrupadas_treinamento": ordered_treinamento,
        "tarefas_agrupadas_pendencias": tarefas_agrupadas_pendencias,
        "todos_modulos": todos_modulos_lista,
        "modulo_pendencias_nome": MODULO_PENDENCIAS,
        "progresso_porcentagem": progresso,
        "nome_usuario_logado": user_perfil.get("nome", usuario_cs_email),
        "email_usuario_logado": usuario_cs_email,
        "justificativas_parada": JUSTIFICATIVAS_PARADA,
        "logs_timeline": logs_timeline,
        "cargos_responsavel": CARGOS_RESPONSAVEL,
        "NIVEIS_RECEITA": NIVEIS_RECEITA,
        "SEGUIMENTOS_LIST": SEGUIMENTOS_LIST,
        "TIPOS_PLANOS": TIPOS_PLANOS,
        "MODALIDADES_LIST": MODALIDADES_LIST,
        "HORARIOS_FUNCIONAMENTO": HORARIOS_FUNCIONAMENTO,
        "FORMAS_PAGAMENTO": FORMAS_PAGAMENTO,
        "SISTEMAS_ANTERIORES": SISTEMAS_ANTERIORES,
        "RECORRENCIA_USADA": RECORRENCIA_USADA,
        "SIM_NAO_OPTIONS": SIM_NAO_OPTIONS,
        "all_cs_users": all_cs_users,
        "is_manager": is_manager,
        "tt": TASK_TIPS,
        "plano_sucesso": plano_sucesso_info,
        "checklist_tree": checklist_nested,
    }
