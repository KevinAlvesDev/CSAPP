from collections import OrderedDict
from datetime import datetime, timedelta
from functools import wraps

from flask import current_app, g

from ..common.utils import format_date_br, format_date_iso_for_json
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
    MODULO_OPCOES,
)
from ..db import execute_and_fetch_one, execute_db, logar_timeline, query_db, db_transaction_with_lock
from ..domain.hierarquia_service import get_hierarquia_implantacao
from ..domain.task_definitions import MODULO_OBRIGATORIO, MODULO_PENDENCIAS, TASK_TIPS

try:
    from ..config.cache_config import cache
except ImportError:
    cache = None


def cached_progress(ttl=30):
    """
    Decorator para cachear resultado de cálculo de progresso.
    TTL padrão: 30 segundos

    Args:
        ttl: Time to live em segundos (padrão: 30)

    Returns:
        Decorator function
    """
    def decorator(func):
        @wraps(func)
        def wrapper(impl_id, *args, **kwargs):
            if not cache:
                return func(impl_id, *args, **kwargs)

            cache_key = f'progresso_impl_{impl_id}'

            try:
                cached_result = cache.get(cache_key)

                if cached_result is not None:
                    return cached_result

                result = func(impl_id, *args, **kwargs)
                cache.set(cache_key, result, timeout=ttl)

                return result
            except Exception as e:
                current_app.logger.warning(f"Erro no cache de progresso para impl_id {impl_id}: {e}")
                return func(impl_id, *args, **kwargs)

        return wrapper
    return decorator


def invalidar_cache_progresso(impl_id):
    """
    Invalida o cache de progresso de uma implantação específica.
    Deve ser chamado sempre que o status de uma tarefa mudar.
    
    Args:
        impl_id: ID da implantação
    """
    if not cache:
        return

    try:
        cache_key = f'progresso_impl_{impl_id}'
        cache.delete(cache_key)
    except Exception as e:
        if current_app:
            current_app.logger.warning(f"Erro ao invalidar cache de progresso para impl_id {impl_id}: {e}")


def _get_progress_optimized(impl_id):
    """
    Versão otimizada que usa uma única query com checklist_items.
    Agora usa checklist_items (estrutura consolidada).
    
    Lógica de cálculo do progresso:
    - Conta apenas itens "folha" (que não têm filhos) para evitar dupla contagem
    - Itens folha são: subtarefas OU tarefas sem subtarefas
    - Se tipo_item não estiver preenchido, usa lógica baseada em parent_id
    """
    try:
        items_exist = query_db(
            "SELECT id FROM checklist_items WHERE implantacao_id = %s LIMIT 1",
            (impl_id,),
            one=True
        )
    except Exception:
        items_exist = None

    if not items_exist:
        return 0, 0, 0

    is_sqlite = current_app.config.get('USE_SQLITE_LOCALLY', False)

    try:
        if is_sqlite:
            query = """
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN completed = 1 THEN 1 ELSE 0 END) as done
                FROM checklist_items ci
                WHERE ci.implantacao_id = ?
                AND NOT EXISTS (
                    SELECT 1 FROM checklist_items filho 
                    WHERE filho.parent_id = ci.id
                    AND filho.implantacao_id = ?
                )
            """
            result = query_db(query, (impl_id, impl_id), one=True) or {}

            total = int(result.get('total', 0) or 0)
            done = int(result.get('done', 0) or 0)
        else:
            query = """
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN completed THEN 1 ELSE 0 END) as done
                FROM checklist_items ci
                WHERE ci.implantacao_id = %s
                AND NOT EXISTS (
                    SELECT 1 FROM checklist_items filho 
                    WHERE filho.parent_id = ci.id
                    AND filho.implantacao_id = %s
                )
            """
            result = query_db(query, (impl_id, impl_id), one=True) or {}

            total = int(result.get('total', 0) or 0)
            done = int(result.get('done', 0) or 0)

        if total == 0:
            any_items = query_db(
                "SELECT COUNT(*) as count FROM checklist_items WHERE implantacao_id = %s",
                (impl_id,),
                one=True
            )
            if any_items and int(any_items.get('count', 0) or 0) > 0:
                if is_sqlite:
                    fallback_query = """
                        SELECT
                            COUNT(*) as total,
                            SUM(CASE WHEN completed = 1 THEN 1 ELSE 0 END) as done
                        FROM checklist_items
                        WHERE implantacao_id = ?
                    """
                    fallback_result = query_db(fallback_query, (impl_id,), one=True) or {}
                else:
                    fallback_query = """
                        SELECT
                            COUNT(*) as total,
                            SUM(CASE WHEN completed THEN 1 ELSE 0 END) as done
                        FROM checklist_items
                        WHERE implantacao_id = %s
                    """
                    fallback_result = query_db(fallback_query, (impl_id,), one=True) or {}

                total = int(fallback_result.get('total', 0) or 0)
                done = int(fallback_result.get('done', 0) or 0)

        return int(round((done / total) * 100)) if total > 0 else 100, total, done

    except Exception as e:
        current_app.logger.error(f"Erro ao calcular progresso otimizado para impl_id {impl_id}: {e}", exc_info=True)
        return _get_progress_legacy(impl_id)


def _get_progress_legacy(impl_id):
    """
    Versão legada usando checklist_items - mantida como fallback.
    Agora usa checklist_items (estrutura consolidada).
    """
    try:
        items_exist = query_db(
            "SELECT id FROM checklist_items WHERE implantacao_id = %s LIMIT 1",
            (impl_id,),
            one=True
        )
    except Exception:
        items_exist = None

    if items_exist:
        sub = query_db(
            """
            SELECT COUNT(*) as total, SUM(CASE WHEN completed THEN 1 ELSE 0 END) as done
            FROM checklist_items
            WHERE implantacao_id = %s AND tipo_item = 'subtarefa'
            """,
            (impl_id,), one=True
        ) or {}

        th_no = query_db(
            """
            SELECT COUNT(*) as total,
                   SUM(CASE WHEN completed THEN 1 ELSE 0 END) as done
            FROM checklist_items ci
            WHERE ci.implantacao_id = %s 
            AND ci.tipo_item = 'tarefa'
            AND NOT EXISTS (
                SELECT 1 FROM checklist_items s 
                WHERE s.parent_id = ci.id 
                AND s.tipo_item = 'subtarefa'
            )
            """,
            (impl_id,), one=True
        ) or {}

        total = int(sub.get('total', 0) or 0) + int(th_no.get('total', 0) or 0)
        done = int(sub.get('done', 0) or 0) + int(th_no.get('done', 0) or 0)
        return int(round((done / total) * 100)) if total > 0 else 100, total, done

    return 0, 0, 0


@cached_progress(ttl=30)
def _get_progress(impl_id):
    """
    Calcula progresso da implantação usando apenas modelo hierárquico.
    Usa versão otimizada se habilitada via feature flag.
    """
    use_optimized = current_app.config.get('USE_OPTIMIZED_PROGRESS', True)

    if use_optimized:
        return _get_progress_optimized(impl_id)
    else:
        return _get_progress_legacy(impl_id)


def auto_finalizar_implantacao(impl_id, usuario_cs_email):
    """
    Verifica se todas as tarefas hierárquicas estão concluídas
    e, em caso afirmativo, finaliza a implantação.
    Agora usa checklist_items (estrutura consolidada).
    """
    items_exist = query_db(
        "SELECT id FROM checklist_items WHERE implantacao_id = %s LIMIT 1",
        (impl_id,),
        one=True
    )

    if not items_exist:
        return False, None

    subtarefas_pendentes = query_db(
        """
        SELECT COUNT(*) as total
        FROM checklist_items
        WHERE implantacao_id = %s 
        AND tipo_item = 'subtarefa' 
        AND completed = false
        """,
        (impl_id,), one=True
    ) or {}

    tarefas_pendentes = query_db(
        """
        SELECT COUNT(*) as total
        FROM checklist_items ci
        WHERE ci.implantacao_id = %s
        AND ci.tipo_item = 'tarefa'
        AND ci.completed = false
        AND NOT EXISTS (
            SELECT 1 FROM checklist_items s 
            WHERE s.parent_id = ci.id 
            AND s.tipo_item = 'subtarefa'
        )
        """,
        (impl_id,), one=True
    ) or {}

    total_pendentes = int(subtarefas_pendentes.get('total', 0) or 0) + int(tarefas_pendentes.get('total', 0) or 0)

    if total_pendentes == 0:
        impl_status = query_db(
            "SELECT status, nome_empresa FROM implantacoes WHERE id = %s",
            (impl_id,),
            one=True
        )
        if impl_status and impl_status.get('status') == 'andamento':
            agora = datetime.now()
            execute_db(
                "UPDATE implantacoes SET status = 'finalizada', data_finalizacao = %s WHERE id = %s",
                (agora, impl_id)
            )
            detalhe = f'Implantação "{impl_status.get("nome_empresa", "N/A")}" auto-finalizada.'
            logar_timeline(impl_id, usuario_cs_email, 'auto_finalizada', detalhe)

            perfil = query_db("SELECT nome FROM perfil_usuario WHERE usuario = %s", (usuario_cs_email,), one=True)
            nome = perfil.get('nome') if perfil else usuario_cs_email

            log_final = query_db(
                "SELECT *, %s as usuario_nome FROM timeline_log "
                "WHERE implantacao_id = %s AND tipo_evento = 'auto_finalizada' "
                "ORDER BY id DESC LIMIT 1",
                (nome, impl_id),
                one=True
            )
            if log_final:
                if not isinstance(log_final, dict):
                    log_final = dict(log_final)
                log_final['data_criacao'] = format_date_iso_for_json(log_final.get('data_criacao'))
                return True, log_final
            else:
                return True, None
    return False, None


def _get_implantacao_and_validate_access(impl_id, usuario_cs_email, user_perfil):
    user_perfil_acesso = user_perfil.get('perfil_acesso') if user_perfil else None
    implantacao = query_db("SELECT * FROM implantacoes WHERE id = %s", (impl_id,), one=True)

    if not implantacao:
        raise ValueError('Implantação não encontrada.')

    is_owner = implantacao.get('usuario_cs') == usuario_cs_email
    is_manager = user_perfil_acesso in PERFIS_COM_GESTAO

    if not is_owner and not is_manager:
        if implantacao.get('status') == 'nova':
             raise ValueError('Esta implantação ainda não foi iniciada.')
        else:
            raise ValueError('Implantação não encontrada ou não pertence a você.')

    if implantacao.get('status') == 'nova' and is_owner and not is_manager:
         raise ValueError('Esta implantação está aguardando início. Use os botões "Iniciar" ou "Início Futuro" no dashboard.')

    return implantacao, is_manager


def _format_implantacao_dates(implantacao):
    implantacao['data_criacao_fmt_dt_hr'] = format_date_br(implantacao.get('data_criacao'), True)
    implantacao['data_criacao_fmt_d'] = format_date_br(implantacao.get('data_criacao'), False)
    implantacao['data_inicio_efetivo_fmt_d'] = format_date_br(implantacao.get('data_inicio_efetivo'), False)
    implantacao['data_finalizacao_fmt_d'] = format_date_br(implantacao.get('data_finalizacao'), False)
    implantacao['data_inicio_producao_fmt_d'] = format_date_br(implantacao.get('data_inicio_producao'), False)
    implantacao['data_final_implantacao_fmt_d'] = format_date_br(implantacao.get('data_final_implantacao'), False)
    implantacao['data_previsao_termino_fmt_d'] = format_date_br(implantacao.get('data_previsao_termino'), False)
    implantacao['data_criacao_iso'] = format_date_iso_for_json(implantacao.get('data_criacao'), only_date=True)
    implantacao['data_inicio_efetivo_iso'] = format_date_iso_for_json(implantacao.get('data_inicio_efetivo'), only_date=True)
    implantacao['data_inicio_producao_iso'] = format_date_iso_for_json(implantacao.get('data_inicio_producao'), only_date=True)
    implantacao['data_final_implantacao_iso'] = format_date_iso_for_json(implantacao.get('data_final_implantacao'), only_date=True)
    implantacao['data_inicio_previsto_fmt_d'] = format_date_br(implantacao.get('data_inicio_previsto'), False)
    
    # Formatação de novos campos
    if implantacao.get('data_cadastro'):
        implantacao['data_cadastro_fmt_d'] = format_date_br(implantacao.get('data_cadastro'), False)
        implantacao['data_cadastro_iso'] = format_date_iso_for_json(implantacao.get('data_cadastro'), only_date=True)
        
    return implantacao


def _get_comentarios_bulk(impl_id, is_owner=False, is_manager=False):
    """
    Busca TODOS os comentários de uma implantação em uma única query (ou poucas queries).
    Retorna dicionário indexado por item_id para acesso rápido.
    """
    comentarios_map = {}

    try:
        comentarios_h_raw = query_db(
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
            (impl_id,)
        ) or []
    except Exception as e:
        from ..config.logging_config import get_logger
        logger = get_logger('implantacao')
        logger.warning(f"Erro ao buscar comentarios_h em bulk para implantação {impl_id}: {e}")
        comentarios_h_raw = []

    for c in comentarios_h_raw:
        if c.get('subtarefa_h_id'):
            item_key = f"subtarefa_h_{c['subtarefa_h_id']}"
        elif c.get('tarefa_h_id'):
            item_key = f"tarefa_h_{c['tarefa_h_id']}"
        else:
            continue

        if not (is_owner or is_manager):
            if c.get('visibilidade') == 'interno':
                continue

        c_formatado = {
            **c,
            'data_criacao_fmt_d': format_date_br(c.get('data_criacao_raw'))
        }
        c_formatado['delete_url'] = f"/api/checklist/comment/{c['id']}"
        c_formatado['email_url'] = f"/api/checklist/comment/{c['id']}/email"

        if item_key not in comentarios_map:
            comentarios_map[item_key] = []
        comentarios_map[item_key].append(c_formatado)

    return comentarios_map


def _get_tarefas_and_comentarios(impl_id, is_owner=False, is_manager=False):
    comentarios_map = _get_comentarios_bulk(impl_id, is_owner, is_manager)

    tarefas_agrupadas_treinamento = OrderedDict()
    tarefas_agrupadas_obrigatorio = OrderedDict()
    tarefas_agrupadas_pendencias = OrderedDict()
    todos_modulos_temp = set()

    try:
        fases_raw = query_db(
            "SELECT id, title as nome, ordem FROM checklist_items WHERE implantacao_id = %s AND tipo_item = 'fase' AND parent_id IS NULL ORDER BY ordem DESC",
            (impl_id,)
        ) or []
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        from ..config.logging_config import get_logger
        logger = get_logger('implantacao')
        logger.warning(f"Erro ao buscar fases para implantação {impl_id}: {e}\n{error_trace}")
        fases_raw = []
    if fases_raw:
        tarefas_agrupadas_treinamento = OrderedDict()
        todos_modulos_temp = set()
        for fase in fases_raw:
            try:
                grupos_raw = query_db(
                    "SELECT id, title as nome FROM checklist_items WHERE parent_id = %s AND tipo_item = 'grupo'",
                    (fase['id'],)
                ) or []
            except Exception as e:
                from ..config.logging_config import get_logger
                logger = get_logger('implantacao')
                logger.warning(f"Erro ao buscar grupos para fase {fase.get('id')}: {e}")
                grupos_raw = []

            for grupo in grupos_raw:
                modulo_nome = grupo.get('nome') or f"Grupo {grupo.get('id')}"
                todos_modulos_temp.add(modulo_nome)
                try:
                    tarefas_h_raw = query_db(
                        "SELECT * FROM checklist_items WHERE parent_id = %s AND tipo_item = 'tarefa'",
                        (grupo['id'],)
                    ) or []
                except Exception as e:
                    from ..config.logging_config import get_logger
                    logger = get_logger('implantacao')
                    logger.warning(f"Erro ao buscar tarefas para grupo {grupo.get('id')}: {e}")
                    tarefas_h_raw = []
                ordem_c = 1
                for th in tarefas_h_raw:
                        try:
                            subs_raw = query_db(
                                "SELECT * FROM checklist_items WHERE parent_id = %s AND tipo_item = 'subtarefa'",
                                (th['id'],)
                            ) or []
                        except Exception as e:
                            from ..config.logging_config import get_logger
                            logger = get_logger('implantacao')
                            logger.warning(f"Erro ao buscar subtarefas para tarefa {th.get('id')}: {e}")
                            subs_raw = []
                        if subs_raw:
                            for sub in subs_raw:
                                comentarios_sub = comentarios_map.get(f"subtarefa_h_{sub['id']}", [])

                                tarefas_agrupadas_treinamento.setdefault(modulo_nome, []).append({
                                    'id': sub['id'],
                                    'tarefa_filho': sub.get('title') or sub.get('nome'),
                                    'concluida': bool(sub.get('completed')),
                                    'tag': sub.get('tag', ''),
                                    'ordem': sub.get('ordem', ordem_c),
                                    'comentarios': comentarios_sub,
                                    'toggle_url': f"/api/checklist/toggle/{sub['id']}",
                                    'comment_url': f"/api/checklist/comment/{sub['id']}"
                                })
                                tarefas_agrupadas_treinamento[modulo_nome].sort(key=lambda x: x.get('ordem', 0))
                                tarefas_agrupadas_treinamento[modulo_nome][-1]['delete_url'] = f"/api/checklist/delete/{sub['id']}"
                                ordem_c += 1
                        else:
                            concl = bool(th.get('completed', False))

                            comentarios_th = comentarios_map.get(f"tarefa_h_{th['id']}", [])

                            tarefas_agrupadas_treinamento.setdefault(modulo_nome, []).append({
                                'id': th['id'],
                                'tarefa_filho': th.get('title') or th.get('nome'),
                                'concluida': concl,
                                'tag': '',
                                'ordem': th.get('ordem', ordem_c),
                                'comentarios': comentarios_th,
                                'toggle_url': f"/api/checklist/toggle/{th['id']}",
                                'comment_url': f"/api/checklist/comment/{th['id']}"
                            })
                            tarefas_agrupadas_treinamento[modulo_nome].sort(key=lambda x: x.get('ordem', 0))
                            tarefas_agrupadas_treinamento[modulo_nome][-1]['delete_url'] = f"/api/checklist/delete/{th['id']}"
                            ordem_c += 1

    ordered_treinamento = OrderedDict()
    modulo_ordem_map = {}
    for modulo, lista in tarefas_agrupadas_treinamento.items():
        try:
            modulo_ordem_map[modulo] = min([t.get('ordem') or 0 for t in (lista or [])])
        except Exception:
            modulo_ordem_map[modulo] = 0
    for modulo in [k for k,  _ in sorted(modulo_ordem_map.items(), key=lambda x: (x[1], x[0]), reverse=True)]:
        ordered_treinamento[modulo] = tarefas_agrupadas_treinamento.get(modulo, [])

    if MODULO_OBRIGATORIO in todos_modulos_temp:
        try:
            todos_modulos_temp.remove(MODULO_OBRIGATORIO)
        except Exception:
            pass
    todos_modulos_lista = sorted(list(todos_modulos_temp))
    if MODULO_PENDENCIAS not in todos_modulos_lista:
        todos_modulos_lista.append(MODULO_PENDENCIAS)

    todos_modulos_lista = sorted(list(todos_modulos_temp), key=lambda m: modulo_ordem_map.get(m, 0), reverse=True)
    if MODULO_PENDENCIAS not in todos_modulos_lista:
        todos_modulos_lista.append(MODULO_PENDENCIAS)

    return tarefas_agrupadas_obrigatorio, ordered_treinamento, tarefas_agrupadas_pendencias, todos_modulos_lista


def _get_timeline_logs(impl_id):
    logs_timeline = query_db(
        """ SELECT tl.*, COALESCE(p.nome, tl.usuario_cs) as usuario_nome 
            FROM timeline_log tl LEFT JOIN perfil_usuario p ON tl.usuario_cs = p.usuario 
            WHERE tl.implantacao_id = %s ORDER BY tl.data_criacao DESC """, (impl_id,)
    )
    for log in logs_timeline:
        log['data_criacao_fmt_dt_hr'] = format_date_br(log.get('data_criacao'), True)
        try:
            import re
            detalhes = log.get('detalhes') or ''
            m = re.search(r'(Item|Subtarefa|TarefaH)\s+(\d+)', detalhes)
            if not m:
                m = re.search(r'data-item-id="(\d+)"', detalhes)
            log['related_item_id'] = int(m.group(2) if m and m.groups() and len(m.groups())>1 else (m.group(1) if m else 0)) or None
        except Exception:
            log['related_item_id'] = None
    return logs_timeline


def get_implantacao_details(impl_id, usuario_cs_email, user_perfil):
    """
    Busca, processa e valida todos os dados para a página de detalhes da implantação.
    Levanta um ValueError se o acesso for negado.
    """
    from ..config.logging_config import get_logger
    logger = get_logger('implantacao')

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
        logger.warning(f"Acesso negado à implantação {impl_id}: {str(e)}")
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
        is_owner = implantacao.get('usuario_cs') == usuario_cs_email
        tarefas_agrupadas_obrigatorio, ordered_treinamento, tarefas_agrupadas_pendencias, todos_modulos_lista = _get_tarefas_and_comentarios(impl_id, is_owner=is_owner, is_manager=is_manager)
    except Exception as e:
        logger.error(f"Erro ao carregar tarefas da implantação {impl_id}: {e}", exc_info=True)
        raise

    try:
        hierarquia = get_hierarquia_implantacao(impl_id)
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        logger.warning(f"Erro ao carregar hierarquia da implantação {impl_id}: {e}\n{error_trace}. Usando estrutura vazia.")
        hierarquia = {'fases': []}

    try:
        logs_timeline = _get_timeline_logs(impl_id)
    except Exception as e:
        logger.error(f"Erro ao carregar timeline da implantação {impl_id}: {e}", exc_info=True)
        raise

    nome_usuario_logado = user_perfil.get('nome', usuario_cs_email) if user_perfil else usuario_cs_email

    all_cs_users = []
    try:
        all_cs_users = query_db("SELECT usuario, nome FROM perfil_usuario WHERE perfil_acesso IS NOT NULL AND perfil_acesso != '' ORDER BY nome")
        all_cs_users = all_cs_users if all_cs_users is not None else []
    except Exception as e:
        logger.error(f"Erro ao carregar lista de CS users: {e}", exc_info=True)
        all_cs_users = []

    plano_sucesso_info = None
    try:
        if implantacao.get('plano_sucesso_id'):
            plano_sucesso_info = query_db(
                "SELECT * FROM planos_sucesso WHERE id = %s",
                (implantacao['plano_sucesso_id'],),
                one=True
            )
            if plano_sucesso_info:
                logger.info(f"Plano de sucesso encontrado: {plano_sucesso_info.get('nome')}")
            else:
                logger.warning(f"Plano de sucesso ID {implantacao['plano_sucesso_id']} não encontrado")
    except Exception as e:
        logger.warning(f"Erro ao buscar plano de sucesso: {e}")
        pass

    checklist_tree = None
    checklist_nested = None
    try:
        from ..domain.checklist_service import build_nested_tree, get_checklist_tree
        checklist_flat = get_checklist_tree(
            implantacao_id=impl_id,
            include_progress=True
        )
        if checklist_flat:
            checklist_nested = build_nested_tree(checklist_flat)
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        logger.warning(f"Erro ao carregar checklist da implantação {impl_id}: {e}\n{error_trace}. Usando checklist vazio.")
        checklist_nested = []


    try:
        user_info = getattr(g, 'user', None) or {'email': usuario_cs_email, 'nome': user_perfil.get('nome', usuario_cs_email) if user_perfil else usuario_cs_email}
    except Exception:
        user_info = {'email': usuario_cs_email, 'nome': user_perfil.get('nome', usuario_cs_email) if user_perfil else usuario_cs_email}

    return {
        'user_info': user_info,
        'implantacao': implantacao,
        'hierarquia': hierarquia,
        'tarefas_agrupadas_obrigatorio': tarefas_agrupadas_obrigatorio,
        'tarefas_agrupadas_treinamento': ordered_treinamento,
        'tarefas_agrupadas_pendencias': tarefas_agrupadas_pendencias,
        'todos_modulos': todos_modulos_lista,
        'modulo_pendencias_nome': MODULO_PENDENCIAS,
        'progresso_porcentagem': progresso,
        'nome_usuario_logado': nome_usuario_logado,
        'email_usuario_logado': usuario_cs_email,
        'justificativas_parada': JUSTIFICATIVAS_PARADA,
        'logs_timeline': logs_timeline,
        'cargos_responsavel': CARGOS_RESPONSAVEL,
        'NIVEIS_RECEITA': NIVEIS_RECEITA,
        'SEGUIMENTOS_LIST': SEGUIMENTOS_LIST,
        'TIPOS_PLANOS': TIPOS_PLANOS,
        'MODALIDADES_LIST': MODALIDADES_LIST,
        'HORARIOS_FUNCIONAMENTO': HORARIOS_FUNCIONAMENTO,
        'FORMAS_PAGAMENTO': FORMAS_PAGAMENTO,
        'SISTEMAS_ANTERIORES': SISTEMAS_ANTERIORES,
        'RECORRENCIA_USADA': RECORRENCIA_USADA,
        'SIM_NAO_OPTIONS': SIM_NAO_OPTIONS,
        'all_cs_users': all_cs_users,
        'is_manager': is_manager,
        'tt': TASK_TIPS,
        'plano_sucesso': plano_sucesso_info,
        'checklist_tree': checklist_nested
    }


def criar_implantacao_service(nome_empresa, usuario_atribuido, usuario_criador, id_favorecido=None):
    """
    Cria uma nova implantação completa.
    """
    if not nome_empresa:
        raise ValueError('Nome da empresa é obrigatório.')
    if not usuario_atribuido:
        raise ValueError('Usuário a ser atribuído é obrigatório.')

    existente = query_db(
        """
        SELECT id, status
        FROM implantacoes
        WHERE LOWER(nome_empresa) = LOWER(%s)
          AND status IN ('nova','futura','andamento','parada')
        LIMIT 1
        """,
        (nome_empresa,), one=True
    )
    if existente:
        status_existente = existente.get('status')
        raise ValueError(f'Já existe uma implantação ativa para "{nome_empresa}" (status: {status_existente}).')

    tipo = 'completa'
    status = 'nova'
    agora = datetime.now()

    result = execute_and_fetch_one(
        "INSERT INTO implantacoes (usuario_cs, nome_empresa, tipo, data_criacao, status, data_inicio_previsto, data_inicio_efetivo, id_favorecido) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id",
        (usuario_atribuido, nome_empresa, tipo, agora, status, None, None, id_favorecido)
    )

    implantacao_id = result.get('id') if result else None
    if not implantacao_id:
        raise Exception("Falha ao obter ID da nova implantação.")

    logar_timeline(implantacao_id, usuario_criador, 'implantacao_criada', f'Implantação "{nome_empresa}" ({tipo.capitalize()}) criada e atribuída a {usuario_atribuido}.')
    
    return implantacao_id


def criar_implantacao_modulo_service(nome_empresa, usuario_atribuido, usuario_criador, modulo_tipo, id_favorecido=None):
    """
    Cria uma nova implantação de módulo.
    """
    if not nome_empresa:
        raise ValueError('Nome da empresa é obrigatório.')
    if not usuario_atribuido:
        raise ValueError('Usuário a ser atribuído é obrigatório.')
    
    modulo_opcoes = {
        'nota_fiscal': 'Nota fiscal',
        'vendas_online': 'Vendas Online',
        'app_treino': 'App Treino',
        'recorrencia': 'Recorrência'
    }
    if modulo_tipo not in modulo_opcoes:
        raise ValueError('Módulo inválido.')

    existente = query_db(
        """
        SELECT id, status
        FROM implantacoes
        WHERE LOWER(nome_empresa) = LOWER(%s)
          AND status IN ('nova','futura','andamento','parada')
        LIMIT 1
        """,
        (nome_empresa,), one=True
    )
    if existente:
        status_existente = existente.get('status')
        raise ValueError(f'Já existe uma implantação ativa para "{nome_empresa}" (status: {status_existente}).')

    tipo = 'modulo'
    status = 'nova'
    agora = datetime.now()

    result = execute_and_fetch_one(
        "INSERT INTO implantacoes (usuario_cs, nome_empresa, tipo, data_criacao, status, data_inicio_previsto, data_inicio_efetivo, id_favorecido) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id",
        (usuario_atribuido, nome_empresa, tipo, agora, status, None, None, id_favorecido)
    )

    implantacao_id = result.get('id') if result else None
    if not implantacao_id:
        raise Exception("Falha ao obter ID da nova implantação de módulo.")

    modulo_label = MODULO_OPCOES.get(modulo_tipo, modulo_tipo)
    logar_timeline(implantacao_id, usuario_criador, 'implantacao_criada', f'Implantação de Módulo "{nome_empresa}" (módulo: {modulo_label}) criada e atribuída a {usuario_atribuido}.')

    return implantacao_id


def iniciar_implantacao_service(implantacao_id, usuario_cs_email):
    """
    Inicia uma implantação (muda status para 'andamento').
    """
    impl = query_db(
        "SELECT usuario_cs, nome_empresa, status, tipo FROM implantacoes WHERE id = %s",
        (implantacao_id,), one=True
    )

    if not impl:
        raise ValueError('Implantação não encontrada.')
    
    if impl.get('usuario_cs') != usuario_cs_email:
        raise ValueError('Operação negada. Implantação não pertence a você.')

    if impl.get('status') not in ['nova', 'futura', 'sem_previsao']:
        raise ValueError(f'Operação negada. Implantação com status "{impl.get("status")}" não pode ser iniciada.')

    agora = datetime.now()
    novo_tipo = impl.get('tipo')
    if novo_tipo == 'futura':
        novo_tipo = 'completa'

    execute_db(
        "UPDATE implantacoes SET tipo = %s, status = 'andamento', data_inicio_efetivo = %s, data_inicio_previsto = NULL WHERE id = %s",
        (novo_tipo, agora, implantacao_id)
    )
    logar_timeline(implantacao_id, usuario_cs_email, 'status_alterado', f'Implantação "{impl.get("nome_empresa", "N/A")}" iniciada.')
    
    return True


def agendar_implantacao_service(implantacao_id, usuario_cs_email, data_prevista_iso):
    """
    Agenda uma implantação (muda status para 'futura').
    """
    impl = query_db(
        "SELECT usuario_cs, nome_empresa, status, plano_sucesso_id FROM implantacoes WHERE id = %s",
        (implantacao_id,), one=True
    )

    if not impl:
        raise ValueError('Implantação não encontrada.')

    if impl.get('usuario_cs') != usuario_cs_email:
        raise ValueError('Operação negada. Implantação não pertence a você.')

    if impl.get('status') != 'nova':
        raise ValueError('Apenas implantações "Novas" podem ser agendadas.')

    execute_db(
        "UPDATE implantacoes SET status = 'futura', data_inicio_previsto = %s WHERE id = %s",
        (data_prevista_iso, implantacao_id)
    )
    logar_timeline(implantacao_id, usuario_cs_email, 'status_alterado', f'Início da implantação "{impl.get("nome_empresa")}" agendado para {data_prevista_iso}.')
    
    return impl.get("nome_empresa")


def marcar_sem_previsao_service(implantacao_id, usuario_cs_email):
    """
    Marca uma implantação como 'sem_previsao'.
    """
    impl = query_db(
        "SELECT usuario_cs, nome_empresa, status FROM implantacoes WHERE id = %s",
        (implantacao_id,), one=True
    )

    if not impl:
        raise ValueError('Implantação não encontrada.')

    if impl.get('usuario_cs') != usuario_cs_email:
        raise ValueError('Operação negada. Implantação não pertence a você.')

    if impl.get('status') != 'nova':
        raise ValueError('Apenas implantações "Novas" podem ser marcadas como Sem previsão.')

    updated = execute_db(
        "UPDATE implantacoes SET status = 'sem_previsao', data_inicio_previsto = NULL WHERE id = %s",
        (implantacao_id,)
    )
    if not updated:
        raise Exception('Falha ao atualizar status para Sem previsão.')

    logar_timeline(implantacao_id, usuario_cs_email, 'status_alterado', f'Implantação "{impl.get("nome_empresa")}" marcada como "Sem previsão".')
    
    return impl.get("nome_empresa")


def finalizar_implantacao_service(implantacao_id, usuario_cs_email, data_final_iso):
    """
    Finaliza uma implantação.
    """
    impl = query_db(
        "SELECT usuario_cs, nome_empresa, status, plano_sucesso_id FROM implantacoes WHERE id = %s",
        (implantacao_id,), one=True
    )
    
    if not impl:
        raise ValueError('Implantação não encontrada.')
    
    if impl.get('usuario_cs') != usuario_cs_email:
        raise ValueError('Permissão negada. Esta implantação não pertence a você.')
    
    if impl.get('status') != 'andamento':
        raise ValueError(f"Operação não permitida: status atual é '{impl.get('status')}'. Retome ou inicie antes de finalizar.")

    # Validação de pendências
    plano_id = impl.get('plano_sucesso_id')
    if plano_id:
        subtarefas_pendentes = query_db(
            """
            SELECT COUNT(*) as total
            FROM checklist_items
            WHERE implantacao_id = %s
            AND tipo_item = 'subtarefa'
            AND completed = false
            """,
            (implantacao_id,), one=True
        ) or {}

        tarefas_pendentes_sem_sub = query_db(
            """
            SELECT COUNT(*) as total
            FROM checklist_items ci
            WHERE ci.implantacao_id = %s
            AND ci.tipo_item = 'tarefa'
            AND ci.completed = false
            AND NOT EXISTS (
                SELECT 1 FROM checklist_items s
                WHERE s.parent_id = ci.id
                AND s.tipo_item = 'subtarefa'
            )
            """,
            (implantacao_id,), one=True
        ) or {}

        total_pendentes = int(subtarefas_pendentes.get('total', 0) or 0) + int(tarefas_pendentes_sem_sub.get('total', 0) or 0)

        if total_pendentes > 0:
            nomes = query_db(
                """
                SELECT title as nome
                FROM checklist_items
                WHERE implantacao_id = %s
                  AND tipo_item = 'subtarefa'
                  AND completed = false
                ORDER BY title LIMIT 10
                """,
                (implantacao_id,)
            ) or []
            nomes_txt = ", ".join([n.get('nome') for n in nomes])
            raise ValueError(f'Não é possível finalizar: {total_pendentes} tarefa(s) do Plano de Sucesso pendente(s). Pendentes: {nomes_txt}...')

    execute_db(
        "UPDATE implantacoes SET status = 'finalizada', data_finalizacao = %s WHERE id = %s",
        (data_final_iso, implantacao_id)
    )
    logar_timeline(implantacao_id, usuario_cs_email, 'status_alterado', f'Implantação "{impl.get("nome_empresa", "N/A")}" finalizada.')
    
    return True


def parar_implantacao_service(implantacao_id, usuario_cs_email, user_perfil_acesso, data_parada_iso, motivo):
    """
    Para uma implantação.
    """
    impl = query_db(
        "SELECT usuario_cs, nome_empresa, status FROM implantacoes WHERE id = %s",
        (implantacao_id,), one=True
    )
    
    if not impl:
        raise ValueError('Implantação não encontrada.')

    is_owner = impl.get('usuario_cs') == usuario_cs_email
    is_manager = user_perfil_acesso in PERFIS_COM_GESTAO

    if not (is_owner or is_manager):
        raise ValueError('Permissão negada. Esta implantação não pertence a você.')

    if impl.get('status') != 'andamento':
        raise ValueError('Apenas implantações "Em Andamento" podem ser marcadas como "Parada".')

    execute_db(
        "UPDATE implantacoes SET status = 'parada', data_finalizacao = %s, motivo_parada = %s WHERE id = %s",
        (data_parada_iso, motivo, implantacao_id)
    )
    logar_timeline(implantacao_id, usuario_cs_email, 'status_alterado', f'Implantação "{impl.get("nome_empresa", "N/A")}" parada retroativamente em {data_parada_iso}. Motivo: {motivo}')
    
    return True


def retomar_implantacao_service(implantacao_id, usuario_cs_email, user_perfil_acesso):
    """
    Retoma uma implantação parada.
    """
    impl = query_db(
        "SELECT usuario_cs, nome_empresa, status FROM implantacoes WHERE id = %s",
        (implantacao_id,), one=True
    )
    
    if not impl:
        raise ValueError('Implantação não encontrada.')

    is_owner = impl.get('usuario_cs') == usuario_cs_email
    is_manager = user_perfil_acesso in PERFIS_COM_GESTAO

    if not (is_owner or is_manager):
        raise ValueError('Permissão negada. Esta implantação não pertence a você.')

    if impl.get('status') != 'parada':
        raise ValueError('Apenas implantações "Paradas" podem ser retomadas.')

    execute_db(
        "UPDATE implantacoes SET status = 'andamento', data_finalizacao = NULL, motivo_parada = '' WHERE id = %s",
        (implantacao_id,)
    )
    logar_timeline(implantacao_id, usuario_cs_email, 'status_alterado', f'Implantação "{impl.get("nome_empresa", "N/A")}" retomada.')
    
    return True


def reabrir_implantacao_service(implantacao_id, usuario_cs_email):
    """
    Reabre uma implantação finalizada.
    """
    impl = query_db(
        "SELECT usuario_cs, nome_empresa, status FROM implantacoes WHERE id = %s",
        (implantacao_id,), one=True
    )
    
    if not impl:
        raise ValueError('Implantação não encontrada.')
        
    if impl.get('usuario_cs') != usuario_cs_email:
        raise ValueError('Permissão negada.')

    if impl.get('status') != 'finalizada':
        raise ValueError('Apenas implantações "Finalizadas" podem ser reabertas.')

    execute_db(
        "UPDATE implantacoes SET status = 'andamento', data_finalizacao = NULL WHERE id = %s",
        (implantacao_id,)
    )
    logar_timeline(implantacao_id, usuario_cs_email, 'status_alterado', f'Implantação "{impl.get("nome_empresa", "N/A")}" reaberta.')
    
    return True


def atualizar_detalhes_empresa_service(implantacao_id, usuario_cs_email, user_perfil_acesso, campos):
    """
    Atualiza os detalhes da empresa de uma implantação.
    """
    impl = query_db("SELECT id, usuario_cs FROM implantacoes WHERE id = %s", (implantacao_id,), one=True)
    
    if not impl:
        raise ValueError('Implantação não encontrada.')

    is_owner = impl.get('usuario_cs') == usuario_cs_email
    is_manager = user_perfil_acesso in PERFIS_COM_GESTAO

    if not (is_owner or is_manager):
        raise ValueError('Permissão negada.')

    allowed_fields = {
        'email_responsavel',
        'responsavel_cliente',
        'cargo_responsavel',
        'telefone_responsavel',
        'data_inicio_producao',
        'data_final_implantacao',
        'data_inicio_efetivo',
        'data_previsao_termino',
        'id_favorecido',
        'nivel_receita',
        'chave_oamd',
        'tela_apoio_link',
        'informacao_infra',
        'seguimento',
        'tipos_planos',
        'modalidades',
        'horarios_func',
        'formas_pagamento',
        'diaria',
        'freepass',
        'alunos_ativos',
        'sistema_anterior',
        'importacao',
        'recorrencia_usa',
        'boleto',
        'nota_fiscal',
        'catraca',
        'modelo_catraca',
        'facial',
        'modelo_facial',
        'wellhub',
        'totalpass',
        'cnpj',
        'status_implantacao_oamd',
        'nivel_atendimento',
        'valor_atribuido',
        'data_cadastro',
        'resp_estrategico_nome',
        'resp_onb_nome',
        'resp_estrategico_obs',
        'contatos',
    }
    
    # Recalcular previsão se data_inicio_efetivo mudou
    if 'data_inicio_efetivo' in campos and campos['data_inicio_efetivo']:
        try:
            # Buscar info do plano atual
            info_plano = query_db(
                """
                SELECT p.dias_duracao 
                FROM implantacoes i 
                JOIN planos_sucesso p ON i.plano_sucesso_id = p.id 
                WHERE i.id = %s
                """, 
                (implantacao_id,), one=True
            )
            
            if info_plano and info_plano.get('dias_duracao'):
                dias = int(info_plano['dias_duracao'])
                dt_str = str(campos['data_inicio_efetivo'])[:10]
                dt_inicio = datetime.strptime(dt_str, '%Y-%m-%d')
                nova_prev = dt_inicio + timedelta(days=dias)
                
                # Atualizar campo de previsão
                campos['data_previsao_termino'] = nova_prev.strftime('%Y-%m-%d')
                current_app.logger.info(f"Previsão recalculada para {campos['data_previsao_termino']} (Início: {dt_str}, Duração: {dias} dias)")
        
        except Exception as e:
            current_app.logger.warning(f"Erro ao recalcular previsão de término: {e}")

    set_clauses = []
    values = []
    for k, v in campos.items():
        if k in allowed_fields:
            set_clauses.append(f"{k} = %s")
            values.append(v)
    if not set_clauses:
        return False
    values.append(implantacao_id)
    query = f"UPDATE implantacoes SET {', '.join(set_clauses)} WHERE id = %s"
    
    execute_db(query, tuple(values))
    
    return True


def remover_plano_implantacao_service(implantacao_id, usuario_cs_email, user_perfil_acesso):
    """
    Remove o plano de sucesso de uma implantação, limpando todas as fases/ações/tarefas associadas.
    """
    impl = query_db("SELECT id, usuario_cs, nome_empresa FROM implantacoes WHERE id = %s", (implantacao_id,), one=True)
    if not impl:
        raise ValueError('Implantação não encontrada.')

    is_owner = impl.get('usuario_cs') == usuario_cs_email
    is_manager = user_perfil_acesso in PERFIS_COM_GESTAO

    if not (is_owner or is_manager):
        raise ValueError('Permissão negada.')

    try:
        before = query_db("SELECT COUNT(*) as total FROM checklist_items WHERE implantacao_id = %s", (implantacao_id,), one=True) or {'total': 0}
        total_removed = int(before.get('total', 0) or 0)
    except Exception:
        total_removed = None

    execute_db("DELETE FROM checklist_items WHERE implantacao_id = %s", (implantacao_id,))

    execute_db(
        "UPDATE implantacoes SET plano_sucesso_id = NULL, data_atribuicao_plano = NULL, data_previsao_termino = NULL WHERE id = %s",
        (implantacao_id,)
    )

    detalhe = f'Plano de sucesso removido da implantação por {usuario_cs_email}.'
    if isinstance(total_removed, int):
        detalhe += f' Itens removidos: {total_removed}.'
    
    logar_timeline(
        implantacao_id,
        usuario_cs_email,
        'plano_removido',
        detalhe
    )


def transferir_implantacao_service(implantacao_id, usuario_cs_email, novo_usuario_cs):
    """
    Transfere a responsabilidade de uma implantação para outro usuário.
    """
    if not novo_usuario_cs or not implantacao_id:
        raise ValueError('Dados inválidos para transferência.')

    impl = query_db("SELECT nome_empresa, usuario_cs FROM implantacoes WHERE id = %s", (implantacao_id,), one=True)
    if not impl:
        raise ValueError('Implantação não encontrada.')

    antigo_usuario_cs = impl.get('usuario_cs', 'Ninguém')
    execute_db("UPDATE implantacoes SET usuario_cs = %s WHERE id = %s", (novo_usuario_cs, implantacao_id))
    
    logar_timeline(implantacao_id, usuario_cs_email, 'detalhes_alterados', f'Implantação "{impl.get("nome_empresa")}" transferida de {antigo_usuario_cs} para {novo_usuario_cs} por {usuario_cs_email}.')
    
    return antigo_usuario_cs


def excluir_implantacao_service(implantacao_id, usuario_cs_email, user_perfil_acesso):
    """
    Exclui permanentemente uma implantação e seus dados associados.
    """
    impl = query_db("SELECT id, usuario_cs FROM implantacoes WHERE id = %s", (implantacao_id,), one=True)
    is_owner = impl and impl.get('usuario_cs') == usuario_cs_email
    is_manager = user_perfil_acesso in PERFIS_COM_GESTAO
    
    if not (is_owner or is_manager):
        raise ValueError('Permissão negada.')

    # Buscar imagens de comentários para exclusão (R2)
    comentarios_img = query_db(
        """ SELECT DISTINCT c.imagem_url 
            FROM comentarios_h c 
            WHERE EXISTS (
                SELECT 1 FROM checklist_items ci 
                WHERE c.checklist_item_id = ci.id
                AND ci.implantacao_id = %s
            )
            AND c.imagem_url IS NOT NULL AND c.imagem_url != '' """,
        (implantacao_id,)
    )
    
    from ..core.extensions import r2_client
    
    public_url_base = current_app.config.get('CLOUDFLARE_PUBLIC_URL')
    bucket_name = current_app.config.get('CLOUDFLARE_BUCKET_NAME')
    
    if r2_client and public_url_base and bucket_name:
        for c in comentarios_img:
            imagem_url = c.get('imagem_url')
            if imagem_url and imagem_url.startswith(public_url_base):
                try:
                    object_key = imagem_url.replace(f"{public_url_base}/", "")
                    if object_key:
                        r2_client.delete_object(Bucket=bucket_name, Key=object_key)
                except Exception as e:
                    current_app.logger.warning(f"Falha ao excluir R2 (key: {object_key}): {e}")

    execute_db("DELETE FROM implantacoes WHERE id = %s", (implantacao_id,))


def cancelar_implantacao_service(implantacao_id, usuario_cs_email, user_perfil_acesso, data_cancelamento_iso, motivo, comprovante_url):
    """
    Cancela uma implantação.
    """
    impl = query_db("SELECT usuario_cs, nome_empresa, status FROM implantacoes WHERE id = %s", (implantacao_id,), one=True)

    is_owner = impl and impl.get('usuario_cs') == usuario_cs_email
    is_manager = user_perfil_acesso in PERFIS_COM_GESTAO

    if not (is_owner or is_manager):
        raise ValueError('Permissão negada para cancelar esta implantação.')

    if impl.get('status') in ['finalizada', 'cancelada']:
        raise ValueError(f'Implantação já está {impl.get("status")}.')

    if impl.get('status') == 'nova':
        raise ValueError('Ações indisponíveis para implantações "Nova". Inicie a implantação para habilitar cancelamento.')

    execute_db(
        "UPDATE implantacoes SET status = 'cancelada', data_cancelamento = %s, motivo_cancelamento = %s, comprovante_cancelamento_url = %s, data_finalizacao = CURRENT_TIMESTAMP WHERE id = %s",
        (data_cancelamento_iso, motivo, comprovante_url, implantacao_id)
    )

    logar_timeline(implantacao_id, usuario_cs_email, 'status_alterado', f'Implantação CANCELADA.\nMotivo: {motivo}\nData inf.: {format_date_br(data_cancelamento_iso)}')


def listar_implantacoes(user_email, status_filter=None, page=1, per_page=50, is_admin=False):
    """
    Lista implantações com paginação e filtro.
    Substitui a lógica do endpoint GET /api/v1/implantacoes.
    """
    try:
        page = int(page)
        per_page = int(per_page)
        per_page = min(per_page, 200)
    except (TypeError, ValueError):
        page = 1
        per_page = 50

    offset = (page - 1) * per_page
    
    # Base query reconstruction
    where_clauses = []
    params = []
    
    # If not admin, filter by user
    if not is_admin: 
        where_clauses.append("i.usuario_cs = %s")
        params.append(user_email)
    
    if status_filter:
        where_clauses.append("i.status = %s")
        params.append(status_filter)
        
    where_str = " WHERE " + " AND ".join(where_clauses) if where_clauses else ""
    
    query = f"""
        SELECT i.*, p.nome as cs_nome
        FROM implantacoes i
        LEFT JOIN perfil_usuario p ON i.usuario_cs = p.usuario
        {where_str}
        ORDER BY i.data_criacao DESC LIMIT %s OFFSET %s
    """
    
    # query param arguments
    query_args = params + [per_page, offset]
    
    try:
        implantacoes = query_db(query, tuple(query_args)) or []
    except Exception as e:
        current_app.logger.error(f"Erro ao listar implantações: {e}")
        implantacoes = []

    # Count query
    count_query = f"SELECT COUNT(*) as total FROM implantacoes i {where_str}"
    try:
        total_result = query_db(count_query, tuple(params), one=True)
        total = total_result.get('total', 0) if total_result else 0
    except Exception:
        total = 0

    return {
        'data': implantacoes,
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': total,
            'pages': (total + per_page - 1) // per_page
        }
    }


def obter_implantacao_basica(impl_id, user_email, is_manager=False):
    """
    Retorna detalhes básicos de uma implantação e sua hierarquia.
    Substitui a lógica do endpoint GET /api/v1/implantacoes/<id>.
    """
    
    query_base = """
        SELECT i.*, p.nome as cs_nome
        FROM implantacoes i
        LEFT JOIN perfil_usuario p ON i.usuario_cs = p.usuario
        WHERE i.id = %s
    """
    params = [impl_id]
    
    if not is_manager:
        query_base += " AND i.usuario_cs = %s"
        params.append(user_email)
        
    impl = query_db(query_base, tuple(params), one=True)
    
    if not impl:
        return None
        
    # Normalizar datas
    impl = _format_implantacao_dates(impl)
    
    # Obter Hierarquia
    hierarquia = get_hierarquia_implantacao(impl_id)
    
    return {
        'implantacao': impl,
        'hierarquia': hierarquia
    }


def consultar_dados_oamd(impl_id=None, user_email=None, id_favorecido_direto=None):
    """
    Consulta dados externos (OAMD) para uma implantação.
    Substitui a lógica de GET /api/v1/oamd/implantacoes/<id>/consulta.
    
    Args:
        impl_id: ID da implantação (opcional se id_favorecido_direto for fornecido)
        user_email: Email do usuário
        id_favorecido_direto: ID Favorecido direto (opcional, usado quando implantação não existe)
    """
    from ..domain.external_service import consultar_empresa_oamd as svc_consultar_empresa
    
    # Inicializar variáveis
    id_favorecido = id_favorecido_direto
    infra_req = None
    
    # Se impl_id foi fornecido, tentar buscar dados locais
    if impl_id:
        impl = query_db(
            "SELECT id, id_favorecido, chave_oamd, informacao_infra, tela_apoio_link FROM implantacoes WHERE id = %s", 
            (impl_id,), one=True
        )
        
        if impl:
            # Usar id_favorecido da implantação se não foi fornecido diretamente
            if not id_favorecido:
                id_favorecido = impl.get('id_favorecido')
            infra_req = impl.get('informacao_infra')
    
    # Se não temos id_favorecido de nenhuma fonte, erro
    if not id_favorecido and not infra_req:
        raise ValueError('Implantação não encontrada e nenhum ID Favorecido fornecido')
    
    # Extract numeric part from infra if possible as fallback
    infra_digits = None
    if infra_req:
        import re
        m = re.search(r"(\d+)", str(infra_req))
        if m:
            infra_digits = m.group(1)
            
    # Call external service
    result = svc_consultar_empresa(id_favorecido=id_favorecido, infra_req=infra_digits if not id_favorecido else None)
    
    if not result.get('ok') or not result.get('mapped'):
        # Construir link de apoio
        if id_favorecido:
             link = f"https://app.pactosolucoes.com.br/apoio/apoio/{id_favorecido}"
        else:
             link = ''
             
        return {
            'persistibles': {},
            'extras': {},
            'derived': {'tela_apoio_link': link},
            'found': False
        }

    mapped = result.get('mapped', {})
    empresa = result.get('empresa', {})
    
    # Construir persistibles (dados que podem ser salvos na tabela implantacoes)
    persistibles = {
        'id_favorecido': empresa.get('codigofinanceiro') or id_favorecido,
        'chave_oamd': mapped.get('chave_oamd'),
        'cnpj': mapped.get('cnpj'),
        'data_cadastro': mapped.get('data_cadastro'),
        'status_implantacao': mapped.get('status_implantacao'),
    }
    
    # Refinando com dados crus da empresa se mapped não tiver tudo
    if 'tipocliente' in empresa: persistibles['tipo_do_cliente'] = empresa['tipocliente']
    if 'inicioimplantacao' in empresa: persistibles['inicio_implantacao'] = empresa['inicioimplantacao']
    if 'finalimplantacao' in empresa: persistibles['final_implantacao'] = empresa['finalimplantacao']
    if 'inicioproducao' in empresa: persistibles['inicio_producao'] = empresa['inicioproducao']
    if 'nivelreceitamensal' in empresa: persistibles['nivel_receita_do_cliente'] = empresa['nivelreceitamensal']
    if 'categoria' in empresa: persistibles['categorias'] = empresa['categoria']
    if 'nivelatendimento' in empresa: persistibles['nivel_atendimento'] = empresa['nivelatendimento']
    if 'condicaoespecial' in empresa: persistibles['condicao_especial'] = empresa['condicaoespecial']
    if 'cs_nome' in empresa: persistibles['analista_cs_responsavel'] = empresa['cs_nome']
    if 'cs_url' in empresa: persistibles['link_agendamento_cs'] = empresa['cs_url']
    if 'cs_telefone' in empresa: persistibles['telefone_cs'] = empresa['cs_telefone']

    # Derived
    derived = {}
    if mapped.get('informacao_infra'):
        derived['informacao_infra'] = mapped['informacao_infra']
    if mapped.get('tela_apoio_link'):
        derived['tela_apoio_link'] = mapped['tela_apoio_link']
        
    # Extras
    extras = {
        'nome_fantasia': empresa.get('nomefantasia'),
        'razao_social': empresa.get('razaosocial'),
        'endereco': empresa.get('endereco'),
        'bairro': empresa.get('bairro'),
        'cidade': empresa.get('cidade'),
        'estado': empresa.get('estado'),
        'nicho': empresa.get('nicho'),
        'ultima_atualizacao': empresa.get('ultimaatualizacao')
    }
    
    return {'persistibles': persistibles, 'derived': derived, 'extras': extras, 'found': True}


def aplicar_dados_oamd(impl_id, user_email, updates_dict):
    """
    Aplica atualizações OAMD na implantação.
    Substitui POST /api/v1/oamd/implantacoes/<id>/aplicar
    """
    
    # Validar implantação
    impl = query_db("SELECT id FROM implantacoes WHERE id = %s", (impl_id,), one=True)
    if not impl:
        raise ValueError('Implantação não encontrada')
        
    allowed_fields = [
        'id_favorecido', 'chave_oamd', 'informacao_infra', 'tela_apoio_link',
        'status_implantacao_oamd', 'nivel_atendimento', 'cnpj', 'data_cadastro', 'valor_atribuido'
    ]
    filtered_updates = {k: v for k, v in updates_dict.items() if k in allowed_fields}
    
    if not filtered_updates:
        return {'updated': False}
        
    set_clauses = []
    values = []
    for k, v in filtered_updates.items():
        set_clauses.append(f"{k} = %s")
        values.append(v)
    
    values.append(impl_id)
    
    with db_transaction_with_lock() as (conn, cursor, db_type):
        sql = f"UPDATE implantacoes SET {', '.join(set_clauses)} WHERE id = %s"
        if db_type == 'sqlite':
            sql = sql.replace('%s', '?')
        cursor.execute(sql, tuple(values))
        conn.commit()
    
    return {'updated': True, 'fields': filtered_updates}