
from flask import g, current_app
from ..db import query_db, execute_db, logar_timeline
from functools import wraps

from ..domain.task_definitions import (
    CHECKLIST_OBRIGATORIO_ITEMS, MODULO_OBRIGATORIO,
    TAREFAS_TREINAMENTO_PADRAO, MODULO_PENDENCIAS, TASK_TIPS
)

from ..domain.hierarquia_service import get_hierarquia_implantacao
from ..constants import (
    PERFIS_COM_GESTAO, 
    JUSTIFICATIVAS_PARADA, CARGOS_RESPONSAVEL, NIVEIS_RECEITA, 
    SEGUIMENTOS_LIST, TIPOS_PLANOS, MODALIDADES_LIST,
    HORARIOS_FUNCIONAMENTO, FORMAS_PAGAMENTO, SISTEMAS_ANTERIORES,
    RECORRENCIA_USADA, SIM_NAO_OPTIONS
)

from ..common.utils import format_date_iso_for_json, format_date_br
from datetime import datetime
from collections import OrderedDict

# Importar cache
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
            # Se não há cache configurado, executar função normalmente
            if not cache:
                return func(impl_id, *args, **kwargs)
            
            cache_key = f'progresso_impl_{impl_id}'
            
            try:
                # Tentar obter do cache
                cached_result = cache.get(cache_key)
                
                if cached_result is not None:
                    return cached_result
                
                # Calcular resultado
                result = func(impl_id, *args, **kwargs)
                
                # Armazenar no cache
                cache.set(cache_key, result, timeout=ttl)
                
                return result
            except Exception as e:
                # Se houver erro no cache, executar função normalmente
                current_app.logger.warning(f"Erro no cache de progresso para impl_id {impl_id}: {e}")
                return func(impl_id, *args, **kwargs)
        
        return wrapper
    return decorator 

def _get_progress_optimized(impl_id):
    """
    Versão otimizada que usa uma única query com CTE/UNION.
    Reduz de 3 queries para 1 query única.
    """
    try:
        fases_exist = query_db("SELECT id FROM fases WHERE implantacao_id = %s LIMIT 1", (impl_id,), one=True)
    except Exception:
        fases_exist = None
    
    if not fases_exist:
        # Se não há fases, retornar 0 (sem progresso)
        return 0, 0, 0
    
    # Detectar tipo de banco de dados
    is_sqlite = current_app.config.get('USE_SQLITE_LOCALLY', False)
    
    try:
        if is_sqlite:
            # SQLite: usar CTE (SQLite suporta CTE desde versão 3.8.3)
            query = """
                WITH subtarefas_count AS (
                    SELECT 
                        COUNT(*) as total,
                        SUM(CASE WHEN concluido = 1 THEN 1 ELSE 0 END) as done
                    FROM subtarefas_h s
                    JOIN tarefas_h th ON s.tarefa_id = th.id
                    JOIN grupos g ON th.grupo_id = g.id
                    JOIN fases f ON g.fase_id = f.id
                    WHERE f.implantacao_id = ?
                ),
                tarefas_count AS (
                    SELECT 
                        COUNT(*) as total,
                        SUM(CASE WHEN LOWER(COALESCE(status, '')) = 'concluida' THEN 1 ELSE 0 END) as done
                    FROM tarefas_h th
                    LEFT JOIN subtarefas_h s ON s.tarefa_id = th.id
                    JOIN grupos g ON th.grupo_id = g.id
                    JOIN fases f ON g.fase_id = f.id
                    WHERE f.implantacao_id = ? AND s.id IS NULL
                )
                SELECT 
                    COALESCE((SELECT total FROM subtarefas_count), 0) + COALESCE((SELECT total FROM tarefas_count), 0) as total,
                    COALESCE((SELECT done FROM subtarefas_count), 0) + COALESCE((SELECT done FROM tarefas_count), 0) as done
            """
            result = query_db(query, (impl_id, impl_id), one=True) or {}
            
            total = int(result.get('total', 0) or 0)
            done = int(result.get('done', 0) or 0)
        else:
            # PostgreSQL: usar CTE (Common Table Expression)
            query = """
                WITH subtarefas_count AS (
                    SELECT 
                        COUNT(*) as total,
                        SUM(CASE WHEN concluido THEN 1 ELSE 0 END) as done
                    FROM subtarefas_h s
                    JOIN tarefas_h th ON s.tarefa_id = th.id
                    JOIN grupos g ON th.grupo_id = g.id
                    JOIN fases f ON g.fase_id = f.id
                    WHERE f.implantacao_id = %s
                ),
                tarefas_count AS (
                    SELECT 
                        COUNT(*) as total,
                        SUM(CASE WHEN LOWER(COALESCE(status, '')) = 'concluida' THEN 1 ELSE 0 END) as done
                    FROM tarefas_h th
                    LEFT JOIN subtarefas_h s ON s.tarefa_id = th.id
                    JOIN grupos g ON th.grupo_id = g.id
                    JOIN fases f ON g.fase_id = f.id
                    WHERE f.implantacao_id = %s AND s.id IS NULL
                )
                SELECT 
                    COALESCE((SELECT total FROM subtarefas_count), 0) + COALESCE((SELECT total FROM tarefas_count), 0) as total,
                    COALESCE((SELECT done FROM subtarefas_count), 0) + COALESCE((SELECT done FROM tarefas_count), 0) as done
            """
            result = query_db(query, (impl_id, impl_id), one=True) or {}
            
            total = int(result.get('total', 0) or 0)
            done = int(result.get('done', 0) or 0)
        
        return int(round((done / total) * 100)) if total > 0 else 100, total, done
        
    except Exception as e:
        current_app.logger.error(f"Erro ao calcular progresso otimizado para impl_id {impl_id}: {e}", exc_info=True)
        # Fallback para versão não otimizada em caso de erro
        return _get_progress_legacy(impl_id)


def _get_progress_legacy(impl_id):
    """Versão legada (3 queries separadas) - mantida como fallback"""
    try:
        fases_exist = query_db("SELECT id FROM fases WHERE implantacao_id = %s LIMIT 1", (impl_id,), one=True)
    except Exception:
        fases_exist = None
    
    if fases_exist:
        # Buscar subtarefas hierárquicas
        sub = query_db(
            """
            SELECT COUNT(s.id) as total, SUM(CASE WHEN s.concluido THEN 1 ELSE 0 END) as done
            FROM subtarefas_h s
            JOIN tarefas_h th ON s.tarefa_id = th.id
            JOIN grupos g ON th.grupo_id = g.id
            JOIN fases f ON g.fase_id = f.id
            WHERE f.implantacao_id = %s
            """,
            (impl_id,), one=True
        ) or {}
        
        # Buscar tarefas hierárquicas sem subtarefas
        th_no = query_db(
            """
            SELECT COUNT(th.id) as total,
                   SUM(CASE WHEN LOWER(COALESCE(th.status,'')) = 'concluida' THEN 1 ELSE 0 END) as done
            FROM tarefas_h th
            LEFT JOIN subtarefas_h s ON s.tarefa_id = th.id
            JOIN grupos g ON th.grupo_id = g.id
            JOIN fases f ON g.fase_id = f.id
            WHERE f.implantacao_id = %s AND s.id IS NULL
            """,
            (impl_id,), one=True
        ) or {}
        
        total = int(sub.get('total', 0) or 0) + int(th_no.get('total', 0) or 0)
        done = int(sub.get('done', 0) or 0) + int(th_no.get('done', 0) or 0)
        return int(round((done / total) * 100)) if total > 0 else 100, total, done
    
    # Se não há fases, retornar 0 (sem progresso)
    return 0, 0, 0


@cached_progress(ttl=30)
def _get_progress(impl_id):
    """
    Calcula progresso da implantação usando apenas modelo hierárquico.
    Usa versão otimizada se habilitada via feature flag.
    """
    # Feature flag para migração gradual
    use_optimized = current_app.config.get('USE_OPTIMIZED_PROGRESS', True)
    
    if use_optimized:
        return _get_progress_optimized(impl_id)
    else:
        return _get_progress_legacy(impl_id)


def auto_finalizar_implantacao(impl_id, usuario_cs_email):
    """
    Verifica se todas as tarefas hierárquicas estão concluídas
    e, em caso afirmativo, finaliza a implantação.
    """
    # Verificar se há fases (modelo hierárquico)
    fases_exist = query_db("SELECT id FROM fases WHERE implantacao_id = %s LIMIT 1", (impl_id,), one=True)
    
    if not fases_exist:
        # Sem fases, não pode auto-finalizar
        return False, None

    # Buscar subtarefas não concluídas
    subtarefas_pendentes = query_db(
        """
        SELECT COUNT(s.id) as total
        FROM subtarefas_h s
        JOIN tarefas_h th ON s.tarefa_id = th.id
        JOIN grupos g ON th.grupo_id = g.id
        JOIN fases f ON g.fase_id = f.id
        WHERE f.implantacao_id = %s AND s.concluido = 0
        """,
        (impl_id,), one=True
    ) or {}

    # Buscar tarefas sem subtarefas não concluídas
    tarefas_pendentes = query_db(
        """
        SELECT COUNT(th.id) as total
        FROM tarefas_h th
        LEFT JOIN subtarefas_h s ON s.tarefa_id = th.id
        JOIN grupos g ON th.grupo_id = g.id
        JOIN fases f ON g.fase_id = f.id
        WHERE f.implantacao_id = %s 
        AND s.id IS NULL 
        AND LOWER(COALESCE(th.status,'')) != 'concluida'
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
    return implantacao

def _get_comentarios_bulk(impl_id, is_owner=False, is_manager=False):
    """
    Busca TODOS os comentários de uma implantação em uma única query (ou poucas queries).
    Retorna dicionário indexado por item_id para acesso rápido.
    
    Otimização: Reduz de N+1 queries (uma por tarefa/subtarefa) para 2 queries totais
    (uma para comentarios_h e uma para comentarios legado).
    
    Returns:
        dict: {
            'tarefa_h_{id}': [comentario1, comentario2, ...],
            'subtarefa_h_{id}': [comentario1, comentario2, ...],
            'tarefa_{id}': [comentario1, comentario2, ...]  # modelo antigo
        }
    """
    comentarios_map = {}
    
    # Comentários do modelo hierárquico (novo) - uma única query
    try:
        comentarios_h_raw = query_db(
            """
            SELECT c.*, 
                   COALESCE(p.nome, c.usuario_cs) as usuario_nome,
                   c.data_criacao as data_criacao_raw,
                   c.subtarefa_h_id,
                   c.tarefa_h_id
            FROM comentarios_h c
            LEFT JOIN perfil_usuario p ON c.usuario_cs = p.usuario
            WHERE EXISTS (
                SELECT 1 FROM subtarefas_h s
                JOIN tarefas_h th_sub ON s.tarefa_id = th_sub.id
                JOIN grupos g_sub ON th_sub.grupo_id = g_sub.id
                JOIN fases f_sub ON g_sub.fase_id = f_sub.id
                WHERE (c.subtarefa_h_id = s.id AND f_sub.implantacao_id = %s)
            ) OR EXISTS (
                SELECT 1 FROM tarefas_h th
                JOIN grupos g ON th.grupo_id = g.id
                JOIN fases f ON g.fase_id = f.id
                WHERE (c.tarefa_h_id = th.id AND f.implantacao_id = %s)
            )
            ORDER BY c.data_criacao DESC
            """,
            (impl_id, impl_id)
        ) or []
    except Exception as e:
        from ..config.logging_config import get_logger
        logger = get_logger('implantacao')
        logger.warning(f"Erro ao buscar comentarios_h em bulk para implantação {impl_id}: {e}")
        comentarios_h_raw = []
    
    # Agrupar comentários hierárquicos (concatenação feita no Python para compatibilidade)
    for c in comentarios_h_raw:
        # Determinar item_key baseado em qual campo está preenchido
        if c.get('subtarefa_h_id'):
            item_key = f"subtarefa_h_{c['subtarefa_h_id']}"
        elif c.get('tarefa_h_id'):
            item_key = f"tarefa_h_{c['tarefa_h_id']}"
        else:
            continue  # Comentário sem associação válida
        
        # Filtrar por visibilidade se necessário
        if not (is_owner or is_manager):
            if c.get('visibilidade') == 'interno':
                continue
        
        # Formatar comentário igual ao código original
        c_formatado = {
            **c,
            'data_criacao_fmt_d': format_date_br(c.get('data_criacao_raw'))
        }
        c_formatado['delete_url'] = f"/api/excluir_comentario_h/{c['id']}"
        c_formatado['email_url'] = f"/api/enviar_email_comentario_h/{c['id']}"
        
        if item_key not in comentarios_map:
            comentarios_map[item_key] = []
        comentarios_map[item_key].append(c_formatado)
    
    # Comentários do modelo antigo (legado) - REMOVIDO
    # O modelo legado foi completamente removido do projeto
    
    return comentarios_map

def _get_tarefas_and_comentarios(impl_id, is_owner=False, is_manager=False):
    # Buscar todos os comentários de uma vez (otimização N+1)
    comentarios_map = _get_comentarios_bulk(impl_id, is_owner, is_manager)
    
    tarefas_agrupadas_treinamento = OrderedDict()
    tarefas_agrupadas_obrigatorio = OrderedDict()
    tarefas_agrupadas_pendencias = OrderedDict()
    todos_modulos_temp = set()

    try:
        fases_raw = query_db("SELECT id, nome, ordem FROM fases WHERE implantacao_id = %s ORDER BY ordem DESC", (impl_id,)) or []
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
                grupos_raw = query_db("SELECT id, nome FROM grupos WHERE fase_id = %s", (fase['id'],)) or []
            except Exception as e:
                from ..config.logging_config import get_logger
                logger = get_logger('implantacao')
                logger.warning(f"Erro ao buscar grupos para fase {fase.get('id')}: {e}")
                grupos_raw = []
            
            for grupo in grupos_raw:
                modulo_nome = grupo.get('nome') or f"Grupo {grupo.get('id')}"
                todos_modulos_temp.add(modulo_nome)
                try:
                    tarefas_h_raw = query_db("SELECT * FROM tarefas_h WHERE grupo_id = %s", (grupo['id'],)) or []
                except Exception as e:
                    from ..config.logging_config import get_logger
                    logger = get_logger('implantacao')
                    logger.warning(f"Erro ao buscar tarefas_h para grupo {grupo.get('id')}: {e}")
                    tarefas_h_raw = []
                ordem_c = 1
                for th in tarefas_h_raw:
                        try:
                            subs_raw = query_db("SELECT * FROM subtarefas_h WHERE tarefa_id = %s", (th['id'],)) or []
                        except Exception as e:
                            from ..config.logging_config import get_logger
                            logger = get_logger('implantacao')
                            logger.warning(f"Erro ao buscar subtarefas_h para tarefa {th.get('id')}: {e}")
                            subs_raw = []
                        if subs_raw:
                            for sub in subs_raw:
                                # OTIMIZAÇÃO: Usar comentários do mapa ao invés de query individual
                                comentarios_sub = comentarios_map.get(f"subtarefa_h_{sub['id']}", [])

                                tarefas_agrupadas_treinamento.setdefault(modulo_nome, []).append({
                                    'id': sub['id'],
                                    'tarefa_filho': sub.get('nome'),
                                    'concluida': bool(sub.get('concluido')), 
                                    'tag': '',
                                    'ordem': sub.get('ordem', ordem_c),
                                    'comentarios': comentarios_sub,  # Comentários já formatados e ordenados do mapa
                                    'toggle_url': f"/api/toggle_subtarefa_h/{sub['id']}",
                                    'comment_url': f"/api/adicionar_comentario_h/subtarefa/{sub['id']}"
                                })
                                tarefas_agrupadas_treinamento[modulo_nome].sort(key=lambda x: x.get('ordem', 0))
                                tarefas_agrupadas_treinamento[modulo_nome][-1]['delete_url'] = f"/api/excluir_subtarefa_h/{sub['id']}"
                                ordem_c += 1
                        else:
                            concl = True if (th.get('status') or '').lower() == 'concluida' else False
                            
                            # OTIMIZAÇÃO: Usar comentários do mapa ao invés de query individual
                            comentarios_th = comentarios_map.get(f"tarefa_h_{th['id']}", [])

                            tarefas_agrupadas_treinamento.setdefault(modulo_nome, []).append({
                                'id': th['id'],
                                'tarefa_filho': th.get('nome'),
                                'concluida': concl,
                                'tag': '',
                                'ordem': th.get('ordem', ordem_c),
                                'comentarios': comentarios_th,  # Comentários já formatados e ordenados do mapa
                                'toggle_url': f"/api/toggle_tarefa_h/{th['id']}",
                                'comment_url': f"/api/adicionar_comentario_h/tarefa/{th['id']}"
                            })
                            tarefas_agrupadas_treinamento[modulo_nome].sort(key=lambda x: x.get('ordem', 0))
                            tarefas_agrupadas_treinamento[modulo_nome][-1]['delete_url'] = f"/api/excluir_tarefa_h/{th['id']}"
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

    # Ordenação de módulos visíveis também segue a ordem derivada das tarefas (maior primeiro)
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
    return logs_timeline

def get_implantacao_details(impl_id, usuario_cs_email, user_perfil):
    """
    Busca, processa e valida todos os dados para a página de detalhes da implantação.
    Levanta um ValueError se o acesso for negado.
    """
    from ..config.logging_config import get_logger
    logger = get_logger('implantacao')
    
    # Garantir que user_perfil seja um dicionário
    if user_perfil is None:
        user_perfil = {}
    
    logger.info(f"Iniciando get_implantacao_details para ID {impl_id}, usuário {usuario_cs_email}")
    
    try:
        implantacao, is_manager = _get_implantacao_and_validate_access(impl_id, usuario_cs_email, user_perfil)
        logger.info(f"Acesso validado para implantação {impl_id}. Is_manager: {is_manager}")
    except ValueError as e:
        logger.warning(f"Acesso negado à implantação {impl_id}: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Erro ao validar acesso à implantação {impl_id}: {e}", exc_info=True)
        raise
    
    try:
        implantacao = _format_implantacao_dates(implantacao)
        logger.debug(f"Datas formatadas para implantação {impl_id}")
    except Exception as e:
        logger.error(f"Erro ao formatar datas da implantação {impl_id}: {e}", exc_info=True)
        raise

    try:
        progresso, _, _ = _get_progress(impl_id)
        logger.debug(f"Progresso calculado para implantação {impl_id}: {progresso}%")
    except Exception as e:
        logger.error(f"Erro ao calcular progresso da implantação {impl_id}: {e}", exc_info=True)
        raise

    try:
        is_owner = implantacao.get('usuario_cs') == usuario_cs_email
        tarefas_agrupadas_obrigatorio, ordered_treinamento, tarefas_agrupadas_pendencias, todos_modulos_lista = _get_tarefas_and_comentarios(impl_id, is_owner=is_owner, is_manager=is_manager)
        logger.debug(f"Tarefas carregadas para implantação {impl_id}")
    except Exception as e:
        logger.error(f"Erro ao carregar tarefas da implantação {impl_id}: {e}", exc_info=True)
        raise
    
    try:
        # Buscar hierarquia completa (novo modelo)
        hierarquia = get_hierarquia_implantacao(impl_id)
        logger.debug(f"Hierarquia carregada para implantação {impl_id}: {len(hierarquia.get('fases', []))} fases")
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        logger.warning(f"Erro ao carregar hierarquia da implantação {impl_id}: {e}\n{error_trace}. Usando estrutura vazia.")
        hierarquia = {'fases': []}

    try:
        logs_timeline = _get_timeline_logs(impl_id)
        logger.debug(f"Timeline carregada para implantação {impl_id}: {len(logs_timeline)} eventos")
    except Exception as e:
        logger.error(f"Erro ao carregar timeline da implantação {impl_id}: {e}", exc_info=True)
        raise

    nome_usuario_logado = user_perfil.get('nome', usuario_cs_email) if user_perfil else usuario_cs_email

    # Carregar lista de CS users para permitir transferência
    all_cs_users = []
    try:
        all_cs_users = query_db("SELECT usuario, nome FROM perfil_usuario WHERE perfil_acesso IS NOT NULL AND perfil_acesso != '' ORDER BY nome")
        all_cs_users = all_cs_users if all_cs_users is not None else []
        logger.debug(f"Lista de CS users carregada: {len(all_cs_users)} usuários")
    except Exception as e:
        logger.error(f"Erro ao carregar lista de CS users: {e}", exc_info=True)
        all_cs_users = []

    # Buscar plano de sucesso aplicado
    plano_sucesso_info = None
    try:
        if implantacao.get('plano_sucesso_id'):
            logger.debug(f"Buscando plano de sucesso ID {implantacao['plano_sucesso_id']}")
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
        # Tabela planos_sucesso pode não existir ainda
        pass

    # Buscar checklist hierárquico (novo modelo)
    checklist_tree = None
    checklist_nested = None
    try:
        from ..domain.checklist_service import get_checklist_tree, build_nested_tree
        checklist_flat = get_checklist_tree(
            implantacao_id=impl_id,
            include_progress=True
        )
        if checklist_flat:
            checklist_nested = build_nested_tree(checklist_flat)
            logger.info(f"Checklist carregado para implantação {impl_id}: {len(checklist_flat)} itens")
        else:
            logger.debug(f"Nenhum item de checklist encontrado para implantação {impl_id}")
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        logger.warning(f"Erro ao carregar checklist da implantação {impl_id}: {e}\n{error_trace}. Usando checklist vazio.")
        checklist_nested = []

    logger.info(f"get_implantacao_details concluído com sucesso para ID {impl_id}")
    
    # Obter user_info do contexto g se disponível, caso contrário usar dados do perfil
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
        'checklist_tree': checklist_nested  # Árvore aninhada do checklist hierárquico
    }
