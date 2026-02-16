"""
Módulo de Cálculos de Gamificação
Verificação de elegibilidade e cálculo de pontos.
Princípio SOLID: Single Responsibility
"""


def _check_eligibility(metricas_manuais, regras_db, count_finalizadas, media_reunioes_dia, cargo):
    """Verifica se o usuário é elegível para a gamificação."""
    elegivel = True
    motivo_inelegibilidade = []

    min_nota_qualidade = regras_db.get("eleg_nota_qualidade_min", 80)
    min_assiduidade = regras_db.get("eleg_assiduidade_min", 85)
    min_planos_sucesso = regras_db.get("eleg_planos_sucesso_min", 75)
    max_reclamacoes = regras_db.get("eleg_reclamacoes_max", 1)
    max_perda_prazo = regras_db.get("eleg_perda_prazo_max", 2)
    max_nao_preenchimento = regras_db.get("eleg_nao_preenchimento_max", 2)

    min_processos_concluidos = 0
    if cargo == "Júnior":
        min_processos_concluidos = regras_db.get("eleg_finalizadas_junior", 4)
    elif cargo == "Pleno":
        min_processos_concluidos = regras_db.get("eleg_finalizadas_pleno", 5)
    elif cargo == "Sênior":
        min_processos_concluidos = regras_db.get("eleg_finalizadas_senior", 5)

    nq = metricas_manuais.get("nota_qualidade")
    if nq is None:
        elegivel = False
        motivo_inelegibilidade.append("Nota Qualidade não informada")
    elif nq < min_nota_qualidade:
        elegivel = False
        motivo_inelegibilidade.append(f"Nota Qualidade < {min_nota_qualidade}%")

    assid = metricas_manuais.get("assiduidade")
    if assid is None:
        elegivel = False
        motivo_inelegibilidade.append("Assiduidade não informada")
    elif assid < min_assiduidade:
        elegivel = False
        motivo_inelegibilidade.append(f"Assiduidade < {min_assiduidade}%")

    psp = metricas_manuais.get("planos_sucesso_perc")
    if psp is None:
        elegivel = False
        motivo_inelegibilidade.append("Planos Sucesso % não informado")
    elif psp < min_planos_sucesso:
        elegivel = False
        motivo_inelegibilidade.append(f"Planos Sucesso < {min_planos_sucesso}%")

    min_reunioes_dia = regras_db.get("eleg_reunioes_min", 3)

    media_reunioes_dia_safe = media_reunioes_dia if media_reunioes_dia is not None else 0
    if media_reunioes_dia_safe < min_reunioes_dia:
        elegivel = False
        motivo_inelegibilidade.append(f"Média Reuniões/Dia ({media_reunioes_dia_safe:.2f}) < {min_reunioes_dia}")

    if count_finalizadas < min_processos_concluidos:
        elegivel = False
        motivo_inelegibilidade.append(f"Impl. Finalizadas ({count_finalizadas}) < {min_processos_concluidos} ({cargo})")

    reclamacoes = metricas_manuais.get("reclamacoes")
    reclamacoes = 0 if reclamacoes is None else reclamacoes
    if reclamacoes >= max_reclamacoes + 1:
        elegivel = False
        motivo_inelegibilidade.append(f"Reclamações >= {max_reclamacoes + 1}")

    perda_prazo = metricas_manuais.get("perda_prazo")
    perda_prazo = 0 if perda_prazo is None else perda_prazo
    if perda_prazo >= max_perda_prazo + 1:
        elegivel = False
        motivo_inelegibilidade.append(f"Perda Prazo >= {max_perda_prazo + 1}")

    nao_preenchimento = metricas_manuais.get("nao_preenchimento")
    nao_preenchimento = 0 if nao_preenchimento is None else nao_preenchimento
    if nao_preenchimento >= max_nao_preenchimento + 1:
        elegivel = False
        motivo_inelegibilidade.append(f"Não Preenchimento >= {max_nao_preenchimento + 1}")

    if nq is not None and nq < 80:
        elegivel = False
        motivo_inelegibilidade.append("Nota Qualidade < 80% (Eliminado)")

    return elegivel, motivo_inelegibilidade


def _calculate_points(
    metricas_manuais, regras_db, tma_medio, media_reunioes_dia, media_acoes_dia, count_iniciadas_final
):
    """Calcula a pontuação base do usuário."""
    pontos = 0
    detalhamento_pontos = {}

    satisfacao = metricas_manuais.get("satisfacao_processo")
    pts_satisfacao = 0
    if satisfacao is not None:
        if satisfacao >= 100:
            pts_satisfacao = regras_db.get("pts_satisfacao_100", 25)
        elif satisfacao >= 95:
            pts_satisfacao = regras_db.get("pts_satisfacao_95", 17)
        elif satisfacao >= 90:
            pts_satisfacao = regras_db.get("pts_satisfacao_90", 15)
        elif satisfacao >= 85:
            pts_satisfacao = regras_db.get("pts_satisfacao_85", 14)
        elif satisfacao >= 80:
            pts_satisfacao = regras_db.get("pts_satisfacao_80", 12)
    pontos += pts_satisfacao
    detalhamento_pontos["Satisfação Processo"] = (
        f"{pts_satisfacao} pts ({satisfacao if satisfacao is not None else 'N/A'}%)"
    )

    assid = metricas_manuais.get("assiduidade")
    pts_assiduidade = 0
    if assid is not None:
        if assid >= 100:
            pts_assiduidade = regras_db.get("pts_assiduidade_100", 30)
        elif assid >= 98:
            pts_assiduidade = regras_db.get("pts_assiduidade_98", 20)
        elif assid >= 95:
            pts_assiduidade = regras_db.get("pts_assiduidade_95", 15)
    pontos += pts_assiduidade
    detalhamento_pontos["Assiduidade"] = f"{pts_assiduidade} pts ({assid if assid is not None else 'N/A'}%)"

    pts_tma = 0
    tma_display = "N/A"
    if tma_medio is not None:
        tma_display = f"{tma_medio:.1f} dias"
        if tma_medio <= 30:
            pts_tma = regras_db.get("pts_tma_30", 45)
        elif tma_medio <= 35:
            pts_tma = regras_db.get("pts_tma_35", 32)
        elif tma_medio <= 40:
            pts_tma = regras_db.get("pts_tma_40", 24)
        elif tma_medio <= 45:
            pts_tma = regras_db.get("pts_tma_45", 16)
        else:
            pts_tma = regras_db.get("pts_tma_46_mais", 8)
    pontos += pts_tma
    detalhamento_pontos["TMA Médio"] = f"{pts_tma} pts ({tma_display})"

    pts_reunioes_dia = 0
    if media_reunioes_dia >= 5:
        pts_reunioes_dia = regras_db.get("pts_reunioes_5", 35)
    elif media_reunioes_dia >= 4:
        pts_reunioes_dia = regras_db.get("pts_reunioes_4", 30)
    elif media_reunioes_dia >= 3:
        pts_reunioes_dia = regras_db.get("pts_reunioes_3", 25)
    elif media_reunioes_dia >= 2:
        pts_reunioes_dia = regras_db.get("pts_reunioes_2", 15)
    pontos += pts_reunioes_dia
    detalhamento_pontos["Média Reuniões/Dia"] = f"{pts_reunioes_dia} pts ({media_reunioes_dia:.2f})"

    pts_acoes_dia = 0
    if media_acoes_dia >= 5:
        pts_acoes_dia = regras_db.get("pts_acoes_5", 15)
    elif media_acoes_dia >= 4:
        pts_acoes_dia = regras_db.get("pts_acoes_4", 10)
    elif media_acoes_dia >= 3:
        pts_acoes_dia = regras_db.get("pts_acoes_3", 7)
    elif media_acoes_dia >= 2:
        pts_acoes_dia = regras_db.get("pts_acoes_2", 5)
    pontos += pts_acoes_dia
    detalhamento_pontos["Média Ações/Dia"] = f"{pts_acoes_dia} pts ({media_acoes_dia:.2f})"

    psp = metricas_manuais.get("planos_sucesso_perc")
    pts_planos = 0
    if psp is not None:
        if psp >= 100:
            pts_planos = regras_db.get("pts_planos_100", 45)
        elif psp >= 95:
            pts_planos = regras_db.get("pts_planos_95", 35)
        elif psp >= 90:
            pts_planos = regras_db.get("pts_planos_90", 30)
        elif psp >= 85:
            pts_planos = regras_db.get("pts_planos_85", 20)
        elif psp >= 80:
            pts_planos = regras_db.get("pts_planos_80", 10)
    pontos += pts_planos
    detalhamento_pontos["Planos Sucesso"] = f"{pts_planos} pts ({psp if psp is not None else 'N/A'}%)"

    pts_iniciadas = 0
    if count_iniciadas_final >= 10:
        pts_iniciadas = regras_db.get("pts_iniciadas_10", 25)
    elif count_iniciadas_final >= 9:
        pts_iniciadas = regras_db.get("pts_iniciadas_9", 20)
    elif count_iniciadas_final >= 8:
        pts_iniciadas = regras_db.get("pts_iniciadas_8", 18)
    elif count_iniciadas_final >= 7:
        pts_iniciadas = regras_db.get("pts_iniciadas_7", 14)
    elif count_iniciadas_final >= 6:
        pts_iniciadas = regras_db.get("pts_iniciadas_6", 10)
    pontos += pts_iniciadas
    detalhamento_pontos["Impl. Iniciadas"] = f"{pts_iniciadas} pts ({count_iniciadas_final})"

    nq = metricas_manuais.get("nota_qualidade")
    pts_qualidade = 0
    if nq is not None:
        if nq >= 100:
            pts_qualidade = regras_db.get("pts_qualidade_100", 55)
        elif nq >= 95:
            pts_qualidade = regras_db.get("pts_qualidade_95", 40)
        elif nq >= 90:
            pts_qualidade = regras_db.get("pts_qualidade_90", 30)
        elif nq >= 85:
            pts_qualidade = regras_db.get("pts_qualidade_85", 15)
        elif nq >= 80:
            pts_qualidade = regras_db.get("pts_qualidade_80", 0)
    pontos += pts_qualidade
    detalhamento_pontos["Nota Qualidade"] = f"{pts_qualidade} pts ({nq if nq is not None else 'N/A'}%)"

    return pontos, detalhamento_pontos


def _calculate_bonus(metricas_manuais, regras_db):
    """Calcula os bônus do usuário."""
    pts_bonus = 0
    detalhamento_bonus = {}

    elogios = metricas_manuais.get("elogios", 0)
    pts_bonus_elogios = min(elogios, 1) * regras_db.get("bonus_elogios", 15)
    pts_bonus += pts_bonus_elogios
    if elogios > 0:
        detalhamento_bonus["Bônus Elogios"] = f"+{pts_bonus_elogios} pts ({elogios} ocorr.)"

    recomendacoes = metricas_manuais.get("recomendacoes", 0)
    pts_bonus_recom = recomendacoes * regras_db.get("bonus_recomendacoes", 1)
    pts_bonus += pts_bonus_recom
    if recomendacoes > 0:
        detalhamento_bonus["Bônus Recomendações"] = f"+{pts_bonus_recom} pts ({recomendacoes} ocorr.)"

    certificacoes = metricas_manuais.get("certificacoes", 0)
    pts_bonus_cert = min(certificacoes, 1) * regras_db.get("bonus_certificacoes", 15)
    pts_bonus += pts_bonus_cert
    if certificacoes > 0:
        detalhamento_bonus["Bônus Certificações"] = f"+{pts_bonus_cert} pts ({certificacoes} ocorr.)"

    trein_part = metricas_manuais.get("treinamentos_pacto_part", 0)
    pts_bonus_tpart = trein_part * regras_db.get("bonus_trein_pacto_part", 15)
    pts_bonus += pts_bonus_tpart
    if trein_part > 0:
        detalhamento_bonus["Bônus Trein. Pacto (Part.)"] = f"+{pts_bonus_tpart} pts ({trein_part} ocorr.)"

    trein_aplic = metricas_manuais.get("treinamentos_pacto_aplic", 0)
    pts_bonus_taplic = trein_aplic * regras_db.get("bonus_trein_pacto_aplic", 30)
    pts_bonus += pts_bonus_taplic
    if trein_aplic > 0:
        detalhamento_bonus["Bônus Trein. Pacto (Aplic.)"] = f"+{pts_bonus_taplic} pts ({trein_aplic} ocorr.)"

    reun_pres = metricas_manuais.get("reunioes_presenciais", 0)
    pts_bonus_reun_pres = 0
    if reun_pres > 10:
        pts_bonus_reun_pres = regras_db.get("bonus_reun_pres_10", 35)
    elif reun_pres >= 7:
        pts_bonus_reun_pres = regras_db.get("bonus_reun_pres_7", 30)
    elif reun_pres >= 5:
        pts_bonus_reun_pres = regras_db.get("bonus_reun_pres_5", 25)
    elif reun_pres >= 3:
        pts_bonus_reun_pres = regras_db.get("bonus_reun_pres_3", 20)
    elif reun_pres >= 1:
        pts_bonus_reun_pres = regras_db.get("bonus_reun_pres_1", 15)
    pts_bonus += pts_bonus_reun_pres
    if reun_pres > 0:
        detalhamento_bonus["Bônus Reuniões Presenciais"] = f"+{pts_bonus_reun_pres} pts ({reun_pres} ocorr.)"

    return pts_bonus, detalhamento_bonus


def _calculate_penalties(metricas_manuais, regras_db):
    """Calcula as penalidades do usuário."""
    pts_penalidade_total = 0
    detalhamento_penalidades = {}

    reclamacoes = metricas_manuais.get("reclamacoes", 0)
    pts_pen_reclam = reclamacoes * abs(regras_db.get("penal_reclamacao", -50))
    pts_penalidade_total += pts_pen_reclam
    if reclamacoes > 0:
        detalhamento_penalidades["Penalidade Reclamação"] = f"-{pts_pen_reclam} pts ({reclamacoes} ocorr.)"

    perda_prazo = metricas_manuais.get("perda_prazo", 0)
    pts_pen_prazo = perda_prazo * abs(regras_db.get("penal_perda_prazo", -10))
    pts_penalidade_total += pts_pen_prazo
    if perda_prazo > 0:
        detalhamento_penalidades["Penalidade Perda Prazo"] = f"-{pts_pen_prazo} pts ({perda_prazo} ocorr.)"

    desc_incomp = metricas_manuais.get("desc_incompreensivel", 0)
    pts_pen_desc = desc_incomp * abs(regras_db.get("penal_desc_incomp", -10))
    pts_penalidade_total += pts_pen_desc
    if desc_incomp > 0:
        detalhamento_penalidades["Penalidade Desc. Incomp."] = f"-{pts_pen_desc} pts ({desc_incomp} ocorr.)"

    cancel_resp = metricas_manuais.get("cancelamentos_resp", 0)
    pts_pen_cancel = cancel_resp * abs(regras_db.get("penal_cancel_resp", -100))
    pts_penalidade_total += pts_pen_cancel
    if cancel_resp > 0:
        detalhamento_penalidades["Penalidade Cancelamento Resp."] = f"-{pts_pen_cancel} pts ({cancel_resp} ocorr.)"

    nao_envolv = metricas_manuais.get("nao_envolvimento", 0)
    pts_pen_envolv = nao_envolv * abs(regras_db.get("penal_nao_envolv", -10))
    pts_penalidade_total += pts_pen_envolv
    if nao_envolv > 0:
        detalhamento_penalidades["Penalidade Não Envolv."] = f"-{pts_pen_envolv} pts ({nao_envolv} ocorr.)"

    nao_preench = metricas_manuais.get("nao_preenchimento", 0)
    pts_pen_preench = nao_preench * abs(regras_db.get("penal_nao_preench", -10))
    pts_penalidade_total += pts_pen_preench
    if nao_preench > 0:
        detalhamento_penalidades["Penalidade Não Preench."] = f"-{pts_pen_preench} pts ({nao_preench} ocorr.)"

    perda_sla = metricas_manuais.get("perda_sla_grupo", 0)
    pts_pen_sla = perda_sla * abs(regras_db.get("penal_sla_grupo", -5))
    pts_penalidade_total += pts_pen_sla
    if perda_sla > 0:
        detalhamento_penalidades["Penalidade SLA Grupo"] = f"-{pts_pen_sla} pts ({perda_sla} ocorr.)"

    final_incomp = metricas_manuais.get("finalizacao_incompleta", 0)
    pts_pen_final = final_incomp * abs(regras_db.get("penal_final_incomp", -10))
    pts_penalidade_total += pts_pen_final
    if final_incomp > 0:
        detalhamento_penalidades["Penalidade Finaliz. Incomp."] = f"-{pts_pen_final} pts ({final_incomp} ocorr.)"

    hora_extra = metricas_manuais.get("hora_extra", 0)
    pts_pen_he = hora_extra * abs(regras_db.get("penal_hora_extra", -10))
    pts_penalidade_total += pts_pen_he
    if hora_extra > 0:
        detalhamento_penalidades["Penalidade Hora Extra"] = f"-{pts_pen_he} pts ({hora_extra} ocorr.)"

    return pts_penalidade_total, detalhamento_penalidades


def _calculate_user_gamification_score(
    perfil, metricas_manuais, regras_db, dias_no_mes, dados_tma, count_iniciadas, dados_tarefas
):
    """
    Calcula a pontuação de gamificação de um usuário.
    Esta função APENAS calcula. Não faz NENHUMA query ao DB.
    Recebe os dados pré-buscados.
    """

    cargo = perfil.get("cargo", "N/A")

    metricas_manuais.setdefault("nota_qualidade", None)
    metricas_manuais.setdefault("assiduidade", None)
    metricas_manuais.setdefault("planos_sucesso_perc", None)
    metricas_manuais.setdefault("satisfacao_processo", None)
    metricas_manuais.setdefault("reclamacoes", 0)
    metricas_manuais.setdefault("perda_prazo", 0)
    metricas_manuais.setdefault("nao_preenchimento", 0)
    metricas_manuais.setdefault("elogios", 0)
    metricas_manuais.setdefault("recomendacoes", 0)
    metricas_manuais.setdefault("certificacoes", 0)
    metricas_manuais.setdefault("treinamentos_pacto_part", 0)
    metricas_manuais.setdefault("treinamentos_pacto_aplic", 0)
    metricas_manuais.setdefault("reunioes_presenciais", 0)
    metricas_manuais.setdefault("cancelamentos_resp", 0)
    metricas_manuais.setdefault("nao_envolvimento", 0)
    metricas_manuais.setdefault("desc_incompreensivel", 0)
    metricas_manuais.setdefault("hora_extra", 0)
    metricas_manuais.setdefault("perda_sla_grupo", 0)
    metricas_manuais.setdefault("finalizacao_incompleta", 0)

    metricas_manuais.setdefault("impl_finalizadas_mes", None)
    metricas_manuais.setdefault("tma_medio_mes", None)
    metricas_manuais.setdefault("impl_iniciadas_mes", None)
    metricas_manuais.setdefault("reunioes_concluidas_dia_media", None)
    metricas_manuais.setdefault("acoes_concluidas_dia_media", None)

    count_finalizadas = metricas_manuais["impl_finalizadas_mes"]
    if count_finalizadas is None:
        count_finalizadas = dados_tma.get("count", 0)

    tma_medio = metricas_manuais["tma_medio_mes"]
    if tma_medio is None:
        tma_total_dias = dados_tma.get("total_dias", 0)
        tma_medio = round(tma_total_dias / count_finalizadas, 1) if count_finalizadas > 0 else None

    count_iniciadas_final = metricas_manuais["impl_iniciadas_mes"]
    if count_iniciadas_final is None:
        count_iniciadas_final = count_iniciadas

    media_reunioes_dia = metricas_manuais["reunioes_concluidas_dia_media"]
    if media_reunioes_dia is None:
        count_reuniao = dados_tarefas.get("Reunião", 0)
        media_reunioes_dia = round(count_reuniao / dias_no_mes, 2) if dias_no_mes > 0 else 0.0

    media_acoes_dia = metricas_manuais["acoes_concluidas_dia_media"]
    if media_acoes_dia is None:
        count_acao_interna = dados_tarefas.get("Ação interna", 0)
        media_acoes_dia = round(count_acao_interna / dias_no_mes, 2) if dias_no_mes > 0 else 0.0

    elegivel, motivo_inelegibilidade = _check_eligibility(
        metricas_manuais, regras_db, count_finalizadas, media_reunioes_dia, cargo
    )

    pontos = 0
    detalhamento_pontos = {}

    if elegivel:
        pontos, detalhamento_pontos = _calculate_points(
            metricas_manuais, regras_db, tma_medio, media_reunioes_dia, media_acoes_dia, count_iniciadas_final
        )

        pts_bonus, detalhamento_bonus = _calculate_bonus(metricas_manuais, regras_db)
        pontos += pts_bonus
        detalhamento_pontos.update(detalhamento_bonus)

        pts_penalidade, detalhamento_penalidades = _calculate_penalties(metricas_manuais, regras_db)
        pontos -= pts_penalidade
        detalhamento_pontos.update(detalhamento_penalidades)

    resultado = {
        "elegivel": elegivel,
        "motivo_inelegibilidade": ", ".join(motivo_inelegibilidade) if motivo_inelegibilidade else None,
        "pontuacao_final": max(0, pontos) if elegivel else 0,
        "detalhamento_pontos": detalhamento_pontos if elegivel else {},
        "impl_finalizadas_mes": count_finalizadas,
        "tma_medio_mes": f"{tma_medio:.1f}" if tma_medio is not None else "N/A",
        "impl_iniciadas_mes": count_iniciadas_final,
        "media_reunioes_dia": media_reunioes_dia,
        "media_acoes_dia": media_acoes_dia,
        "metricas_manuais_usadas": metricas_manuais,
    }

    dados_automaticos_calculados = {
        "pontuacao_calculada": resultado["pontuacao_final"],
        "elegivel": resultado["elegivel"],
        "impl_finalizadas_mes": count_finalizadas if metricas_manuais.get("impl_finalizadas_mes") is None else None,
        "tma_medio_mes": tma_medio if metricas_manuais.get("tma_medio_mes") is None else None,
        "impl_iniciadas_mes": count_iniciadas_final if metricas_manuais.get("impl_iniciadas_mes") is None else None,
        "reunioes_concluidas_dia_media": media_reunioes_dia
        if metricas_manuais.get("reunioes_concluidas_dia_media") is None
        else None,
        "acoes_concluidas_dia_media": media_acoes_dia
        if metricas_manuais.get("acoes_concluidas_dia_media") is None
        else None,
    }

    return resultado, dados_automaticos_calculados
