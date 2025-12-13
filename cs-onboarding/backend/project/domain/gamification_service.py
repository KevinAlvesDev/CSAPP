import calendar
from collections import OrderedDict
from datetime import date, datetime

from ..db import execute_db, query_db


def _get_gamification_rules_as_dict():
    """Busca todas as regras do DB e retorna um dicionário (com cache)."""
    from flask import current_app

    from ..core.extensions import gamification_rules_cache

    cache_key = 'gamification_rules_dict'
    if cache_key in gamification_rules_cache:
        cached_result = gamification_rules_cache[cache_key]
        if cached_result:  # Se o cache tem dados, retornar
            return cached_result
        # Se o cache está vazio, tentar buscar novamente

    try:
        regras_raw = query_db("SELECT regra_id, valor_pontos FROM gamificacao_regras")
        if not regras_raw:
            current_app.logger.warning("Tabela gamificacao_regras está vazia. Verifique se as regras foram inseridas.")
            result = {}
        else:
            result = {r['regra_id']: r['valor_pontos'] for r in regras_raw}
            current_app.logger.info(f"Carregadas {len(result)} regras de gamificação do banco de dados.")

        gamification_rules_cache[cache_key] = result
        return result
    except Exception as e:
        current_app.logger.error(f"Erro ao buscar regras de gamificação: {e}", exc_info=True)
        # Se a tabela não existir ainda, retornar dict vazio
        return {}


def _get_all_gamification_rules_grouped():
    """Busca todas as regras de gamificação e as agrupa por categoria (com cache)."""
    from ..core.extensions import gamification_rules_cache

    cache_key = 'gamification_rules_grouped'
    if cache_key in gamification_rules_cache:
        return gamification_rules_cache[cache_key]

    try:
        regras = query_db("SELECT * FROM gamificacao_regras ORDER BY categoria, id")
        if not regras:
            result = {}
        else:
            regras_agrupadas = OrderedDict()
            for regra in regras:
                categoria = regra['categoria']
                if categoria not in regras_agrupadas:
                    regras_agrupadas[categoria] = []
                regras_agrupadas[categoria].append(regra)
            result = regras_agrupadas

        gamification_rules_cache[cache_key] = result
        return result
    except Exception:
        # Se a tabela não existir ainda, retornar dict vazio
        return {}


def _get_gamification_automatic_data_bulk(mes, ano, primeiro_dia_str, fim_ultimo_dia_str, target_cs_email=None):
    """Busca todos os dados automáticos de todos os usuários de uma vez."""

    sql_finalizadas = """
        SELECT usuario_cs, data_criacao, data_finalizacao FROM implantacoes
        WHERE status = 'finalizada'
        AND data_finalizacao >= %s AND data_finalizacao <= %s
    """
    args_finalizadas = [primeiro_dia_str, fim_ultimo_dia_str]
    if target_cs_email:
        sql_finalizadas += " AND usuario_cs = %s"
        args_finalizadas.append(target_cs_email)

    impl_finalizadas_raw = query_db(sql_finalizadas, tuple(args_finalizadas))
    impl_finalizadas_raw = impl_finalizadas_raw if impl_finalizadas_raw is not None else []

    tma_data_map = {}
    for impl in impl_finalizadas_raw:
        if not isinstance(impl, dict): continue
        email = impl.get('usuario_cs')
        dt_criacao = impl.get('data_criacao')
        dt_finalizacao = impl.get('data_finalizacao')
        if not email or not dt_criacao or not dt_finalizacao:
            continue

        if email not in tma_data_map:
            tma_data_map[email] = {'total_dias': 0, 'count': 0}

        dt_criacao_datetime = None
        dt_finalizacao_datetime = None
        if isinstance(dt_criacao, str):
            try:
                dt_criacao_datetime = datetime.fromisoformat(dt_criacao.replace('Z', '+00:00'))
            except ValueError:
                try:
                    if '.' in dt_criacao:
                        dt_criacao_datetime = datetime.strptime(dt_criacao, '%Y-%m-%d %H:%M:%S.%f')
                    else:
                        dt_criacao_datetime = datetime.strptime(dt_criacao, '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    pass
        elif isinstance(dt_criacao, date) and not isinstance(dt_criacao, datetime):
            dt_criacao_datetime = datetime.combine(dt_criacao, datetime.min.time())
        elif isinstance(dt_criacao, datetime):
            dt_criacao_datetime = dt_criacao

        if isinstance(dt_finalizacao, str):
            try:
                dt_finalizacao_datetime = datetime.fromisoformat(dt_finalizacao.replace('Z', '+00:00'))
            except ValueError:
                try:
                    if '.' in dt_finalizacao:
                        dt_finalizacao_datetime = datetime.strptime(dt_finalizacao, '%Y-%m-%d %H:%M:%S.%f')
                    else:
                        dt_finalizacao_datetime = datetime.strptime(dt_finalizacao, '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    pass
        elif isinstance(dt_finalizacao, date) and not isinstance(dt_finalizacao, datetime):
            dt_finalizacao_datetime = datetime.combine(dt_finalizacao, datetime.min.time())
        elif isinstance(dt_finalizacao, datetime):
            dt_finalizacao_datetime = dt_finalizacao

        if dt_criacao_datetime and dt_finalizacao_datetime:
            criacao_naive = dt_criacao_datetime.replace(tzinfo=None) if dt_criacao_datetime.tzinfo else dt_criacao_datetime
            final_naive = dt_finalizacao_datetime.replace(tzinfo=None) if dt_finalizacao_datetime.tzinfo else dt_finalizacao_datetime
            try:
                delta = final_naive - criacao_naive
                tma_data_map[email]['total_dias'] += max(0, delta.days)
                tma_data_map[email]['count'] += 1
            except TypeError:
                pass

    sql_iniciadas = "SELECT usuario_cs, COUNT(*) as total FROM implantacoes WHERE data_inicio_efetivo >= %s AND data_inicio_efetivo <= %s"
    args_iniciadas = [primeiro_dia_str, fim_ultimo_dia_str]
    if target_cs_email:
        sql_iniciadas += " AND usuario_cs = %s"
        args_iniciadas.append(target_cs_email)
    sql_iniciadas += " GROUP BY usuario_cs"

    impl_iniciadas_raw = query_db(sql_iniciadas, tuple(args_iniciadas))
    impl_iniciadas_raw = impl_iniciadas_raw if impl_iniciadas_raw is not None else []
    iniciadas_map = {row['usuario_cs']: row['total'] for row in impl_iniciadas_raw if isinstance(row, dict)}

    sql_tarefas = """
        SELECT i.usuario_cs, COALESCE(ci.tag, 'Ação interna') as tag, COUNT(DISTINCT ci.id) as total
        FROM checklist_items ci
        JOIN implantacoes i ON ci.implantacao_id = i.id
        WHERE ci.tipo_item = 'subtarefa'
        AND ci.completed = TRUE 
        AND ci.tag IN ('Ação interna', 'Reunião')
        AND ci.data_conclusao >= %s AND ci.data_conclusao <= %s
    """
    args_tarefas = [primeiro_dia_str, fim_ultimo_dia_str]
    if target_cs_email:
        sql_tarefas += " AND i.usuario_cs = %s"
        args_tarefas.append(target_cs_email)
    sql_tarefas += " GROUP BY i.usuario_cs, ci.tag"

    tarefas_concluidas_raw = query_db(sql_tarefas, tuple(args_tarefas))
    tarefas_concluidas_raw = tarefas_concluidas_raw if tarefas_concluidas_raw is not None else []

    tarefas_map = {}
    for row in tarefas_concluidas_raw:
        if not isinstance(row, dict): continue
        email = row.get('usuario_cs')
        tag = row.get('tag')
        total = row.get('total', 0)
        if not email or not tag: continue

        if email not in tarefas_map:
            tarefas_map[email] = {'Ação interna': 0, 'Reunião': 0}

        if tag == 'Ação interna':
            tarefas_map[email]['Ação interna'] = total
        elif tag == 'Reunião':
            tarefas_map[email]['Reunião'] = total

    return tma_data_map, iniciadas_map, tarefas_map


def _check_eligibility(metricas_manuais, regras_db, count_finalizadas, media_reunioes_dia, cargo):
    elegivel = True
    motivo_inelegibilidade = []

    min_nota_qualidade = regras_db.get('eleg_nota_qualidade_min', 80)
    min_assiduidade = regras_db.get('eleg_assiduidade_min', 85)
    min_planos_sucesso = regras_db.get('eleg_planos_sucesso_min', 75)
    max_reclamacoes = regras_db.get('eleg_reclamacoes_max', 1)
    max_perda_prazo = regras_db.get('eleg_perda_prazo_max', 2)
    max_nao_preenchimento = regras_db.get('eleg_nao_preenchimento_max', 2)

    min_processos_concluidos = 0
    if cargo == 'Júnior':
        min_processos_concluidos = regras_db.get('eleg_finalizadas_junior', 4)
    elif cargo == 'Pleno':
        min_processos_concluidos = regras_db.get('eleg_finalizadas_pleno', 5)
    elif cargo == 'Sênior':
        min_processos_concluidos = regras_db.get('eleg_finalizadas_senior', 5)

    nq = metricas_manuais.get('nota_qualidade')
    if nq is None:
        elegivel = False
        motivo_inelegibilidade.append("Nota Qualidade não informada")
    elif nq < min_nota_qualidade:
        elegivel = False
        motivo_inelegibilidade.append(f"Nota Qualidade < {min_nota_qualidade}%")

    assid = metricas_manuais.get('assiduidade')
    if assid is None:
        elegivel = False
        motivo_inelegibilidade.append("Assiduidade não informada")
    elif assid < min_assiduidade:
        elegivel = False
        motivo_inelegibilidade.append(f"Assiduidade < {min_assiduidade}%")

    psp = metricas_manuais.get('planos_sucesso_perc')
    if psp is None:
        elegivel = False
        motivo_inelegibilidade.append("Planos Sucesso % não informado")
    elif psp < min_planos_sucesso:
        elegivel = False
        motivo_inelegibilidade.append(f"Planos Sucesso < {min_planos_sucesso}%")

    min_reunioes_dia = regras_db.get('eleg_reunioes_min', 3)

    media_reunioes_dia_safe = media_reunioes_dia if media_reunioes_dia is not None else 0
    if media_reunioes_dia_safe < min_reunioes_dia:
        elegivel = False
        motivo_inelegibilidade.append(f"Média Reuniões/Dia ({media_reunioes_dia_safe:.2f}) < {min_reunioes_dia}")

    if count_finalizadas < min_processos_concluidos:
        elegivel = False
        motivo_inelegibilidade.append(f"Impl. Finalizadas ({count_finalizadas}) < {min_processos_concluidos} ({cargo})")

    reclamacoes = metricas_manuais.get('reclamacoes')
    reclamacoes = 0 if reclamacoes is None else reclamacoes
    if reclamacoes >= max_reclamacoes + 1:
        elegivel = False
        motivo_inelegibilidade.append(f"Reclamações >= {max_reclamacoes + 1}")

    perda_prazo = metricas_manuais.get('perda_prazo')
    perda_prazo = 0 if perda_prazo is None else perda_prazo
    if perda_prazo >= max_perda_prazo + 1:
        elegivel = False
        motivo_inelegibilidade.append(f"Perda Prazo >= {max_perda_prazo + 1}")

    nao_preenchimento = metricas_manuais.get('nao_preenchimento')
    nao_preenchimento = 0 if nao_preenchimento is None else nao_preenchimento
    if nao_preenchimento >= max_nao_preenchimento + 1:
        elegivel = False
        motivo_inelegibilidade.append(f"Não Preenchimento >= {max_nao_preenchimento + 1}")

    if nq is not None and nq < 80:
        elegivel = False
        motivo_inelegibilidade.append("Nota Qualidade < 80% (Eliminado)")

    return elegivel, motivo_inelegibilidade


def _calculate_points(metricas_manuais, regras_db, tma_medio, media_reunioes_dia, media_acoes_dia, count_iniciadas_final):
    pontos = 0
    detalhamento_pontos = {}

    satisfacao = metricas_manuais.get('satisfacao_processo')
    pts_satisfacao = 0
    if satisfacao is not None:
        if satisfacao >= 100: pts_satisfacao = regras_db.get('pts_satisfacao_100', 25)
        elif satisfacao >= 95: pts_satisfacao = regras_db.get('pts_satisfacao_95', 17)
        elif satisfacao >= 90: pts_satisfacao = regras_db.get('pts_satisfacao_90', 15)
        elif satisfacao >= 85: pts_satisfacao = regras_db.get('pts_satisfacao_85', 14)
        elif satisfacao >= 80: pts_satisfacao = regras_db.get('pts_satisfacao_80', 12)
    pontos += pts_satisfacao
    detalhamento_pontos['Satisfação Processo'] = f"{pts_satisfacao} pts ({satisfacao if satisfacao is not None else 'N/A'}%)"

    assid = metricas_manuais.get('assiduidade')
    pts_assiduidade = 0
    if assid is not None:
        if assid >= 100: pts_assiduidade = regras_db.get('pts_assiduidade_100', 30)
        elif assid >= 98: pts_assiduidade = regras_db.get('pts_assiduidade_98', 20)
        elif assid >= 95: pts_assiduidade = regras_db.get('pts_assiduidade_95', 15)
    pontos += pts_assiduidade
    detalhamento_pontos['Assiduidade'] = f"{pts_assiduidade} pts ({assid if assid is not None else 'N/A'}%)"

    pts_tma = 0
    tma_display = 'N/A'
    if tma_medio is not None:
        tma_display = f"{tma_medio:.1f} dias"
        if tma_medio <= 30: pts_tma = regras_db.get('pts_tma_30', 45)
        elif tma_medio <= 35: pts_tma = regras_db.get('pts_tma_35', 32)
        elif tma_medio <= 40: pts_tma = regras_db.get('pts_tma_40', 24)
        elif tma_medio <= 45: pts_tma = regras_db.get('pts_tma_45', 16)
        else: pts_tma = regras_db.get('pts_tma_46_mais', 8)
    pontos += pts_tma
    detalhamento_pontos['TMA Médio'] = f"{pts_tma} pts ({tma_display})"

    pts_reunioes_dia = 0
    if media_reunioes_dia >= 5: pts_reunioes_dia = regras_db.get('pts_reunioes_5', 35)
    elif media_reunioes_dia >= 4: pts_reunioes_dia = regras_db.get('pts_reunioes_4', 30)
    elif media_reunioes_dia >= 3: pts_reunioes_dia = regras_db.get('pts_reunioes_3', 25)
    elif media_reunioes_dia >= 2: pts_reunioes_dia = regras_db.get('pts_reunioes_2', 15)
    pontos += pts_reunioes_dia
    detalhamento_pontos['Média Reuniões/Dia'] = f"{pts_reunioes_dia} pts ({media_reunioes_dia:.2f})"

    pts_acoes_dia = 0
    if media_acoes_dia >= 5: pts_acoes_dia = regras_db.get('pts_acoes_5', 15)
    elif media_acoes_dia >= 4: pts_acoes_dia = regras_db.get('pts_acoes_4', 10)
    elif media_acoes_dia >= 3: pts_acoes_dia = regras_db.get('pts_acoes_3', 7)
    elif media_acoes_dia >= 2: pts_acoes_dia = regras_db.get('pts_acoes_2', 5)
    pontos += pts_acoes_dia
    detalhamento_pontos['Média Ações/Dia'] = f"{pts_acoes_dia} pts ({media_acoes_dia:.2f})"

    psp = metricas_manuais.get('planos_sucesso_perc')
    pts_planos = 0
    if psp is not None:
        if psp >= 100: pts_planos = regras_db.get('pts_planos_100', 45)
        elif psp >= 95: pts_planos = regras_db.get('pts_planos_95', 35)
        elif psp >= 90: pts_planos = regras_db.get('pts_planos_90', 30)
        elif psp >= 85: pts_planos = regras_db.get('pts_planos_85', 20)
        elif psp >= 80: pts_planos = regras_db.get('pts_planos_80', 10)
    pontos += pts_planos
    detalhamento_pontos['Planos Sucesso'] = f"{pts_planos} pts ({psp if psp is not None else 'N/A'}%)"

    pts_iniciadas = 0
    if count_iniciadas_final >= 10: pts_iniciadas = regras_db.get('pts_iniciadas_10', 25)
    elif count_iniciadas_final >= 9: pts_iniciadas = regras_db.get('pts_iniciadas_9', 20)
    elif count_iniciadas_final >= 8: pts_iniciadas = regras_db.get('pts_iniciadas_8', 18)
    elif count_iniciadas_final >= 7: pts_iniciadas = regras_db.get('pts_iniciadas_7', 14)
    elif count_iniciadas_final >= 6: pts_iniciadas = regras_db.get('pts_iniciadas_6', 10)
    pontos += pts_iniciadas
    detalhamento_pontos['Impl. Iniciadas'] = f"{pts_iniciadas} pts ({count_iniciadas_final})"

    nq = metricas_manuais.get('nota_qualidade')
    pts_qualidade = 0
    if nq is not None:
        if nq >= 100: pts_qualidade = regras_db.get('pts_qualidade_100', 55)
        elif nq >= 95: pts_qualidade = regras_db.get('pts_qualidade_95', 40)
        elif nq >= 90: pts_qualidade = regras_db.get('pts_qualidade_90', 30)
        elif nq >= 85: pts_qualidade = regras_db.get('pts_qualidade_85', 15)
        elif nq >= 80: pts_qualidade = regras_db.get('pts_qualidade_80', 0)
    pontos += pts_qualidade
    detalhamento_pontos['Nota Qualidade'] = f"{pts_qualidade} pts ({nq if nq is not None else 'N/A'}%)"

    return pontos, detalhamento_pontos


def _calculate_bonus(metricas_manuais, regras_db):
    pts_bonus = 0
    detalhamento_bonus = {}

    elogios = metricas_manuais.get('elogios', 0)
    pts_bonus_elogios = min(elogios, 1) * regras_db.get('bonus_elogios', 15)
    pts_bonus += pts_bonus_elogios
    if elogios > 0:
        detalhamento_bonus['Bônus Elogios'] = f"+{pts_bonus_elogios} pts ({elogios} ocorr.)"

    recomendacoes = metricas_manuais.get('recomendacoes', 0)
    pts_bonus_recom = recomendacoes * regras_db.get('bonus_recomendacoes', 1)
    pts_bonus += pts_bonus_recom
    if recomendacoes > 0:
        detalhamento_bonus['Bônus Recomendações'] = f"+{pts_bonus_recom} pts ({recomendacoes} ocorr.)"

    certificacoes = metricas_manuais.get('certificacoes', 0)
    pts_bonus_cert = min(certificacoes, 1) * regras_db.get('bonus_certificacoes', 15)
    pts_bonus += pts_bonus_cert
    if certificacoes > 0:
        detalhamento_bonus['Bônus Certificações'] = f"+{pts_bonus_cert} pts ({certificacoes} ocorr.)"

    trein_part = metricas_manuais.get('treinamentos_pacto_part', 0)
    pts_bonus_tpart = trein_part * regras_db.get('bonus_trein_pacto_part', 15)
    pts_bonus += pts_bonus_tpart
    if trein_part > 0:
        detalhamento_bonus['Bônus Trein. Pacto (Part.)'] = f"+{pts_bonus_tpart} pts ({trein_part} ocorr.)"

    trein_aplic = metricas_manuais.get('treinamentos_pacto_aplic', 0)
    pts_bonus_taplic = trein_aplic * regras_db.get('bonus_trein_pacto_aplic', 30)
    pts_bonus += pts_bonus_taplic
    if trein_aplic > 0:
        detalhamento_bonus['Bônus Trein. Pacto (Aplic.)'] = f"+{pts_bonus_taplic} pts ({trein_aplic} ocorr.)"

    reun_pres = metricas_manuais.get('reunioes_presenciais', 0)
    pts_bonus_reun_pres = 0
    if reun_pres > 10: pts_bonus_reun_pres = regras_db.get('bonus_reun_pres_10', 35)
    elif reun_pres >= 7: pts_bonus_reun_pres = regras_db.get('bonus_reun_pres_7', 30)
    elif reun_pres >= 5: pts_bonus_reun_pres = regras_db.get('bonus_reun_pres_5', 25)
    elif reun_pres >= 3: pts_bonus_reun_pres = regras_db.get('bonus_reun_pres_3', 20)
    elif reun_pres >= 1: pts_bonus_reun_pres = regras_db.get('bonus_reun_pres_1', 15)
    pts_bonus += pts_bonus_reun_pres
    if reun_pres > 0:
        detalhamento_bonus['Bônus Reuniões Presenciais'] = f"+{pts_bonus_reun_pres} pts ({reun_pres} ocorr.)"

    return pts_bonus, detalhamento_bonus


def _calculate_penalties(metricas_manuais, regras_db):
    pts_penalidade_total = 0
    detalhamento_penalidades = {}

    reclamacoes = metricas_manuais.get('reclamacoes', 0)
    pts_pen_reclam = reclamacoes * abs(regras_db.get('penal_reclamacao', -50))
    pts_penalidade_total += pts_pen_reclam
    if reclamacoes > 0:
        detalhamento_penalidades['Penalidade Reclamação'] = f"-{pts_pen_reclam} pts ({reclamacoes} ocorr.)"

    perda_prazo = metricas_manuais.get('perda_prazo', 0)
    pts_pen_prazo = perda_prazo * abs(regras_db.get('penal_perda_prazo', -10))
    pts_penalidade_total += pts_pen_prazo
    if perda_prazo > 0:
        detalhamento_penalidades['Penalidade Perda Prazo'] = f"-{pts_pen_prazo} pts ({perda_prazo} ocorr.)"

    desc_incomp = metricas_manuais.get('desc_incompreensivel', 0)
    pts_pen_desc = desc_incomp * abs(regras_db.get('penal_desc_incomp', -10))
    pts_penalidade_total += pts_pen_desc
    if desc_incomp > 0:
        detalhamento_penalidades['Penalidade Desc. Incomp.'] = f"-{pts_pen_desc} pts ({desc_incomp} ocorr.)"

    cancel_resp = metricas_manuais.get('cancelamentos_resp', 0)
    pts_pen_cancel = cancel_resp * abs(regras_db.get('penal_cancel_resp', -100))
    pts_penalidade_total += pts_pen_cancel
    if cancel_resp > 0:
        detalhamento_penalidades['Penalidade Cancelamento Resp.'] = f"-{pts_pen_cancel} pts ({cancel_resp} ocorr.)"

    nao_envolv = metricas_manuais.get('nao_envolvimento', 0)
    pts_pen_envolv = nao_envolv * abs(regras_db.get('penal_nao_envolv', -10))
    pts_penalidade_total += pts_pen_envolv
    if nao_envolv > 0:
        detalhamento_penalidades['Penalidade Não Envolv.'] = f"-{pts_pen_envolv} pts ({nao_envolv} ocorr.)"

    nao_preench = metricas_manuais.get('nao_preenchimento', 0)
    pts_pen_preench = nao_preench * abs(regras_db.get('penal_nao_preench', -10))
    pts_penalidade_total += pts_pen_preench
    if nao_preench > 0:
        detalhamento_penalidades['Penalidade Não Preench.'] = f"-{pts_pen_preench} pts ({nao_preench} ocorr.)"

    perda_sla = metricas_manuais.get('perda_sla_grupo', 0)
    pts_pen_sla = perda_sla * abs(regras_db.get('penal_sla_grupo', -5))
    pts_penalidade_total += pts_pen_sla
    if perda_sla > 0:
        detalhamento_penalidades['Penalidade SLA Grupo'] = f"-{pts_pen_sla} pts ({perda_sla} ocorr.)"

    final_incomp = metricas_manuais.get('finalizacao_incompleta', 0)
    pts_pen_final = final_incomp * abs(regras_db.get('penal_final_incomp', -10))
    pts_penalidade_total += pts_pen_final
    if final_incomp > 0:
        detalhamento_penalidades['Penalidade Finaliz. Incomp.'] = f"-{pts_pen_final} pts ({final_incomp} ocorr.)"

    hora_extra = metricas_manuais.get('hora_extra', 0)
    pts_pen_he = hora_extra * abs(regras_db.get('penal_hora_extra', -10))
    pts_penalidade_total += pts_pen_he
    if hora_extra > 0:
        detalhamento_penalidades['Penalidade Hora Extra'] = f"-{pts_pen_he} pts ({hora_extra} ocorr.)"

    return pts_penalidade_total, detalhamento_penalidades


def _calculate_user_gamification_score(
    perfil,
    metricas_manuais,
    regras_db,
    dias_no_mes,
    dados_tma,
    count_iniciadas,
    dados_tarefas
):
    """
    Esta função APENAS calcula. Não faz NENHUMA query ao DB.
    Recebe os dados pré-buscados.
    """

    cargo = perfil.get('cargo', 'N/A')

    metricas_manuais.setdefault('nota_qualidade', None)
    metricas_manuais.setdefault('assiduidade', None)
    metricas_manuais.setdefault('planos_sucesso_perc', None)
    metricas_manuais.setdefault('satisfacao_processo', None)
    metricas_manuais.setdefault('reclamacoes', 0)
    metricas_manuais.setdefault('perda_prazo', 0)
    metricas_manuais.setdefault('nao_preenchimento', 0)
    metricas_manuais.setdefault('elogios', 0)
    metricas_manuais.setdefault('recomendacoes', 0)
    metricas_manuais.setdefault('certificacoes', 0)
    metricas_manuais.setdefault('treinamentos_pacto_part', 0)
    metricas_manuais.setdefault('treinamentos_pacto_aplic', 0)
    metricas_manuais.setdefault('reunioes_presenciais', 0)
    metricas_manuais.setdefault('cancelamentos_resp', 0)
    metricas_manuais.setdefault('nao_envolvimento', 0)
    metricas_manuais.setdefault('desc_incompreensivel', 0)
    metricas_manuais.setdefault('hora_extra', 0)
    metricas_manuais.setdefault('perda_sla_grupo', 0)
    metricas_manuais.setdefault('finalizacao_incompleta', 0)

    metricas_manuais.setdefault('impl_finalizadas_mes', None)
    metricas_manuais.setdefault('tma_medio_mes', None)
    metricas_manuais.setdefault('impl_iniciadas_mes', None)
    metricas_manuais.setdefault('reunioes_concluidas_dia_media', None)
    metricas_manuais.setdefault('acoes_concluidas_dia_media', None)

    count_finalizadas = metricas_manuais['impl_finalizadas_mes']
    if count_finalizadas is None:
        count_finalizadas = dados_tma.get('count', 0)

    tma_medio = metricas_manuais['tma_medio_mes']
    if tma_medio is None:
        tma_total_dias = dados_tma.get('total_dias', 0)
        tma_medio = round(tma_total_dias / count_finalizadas, 1) if count_finalizadas > 0 else None

    count_iniciadas_final = metricas_manuais['impl_iniciadas_mes']
    if count_iniciadas_final is None:
        count_iniciadas_final = count_iniciadas

    media_reunioes_dia = metricas_manuais['reunioes_concluidas_dia_media']
    if media_reunioes_dia is None:
        count_reuniao = dados_tarefas.get('Reunião', 0)
        media_reunioes_dia = round(count_reuniao / dias_no_mes, 2) if dias_no_mes > 0 else 0.0

    media_acoes_dia = metricas_manuais['acoes_concluidas_dia_media']
    if media_acoes_dia is None:
        count_acao_interna = dados_tarefas.get('Ação interna', 0)
        media_acoes_dia = round(count_acao_interna / dias_no_mes, 2) if dias_no_mes > 0 else 0.0

    elegivel, motivo_inelegibilidade = _check_eligibility(metricas_manuais, regras_db, count_finalizadas, media_reunioes_dia, cargo)

    pontos = 0
    detalhamento_pontos = {}

    if elegivel:
        pontos, detalhamento_pontos = _calculate_points(metricas_manuais, regras_db, tma_medio, media_reunioes_dia, media_acoes_dia, count_iniciadas_final)

        pts_bonus, detalhamento_bonus = _calculate_bonus(metricas_manuais, regras_db)
        pontos += pts_bonus
        detalhamento_pontos.update(detalhamento_bonus)

        pts_penalidade, detalhamento_penalidades = _calculate_penalties(metricas_manuais, regras_db)
        pontos -= pts_penalidade
        detalhamento_pontos.update(detalhamento_penalidades)

    resultado = {
        'elegivel': elegivel,
        'motivo_inelegibilidade': ", ".join(motivo_inelegibilidade) if motivo_inelegibilidade else None,
        'pontuacao_final': max(0, pontos) if elegivel else 0,
        'detalhamento_pontos': detalhamento_pontos if elegivel else {},
        'impl_finalizadas_mes': count_finalizadas,
        'tma_medio_mes': f"{tma_medio:.1f}" if tma_medio is not None else 'N/A',
        'impl_iniciadas_mes': count_iniciadas_final,
        'media_reunioes_dia': media_reunioes_dia,
        'media_acoes_dia': media_acoes_dia,
        'metricas_manuais_usadas': metricas_manuais
    }

    dados_automaticos_calculados = {
        'pontuacao_calculada': resultado['pontuacao_final'],
        'elegivel': resultado['elegivel'],

        'impl_finalizadas_mes': count_finalizadas if metricas_manuais.get('impl_finalizadas_mes') is None else None,
        'tma_medio_mes': tma_medio if metricas_manuais.get('tma_medio_mes') is None else None,
        'impl_iniciadas_mes': count_iniciadas_final if metricas_manuais.get('impl_iniciadas_mes') is None else None,
        'reunioes_concluidas_dia_media': media_reunioes_dia if metricas_manuais.get('reunioes_concluidas_dia_media') is None else None,
        'acoes_concluidas_dia_media': media_acoes_dia if metricas_manuais.get('acoes_concluidas_dia_media') is None else None
    }

    return resultado, dados_automaticos_calculados


def get_gamification_report_data(mes, ano, target_cs_email=None, all_cs_users_list=None):
    """
    Função principal para buscar e calcular o relatório de gamificação.
    Resolve o problema N+1 ao buscar todos os dados em massa.
    """
    from flask import current_app

    from ..core.extensions import gamification_rules_cache

    regras_db = _get_gamification_rules_as_dict()
    if not regras_db:
        # Limpar cache se estiver vazio e tentar novamente
        cache_key = 'gamification_rules_dict'
        if cache_key in gamification_rules_cache:
            del gamification_rules_cache[cache_key]
            current_app.logger.warning("Cache de regras estava vazio, limpando e tentando novamente...")
            regras_db = _get_gamification_rules_as_dict()

        if not regras_db:
            current_app.logger.error("Tabela gamificacao_regras está vazia ou não acessível.")
            raise ValueError("Falha ao carregar as regras de pontuação da gamificação do banco de dados. Verifique se a tabela gamificacao_regras tem dados.")

    try:
        primeiro_dia = date(ano, mes, 1)
        ultimo_dia_mes = calendar.monthrange(ano, mes)[1]
        ultimo_dia = date(ano, mes, ultimo_dia_mes)
        fim_ultimo_dia = datetime.combine(ultimo_dia, datetime.max.time())
        dias_no_mes = ultimo_dia_mes
    except ValueError:
        raise ValueError(f"Mês ({mes}) ou Ano ({ano}) inválido.")

    primeiro_dia_str = primeiro_dia.isoformat()
    fim_ultimo_dia_str = fim_ultimo_dia.isoformat()

    if all_cs_users_list is None:
        sql_users = "SELECT usuario, nome, cargo FROM perfil_usuario WHERE perfil_acesso IS NOT NULL AND perfil_acesso != ''"
        args_users = []
        if target_cs_email:
            sql_users += " AND usuario = %s"
            args_users.append(target_cs_email)
        sql_users += " ORDER BY nome"

        all_cs_users_list = query_db(sql_users, tuple(args_users))
        all_cs_users_list = all_cs_users_list if all_cs_users_list is not None else []

    usuarios_filtrados = [u['usuario'] for u in all_cs_users_list if isinstance(u, dict)]
    metricas_manuais_map = {}

    if usuarios_filtrados:
        placeholders = ','.join(['%s'] * len(usuarios_filtrados))
        sql_metricas = f"SELECT * FROM gamificacao_metricas_mensais WHERE mes = %s AND ano = %s AND usuario_cs IN ({placeholders})"
        args_metricas = [mes, ano] + usuarios_filtrados

        metricas_manuais_raw = query_db(sql_metricas, tuple(args_metricas))
        metricas_manuais_raw = metricas_manuais_raw if metricas_manuais_raw is not None else []

        for metrica in metricas_manuais_raw:
            if isinstance(metrica, dict):
                metricas_manuais_map[metrica['usuario_cs']] = metrica

    tma_data_map, iniciadas_map, tarefas_map = _get_gamification_automatic_data_bulk(
        mes, ano, primeiro_dia_str, fim_ultimo_dia_str, target_cs_email
    )

    report_data = []

    for user_profile in all_cs_users_list:
        if not isinstance(user_profile, dict): continue
        user_email = user_profile.get('usuario')
        if not user_email: continue

        try:
            metricas_manuais = metricas_manuais_map.get(user_email, {})
            dados_tma = tma_data_map.get(user_email, {})
            count_iniciadas = iniciadas_map.get(user_email, 0)
            dados_tarefas = tarefas_map.get(user_email, {})

            resultado, dados_automaticos_calculados = _calculate_user_gamification_score(
                user_profile,
                metricas_manuais,
                regras_db,
                dias_no_mes,
                dados_tma,
                count_iniciadas,
                dados_tarefas
            )

            report_data.append({
                'usuario_nome': user_profile.get('nome', user_email),
                'cargo': user_profile.get('cargo', 'N/A'),
                'usuario_cs': user_email,
                'mes': mes,
                'ano': ano,
                'status_calculo': 'Calculado/Atualizado',
                **resultado
            })

            try:
                dados_para_salvar = {
                    key: value for key, value in dados_automaticos_calculados.items()
                    if value is not None
                }

                dados_para_salvar['data_registro'] = datetime.now()

                existing_record_id = metricas_manuais.get('id')

                if existing_record_id:
                    set_clauses_calc = [f"{key} = %s" for key in dados_para_salvar.keys()]

                    if set_clauses_calc:
                        sql_update_calc = f"UPDATE gamificacao_metricas_mensais SET {', '.join(set_clauses_calc)} WHERE id = %s"
                        args_update_calc = list(dados_para_salvar.values()) + [existing_record_id]
                        execute_db(sql_update_calc, tuple(args_update_calc))

            except Exception:
                pass

        except Exception as e:
            report_data.append({
                'usuario_nome': user_profile.get('nome', user_email),
                'cargo': user_profile.get('cargo', 'N/A'),
                'usuario_cs': user_email,
                'mes': mes,
                'ano': ano,
                'elegivel': False,
                'pontuacao_final': 0,
                'motivo_inelegibilidade': f'Erro interno no sistema: {e}',
                'detalhamento_pontos': {},
                'status_calculo': 'Erro Crítico'
            })

    report_data_sorted = sorted(report_data, key=lambda x: x['pontuacao_final'], reverse=True)
    return report_data_sorted


def clear_gamification_cache():
    """Limpa o cache de regras de gamificação."""
    from ..core.extensions import gamification_rules_cache

    try:
        gamification_rules_cache.clear()
        return True
    except Exception:
        return False


def get_all_cs_users_for_gamification():
    """Busca todos os usuários com nome e e-mail para o filtro de gamificação."""
    result = query_db(
        "SELECT usuario, nome, cargo FROM perfil_usuario WHERE perfil_acesso IS NOT NULL AND perfil_acesso != '' ORDER BY nome",
        ()
    )
    return result if result is not None else []


def salvar_regras_gamificacao(updates_list):
    """
    Salva atualizações de regras de gamificação.
    
    Args:
        updates_list: Lista de tuplas (valor_pontos, regra_id)
        
    Returns:
        int: Número de regras atualizadas
    """
    if not updates_list:
        return 0
    
    total_atualizado = 0
    for valor, regra_id in updates_list:
        execute_db(
            "UPDATE gamificacao_regras SET valor_pontos = %s WHERE regra_id = %s",
            (valor, regra_id)
        )
        total_atualizado += 1
    
    clear_gamification_cache()
    return total_atualizado


def obter_metricas_mensais(usuario_cs, mes, ano):
    """Busca as métricas mensais de um usuário específico."""
    return query_db(
        "SELECT * FROM gamificacao_metricas_mensais WHERE usuario_cs = %s AND mes = %s AND ano = %s",
        (usuario_cs, mes, ano),
        one=True
    )


def salvar_metricas_mensais(data_to_save, existing_record_id=None):
    """
    Salva ou atualiza métricas mensais de gamificação.
    
    Args:
        data_to_save: Dicionário com os dados a salvar
        existing_record_id: ID do registro existente (None para inserir novo)
        
    Returns:
        bool: True se sucesso
    """
    if existing_record_id:
        # Atualizar registro existente
        set_clauses = [f"{key} = %s" for key in data_to_save.keys() if key not in ['usuario_cs', 'mes', 'ano']]
        sql_update = f"""
            UPDATE gamificacao_metricas_mensais
            SET {', '.join(set_clauses)}
            WHERE id = %s
        """
        args = list(data_to_save.values())[3:] + [existing_record_id]
        execute_db(sql_update, tuple(args))
    else:
        # Inserir novo registro
        columns = data_to_save.keys()
        values_placeholders = ['%s'] * len(columns)
        sql_insert = f"INSERT INTO gamificacao_metricas_mensais ({', '.join(columns)}) VALUES ({', '.join(values_placeholders)})"
        args = list(data_to_save.values())
        execute_db(sql_insert, tuple(args))
    
    return True
