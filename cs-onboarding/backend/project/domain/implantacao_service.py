"""
Serviço de Implantação - Módulo Principal.

Este módulo coordena operações de implantação, delegando para submódulos:
- crud: Operações CRUD básicas
- details: Formatação e detalhes
- listing: Listagem e busca
- status: Transições de status
- progress: Cálculo de progresso
- oamd_integration: Integração com sistema externo
"""

from __future__ import annotations

from collections import OrderedDict
from typing import Any

from flask import g

from ..common.utils import format_date_br
from ..constants import (
    CARGOS_RESPONSAVEL,
    FORMAS_PAGAMENTO,
    HORARIOS_FUNCIONAMENTO,
    JUSTIFICATIVAS_PARADA,
    MODALIDADES_LIST,
    NIVEIS_RECEITA,
    PERFIS_COM_GESTAO,
    RECORRENCIA_USADA,
    SEGUIMENTOS_LIST,
    SIM_NAO_OPTIONS,
    SISTEMAS_ANTERIORES,
    TIPOS_PLANOS,
)
from ..db import execute_db, logar_timeline, query_db
from ..domain.hierarquia_service import get_hierarquia_implantacao
from ..domain.task_definitions import MODULO_OBRIGATORIO, MODULO_PENDENCIAS, TASK_TIPS

# Type aliases para melhor legibilidade
ImplantacaoDict = dict[str, Any]
UserProfile = dict[str, Any]
TimelineLog = dict[str, Any]

# ============================================================================
# REFATORAÇÃO SOLID - Importações do novo módulo de CRUD
# ============================================================================
# ============================================================================
# REFATORAÇÃO SOLID - Importações do novo módulo de detalhes
# ============================================================================
import contextlib

from .implantacao.details import (
    _format_implantacao_dates,
    _get_timeline_logs,
)

# ============================================================================
# REFATORAÇÃO SOLID - Importações do novo módulo de listagem
# ============================================================================
# ============================================================================
# REFATORAÇÃO SOLID - Importações do novo módulo de integração OAMD
# ============================================================================
# ============================================================================
# REFATORAÇÃO SOLID - Importações do novo módulo de progresso
# ============================================================================
from .implantacao.progress import (
    _get_progress,
)

# ============================================================================
# REFATORAÇÃO SOLID - Importações do novo módulo de status
# ============================================================================

try:
    from ..config.cache_config import cache
except ImportError:
    cache = None


# ============================================================================
# INÍCIO DAS FUNÇÕES QUE PERMANECEM NESTE ARQUIVO
# (Serão movidas em etapas futuras)
# ============================================================================


# Auto-finalização removida a pedido do usuário
def auto_finalizar_implantacao(impl_id: int, usuario_cs_email: str) -> tuple[bool, TimelineLog | None]:
    """
    Função desativada. Finalizações agora devem ser manuais.
    """
    return False, None


def _get_implantacao_and_validate_access(
    impl_id: int, usuario_cs_email: str, user_perfil: UserProfile | None
) -> tuple[ImplantacaoDict, bool]:
    user_perfil_acesso = user_perfil.get("perfil_acesso") if user_perfil else None
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

    # Regra removida: permitir acesso a detalhes mesmo sem iniciar a implantação
    # (anteriormente bloqueava implantações com status "nova" para o dono)

    return implantacao, is_manager


def _get_comentarios_bulk(
    impl_id: int, is_owner: bool = False, is_manager: bool = False
) -> dict[str, list[dict[str, Any]]]:
    """
    Busca TODOS os comentários de uma implantação em uma única query (ou poucas queries).
    Retorna dicionário indexado por item_id para acesso rápido.
    """
    comentarios_map = {}

    try:
        comentarios_h_raw = (
            query_db(
                """
            SELECT c.*,
                   COALESCE(p.nome, c.usuario_cs) as usuario_nome,
                   c.data_criacao as data_criacao_raw,
                   c.checklist_item_id
            FROM comentarios_h c
            LEFT JOIN perfil_usuario p ON c.usuario_cs = p.usuario
            WHERE EXISTS (
                SELECT 1 FROM checklist_items ci
                WHERE c.checklist_item_id = ci.id
                AND ci.implantacao_id = %s
            )
            ORDER BY c.data_criacao DESC
            """,
                (impl_id,),
            )
            or []
        )
    except Exception as e:
        from ..config.logging_config import get_logger

        logger = get_logger("implantacao")
        logger.warning(f"Erro ao buscar comentarios_h em bulk para implantação {impl_id}: {e}")
        comentarios_h_raw = []

    for c in comentarios_h_raw:
        if c.get("subtarefa_h_id"):
            item_key = f"subtarefa_h_{c['subtarefa_h_id']}"
        elif c.get("tarefa_h_id"):
            item_key = f"tarefa_h_{c['tarefa_h_id']}"
        else:
            continue

        if not (is_owner or is_manager) and c.get("visibilidade") == "interno":
            continue

        c_formatado = {**c, "data_criacao_fmt_d": format_date_br(c.get("data_criacao_raw"))}
        c_formatado["delete_url"] = f"/api/checklist/comment/{c['id']}"
        c_formatado["email_url"] = f"/api/checklist/comment/{c['id']}/email"

        if item_key not in comentarios_map:
            comentarios_map[item_key] = []
        comentarios_map[item_key].append(c_formatado)

    return comentarios_map


def _get_tarefas_and_comentarios(
    impl_id: int, is_owner: bool = False, is_manager: bool = False
) -> tuple[OrderedDict, OrderedDict, OrderedDict, list[str]]:
    """
    Carrega tarefas e comentários de uma implantação.

    OTIMIZADO: Usa DataLoader para carregar TODOS os items em 1 query
    + 1 query para comentários (antes: 50+ queries N+1).

    Args:
        impl_id: ID da implantação
        is_owner: Se o usuário é dono da implantação
        is_manager: Se o usuário tem perfil de gestão

    Returns:
        Tupla com (obrigatorio, treinamento, pendencias, modulos)
    """
    from ..common.dataloader import ChecklistDataLoader

    comentarios_map = _get_comentarios_bulk(impl_id, is_owner, is_manager)

    tarefas_agrupadas_treinamento: OrderedDict[str, list[dict[str, Any]]] = OrderedDict()
    tarefas_agrupadas_obrigatorio: OrderedDict[str, list[dict[str, Any]]] = OrderedDict()
    tarefas_agrupadas_pendencias: OrderedDict[str, list[dict[str, Any]]] = OrderedDict()
    todos_modulos_temp: set[str] = set()

    # ── DataLoader: 1 query para TODOS os items ──
    loader = ChecklistDataLoader(impl_id)

    try:
        fases = loader.get_fases()
    except Exception as e:
        from ..config.logging_config import get_logger

        logger = get_logger("implantacao")
        logger.warning(f"Erro ao carregar fases para implantação {impl_id}: {e}")
        fases = []

    if fases:
        for fase in fases:
            grupos = loader.get_grupos(fase["id"])

            for grupo in grupos:
                modulo_nome = grupo.get("title") or grupo.get("nome") or f"Grupo {grupo.get('id')}"
                todos_modulos_temp.add(modulo_nome)
                tarefas = loader.get_tarefas(grupo["id"])

                ordem_c = 1
                for th in tarefas:
                    subtarefas = loader.get_subtarefas(th["id"])

                    if subtarefas:
                        for sub in subtarefas:
                            comentarios_sub = comentarios_map.get(f"subtarefa_h_{sub['id']}", [])

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
                        concl = bool(th.get("completed", False))
                        comentarios_th = comentarios_map.get(f"tarefa_h_{th['id']}", [])

                        tarefas_agrupadas_treinamento.setdefault(modulo_nome, []).append(
                            {
                                "id": th["id"],
                                "tarefa_filho": th.get("title") or th.get("nome"),
                                "concluida": concl,
                                "tag": "",
                                "ordem": th.get("ordem", ordem_c),
                                "comentarios": comentarios_th,
                                "toggle_url": f"/api/checklist/toggle/{th['id']}",
                                "comment_url": f"/api/checklist/comment/{th['id']}",
                                "delete_url": f"/api/checklist/delete/{th['id']}",
                            }
                        )
                        ordem_c += 1

                # Ordenar tarefas por ordem (uma vez por grupo, não a cada iteração)
                if modulo_nome in tarefas_agrupadas_treinamento:
                    tarefas_agrupadas_treinamento[modulo_nome].sort(key=lambda x: x.get("ordem", 0))

    # ── Ordenar módulos ──
    ordered_treinamento: OrderedDict[str, list[dict[str, Any]]] = OrderedDict()
    modulo_ordem_map: dict[str, int] = {}
    for modulo, lista in tarefas_agrupadas_treinamento.items():
        try:
            modulo_ordem_map[modulo] = min(t.get("ordem") or 0 for t in (lista or []))
        except Exception:
            modulo_ordem_map[modulo] = 0
    for modulo in [k for k, _ in sorted(modulo_ordem_map.items(), key=lambda x: (x[1], x[0]), reverse=True)]:
        ordered_treinamento[modulo] = tarefas_agrupadas_treinamento.get(modulo, [])

    if MODULO_OBRIGATORIO in todos_modulos_temp:
        todos_modulos_temp.discard(MODULO_OBRIGATORIO)

    todos_modulos_lista: list[str] = sorted(todos_modulos_temp, key=lambda m: modulo_ordem_map.get(m, 0), reverse=True)
    if MODULO_PENDENCIAS not in todos_modulos_lista:
        todos_modulos_lista.append(MODULO_PENDENCIAS)

    return tarefas_agrupadas_obrigatorio, ordered_treinamento, tarefas_agrupadas_pendencias, todos_modulos_lista


def get_implantacao_details(
    impl_id: int, usuario_cs_email: str, user_perfil: dict = None, plano_historico_id: int = None
) -> dict[str, Any]:
    """
    Busca, processa e valida todos os dados para a página de detalhes da implantação.
    Levanta um ValueError se o acesso for negado.

    Args:
        impl_id: ID da implantação
        usuario_cs_email: Email do usuário CS logado
        user_perfil: Perfil do usuário (pode ser None)
        plano_historico_id: ID de um plano de sucesso histórico para visualização (opcional)

    Returns:
        Dicionário com todos os dados necessários para renderizar a página

    Raises:
        ValueError: Se acesso for negado ou implantação não encontrada
    """
    from ..config.logging_config import get_logger

    logger = get_logger("implantacao")

    if user_perfil is None:
        user_perfil = {}

    # Force clear cache before fetching to ensure fresh data
    try:
        from ..config.cache_config import clear_implantacao_cache

        clear_implantacao_cache(impl_id)
    except Exception:
        pass

    try:
        implantacao, is_manager = _get_implantacao_and_validate_access(impl_id, usuario_cs_email, user_perfil)
    except ValueError as e:
        logger.warning(f"Acesso negado à implantação {impl_id}: {e!s}")
        raise
    except Exception as e:
        logger.error(f"Erro ao validar acesso à implantação {impl_id}: {e}", exc_info=True)
        raise

    try:
        implantacao = _format_implantacao_dates(implantacao)
    except Exception as e:
        logger.error(f"Erro ao formatar datas da implantação {impl_id}: {e}", exc_info=True)
        raise

    try:
        progresso, _, _ = _get_progress(impl_id)
    except Exception as e:
        logger.error(f"Erro ao calcular progresso da implantação {impl_id}: {e}", exc_info=True)
        raise

    try:
        is_owner = implantacao.get("usuario_cs") == usuario_cs_email
        tarefas_agrupadas_obrigatorio, ordered_treinamento, tarefas_agrupadas_pendencias, todos_modulos_lista = (
            _get_tarefas_and_comentarios(impl_id, is_owner=is_owner, is_manager=is_manager)
        )
    except Exception as e:
        logger.error(f"Erro ao carregar tarefas da implantação {impl_id}: {e}", exc_info=True)
        raise

    try:
        hierarquia = get_hierarquia_implantacao(impl_id)
    except Exception as e:
        import traceback

        error_trace = traceback.format_exc()
        logger.warning(
            f"Erro ao carregar hierarquia da implantação {impl_id}: {e}\n{error_trace}. Usando estrutura vazia."
        )
        hierarquia = {"fases": []}

    try:
        logs_timeline = _get_timeline_logs(impl_id)
    except Exception as e:
        logger.error(f"Erro ao carregar timeline da implantação {impl_id}: {e}", exc_info=True)
        raise

    nome_usuario_logado = user_perfil.get("nome", usuario_cs_email) if user_perfil else usuario_cs_email

    all_cs_users = []
    try:
        all_cs_users = query_db(
            "SELECT usuario, nome FROM perfil_usuario WHERE perfil_acesso IS NOT NULL AND perfil_acesso != '' ORDER BY nome"
        )
        all_cs_users = all_cs_users if all_cs_users is not None else []
    except Exception as e:
        logger.error(f"Erro ao carregar lista de CS users: {e}", exc_info=True)
        all_cs_users = []

    # Se estiver visualizando um histórico, o ID do plano vem do parâmetro
    success_plan_id = plano_historico_id or implantacao.get("plano_sucesso_id")

    plano_sucesso_info = None
    try:
        if success_plan_id:
            plano_sucesso_info = query_db("SELECT * FROM planos_sucesso WHERE id = %s", (success_plan_id,), one=True)
    except Exception as e:
        logger.warning(f"Erro ao buscar plano de sucesso {success_plan_id}: {e}")

    checklist_nested = None
    try:
        from ..domain.checklist_service import build_nested_tree, get_checklist_tree

        if plano_historico_id:
            checklist_flat = get_checklist_tree(plano_id=plano_historico_id, include_progress=True)
        else:
            checklist_flat = get_checklist_tree(implantacao_id=impl_id, include_progress=True)

        # SELF-HEALING: Se tem plano mas não tem itens, clonar agora.
        if not checklist_flat and implantacao.get("plano_sucesso_id") and plano_sucesso_info and not plano_historico_id:
            logger.warning(
                f"Implantação {impl_id} tem plano {implantacao['plano_sucesso_id']} mas checklist vazio. Tentando auto-reparar..."
            )
            try:
                from datetime import (
                    date as datetime_date,
                    datetime,
                    timedelta,
                )

                from ..db import db_connection
                from ..domain.planos.aplicar import _clonar_plano_para_implantacao_checklist

                plano_id = implantacao["plano_sucesso_id"]
                dias_duracao = plano_sucesso_info.get("dias_duracao") or 0

                # Resolver data base safely
                data_base = implantacao.get("data_inicio_efetivo") or implantacao.get("data_criacao")
                base_dt = datetime.now()

                if data_base:
                    if isinstance(data_base, str):
                        with contextlib.suppress(ValueError, TypeError):
                            base_dt = datetime.strptime(data_base[:10], "%Y-%m-%d")
                    elif isinstance(data_base, datetime):
                        base_dt = data_base
                    elif isinstance(data_base, datetime_date):
                        base_dt = datetime.combine(data_base, datetime.min.time())

                data_previsao = base_dt + timedelta(days=int(dias_duracao))

                with db_connection() as (conn, db_type):
                    cursor = conn.cursor()
                    responsavel = "sistema"

                    _clonar_plano_para_implantacao_checklist(
                        cursor, db_type, plano_id, impl_id, responsavel, base_dt, int(dias_duracao), data_previsao
                    )
                    conn.commit()

                logger.info("Auto-reparo concluído. Recarregando checklist...")
                # Invalida cache se houver
                try:
                    from ..config.cache_config import clear_implantacao_cache

                    clear_implantacao_cache(impl_id)
                except Exception:
                    pass

                # Busca novamente
                checklist_flat = get_checklist_tree(implantacao_id=impl_id, include_progress=True)
            except Exception as e:
                logger.error(f"Falha no auto-reparo do checklist: {e}", exc_info=True)

        if checklist_flat:
            checklist_nested = build_nested_tree(checklist_flat)
    except Exception as e:
        import traceback

        error_trace = traceback.format_exc()
        logger.warning(
            f"Erro ao carregar checklist da implantação {impl_id}: {e}\n{error_trace}. Usando checklist vazio."
        )
        checklist_nested = []

    try:
        user_info = getattr(g, "user", None) or {
            "email": usuario_cs_email,
            "nome": user_perfil.get("nome", usuario_cs_email) if user_perfil else usuario_cs_email,
        }
    except Exception:
        user_info = {
            "email": usuario_cs_email,
            "nome": user_perfil.get("nome", usuario_cs_email) if user_perfil else usuario_cs_email,
        }

    # Buscar planos (instâncias) associados a esta implantação
    planos_lista = []
    plano_ativo_instancia = None
    try:
        planos_lista = (
            query_db(
                "SELECT * FROM planos_sucesso WHERE processo_id = %s ORDER BY data_criacao DESC", (impl_id,)
            )
            or []
        )

        # Determinar qual plano mostrar como "ativo" no contexto da página
        if plano_historico_id:
            # Se é visão de histórico, o plano ativo é o do histórico
            plano_ativo_instancia = query_db("SELECT * FROM planos_sucesso WHERE id = %s", (plano_historico_id,), one=True)
        else:
            # Identificar a instância em andamento na lista de planos da implantação
            plano_ativo_instancia = next((p for p in planos_lista if p.get("status") == "em_andamento"), None)

            # Fallback de compatibilidade: se não há instância em andamento na lista, mas a implantação
            # tem um plano_sucesso_id, usamos ele apenas se ele ainda estiver 'em_andamento'
            if not plano_ativo_instancia and implantacao.get("plano_sucesso_id"):
                temp_p = query_db("SELECT * FROM planos_sucesso WHERE id = %s", (implantacao["plano_sucesso_id"],), one=True)
                if temp_p and temp_p.get("status") == "em_andamento":
                    plano_ativo_instancia = temp_p

        # Formatar datas para o template em todos os planos da lista
        for p in planos_lista:
            p["data_criacao_fmt"] = format_date_br(p.get("data_criacao"), False)
            p["data_atualizacao_fmt"] = format_date_br(p.get("data_atualizacao"), p.get("status") != "concluido")
            p["data_conclusao_fmt"] = format_date_br(p.get("data_atualizacao"), False)

        # Formatar datas para o plano exibido
        if plano_ativo_instancia:
            plano_ativo_instancia["data_criacao_fmt"] = format_date_br(plano_ativo_instancia.get("data_criacao"), False)
            plano_ativo_instancia["data_atualizacao_fmt"] = format_date_br(
                plano_ativo_instancia.get("data_atualizacao"), plano_ativo_instancia.get("status") != "concluido"
            )
    except Exception as e:
        logger.warning(f"Erro ao buscar lista de planos da implantação {impl_id}: {e}")

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
        "nome_usuario_logado": nome_usuario_logado,
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
        "is_owner": implantacao.get('usuario_cs') == usuario_cs_email,
        "tt": TASK_TIPS,
        "plano_sucesso": plano_sucesso_info,
        "checklist_tree": checklist_nested,
        "planos_lista": planos_lista,
        "plano_ativo_instancia": plano_ativo_instancia,
        "is_historico_view": bool(plano_historico_id),
        "plano_historico_id": plano_historico_id,
    }


# ============================================================================
# FUNÇÕES CRUD REMOVIDAS - Agora em: domain/implantacao/crud.py
# As funções são re-importadas no topo deste arquivo para compatibilidade.
# Funções movidas: criar_implantacao, criar_implantacao_modulo, transferir, excluir, cancelar
# ============================================================================

# ============================================================================
# FUNÇÕES DE STATUS REMOVIDAS - Agora em: domain/implantacao/status.py
# As funções são re-importadas no topo deste arquivo para compatibilidade.
# Funções movidas: iniciar, agendar, marcar_sem_previsao, finalizar, parar, retomar, reabrir
# ============================================================================


def remover_plano_implantacao_service(implantacao_id: int, usuario_cs_email: str, user_perfil_acesso: str) -> None:
    """
    Remove o plano de sucesso de uma implantação, limpando todas as fases/ações/tarefas associadas.

    Args:
        implantacao_id: ID da implantação
        usuario_cs_email: Email do CS que está removendo
        user_perfil_acesso: Perfil de acesso do usuário

    Raises:
        ValueError: Se implantação não encontrada ou permissão negada
    """
    impl = query_db("SELECT id, usuario_cs, nome_empresa FROM implantacoes WHERE id = %s", (implantacao_id,), one=True)
    if not impl:
        raise ValueError("Implantação não encontrada.")

    is_owner = impl.get("usuario_cs") == usuario_cs_email
    is_manager = user_perfil_acesso in PERFIS_COM_GESTAO

    if not (is_owner or is_manager):
        raise ValueError("Permissão negada.")

    try:
        before = query_db(
            "SELECT COUNT(*) as total FROM checklist_items WHERE implantacao_id = %s", (implantacao_id,), one=True
        ) or {"total": 0}
        total_removed = int(before.get("total", 0) or 0)
    except Exception:
        total_removed = None

    # Deletar checklist_items (comentários serão deletados automaticamente via CASCADE)
    execute_db("DELETE FROM checklist_items WHERE implantacao_id = %s", (implantacao_id,))

    execute_db(
        "UPDATE implantacoes SET plano_sucesso_id = NULL, data_atribuicao_plano = NULL, data_previsao_termino = NULL WHERE id = %s",
        (implantacao_id,),
    )

    detalhe = f"Plano de sucesso removido da implantação por {usuario_cs_email}."
    if isinstance(total_removed, int):
        detalhe += f" Itens removidos: {total_removed}."

    logar_timeline(implantacao_id, usuario_cs_email, "plano_removido", detalhe)

    # Limpar cache relacionado à implantação
    from ..config.cache_config import clear_implantacao_cache, clear_user_cache

    clear_implantacao_cache(implantacao_id)
    clear_user_cache(usuario_cs_email)


# ============================================================================
# FIM DAS FUNÇÕES - As seguintes foram movidas para módulos específicos:
# - listar_implantacoes -> implantacao/listing.py
# - obter_implantacao_basica -> implantacao/listing.py
# - consultar_dados_oamd -> implantacao/oamd_integration.py
# - aplicar_dados_oamd -> implantacao/oamd_integration.py
# ============================================================================
