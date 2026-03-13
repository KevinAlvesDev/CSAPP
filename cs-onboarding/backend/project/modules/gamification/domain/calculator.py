"""
Módulo de Cálculos de Gamificação
Verificação de elegibilidade e cálculo de pontos.
Princípio SOLID: Single Responsibility
"""


# ---------------------------------------------------------------------------
# Funções helper genéricas (sem estado, sem dependências externas)
# ---------------------------------------------------------------------------

def _apply_threshold_rule(value, thresholds, regras_db):
    """
    Avalia value contra uma lista de limiares ordenados do maior para o menor.
    Cada entrada de thresholds é (min_val, regra_key, default_pts).
    Retorna (pontos, valor_usado).
    """
    if value is None:
        return 0, None
    for min_val, key, default_pts in thresholds:
        if value >= min_val:
            return regras_db.get(key, default_pts), value
    return 0, value


def _apply_max_threshold_rule(value, thresholds, regras_db):
    """
    Para métricas onde MENOR valor = MAIS pontos (ex: TMA em dias).
    Cada entrada de thresholds é (max_val, regra_key, default_pts).
    Retorna (pontos, valor_usado).
    """
    if value is None:
        return 0, None
    for max_val, key, default_pts in thresholds:
        if value <= max_val:
            return regras_db.get(key, default_pts), value
    # Além do último limiar: usa o pior nível (último item)
    _, key, default_pts = thresholds[-1]
    return regras_db.get(key, default_pts), value


def _check_metric(value, min_value, label, motivos):
    """Verifica se uma métrica obrigatória atende ao mínimo. Registra motivo se falhar."""
    if value is None:
        motivos.append(f"{label} não informada")
        return False
    if value < min_value:
        motivos.append(f"{label} < {min_value}%")
        return False
    return True


# ---------------------------------------------------------------------------
# Elegibilidade
# ---------------------------------------------------------------------------

def _check_eligibility(metricas_manuais, regras_db, count_finalizadas, media_reunioes_dia, cargo):
    """Verifica se o usuário é elegível para a gamificação."""
    elegivel = True
    motivo_inelegibilidade = []

    # Verificações de mínimos percentuais (None-safe via _check_metric)
    min_checks = [
        ("nota_qualidade",     "eleg_nota_qualidade_min", 80, "Nota Qualidade"),
        ("assiduidade",        "eleg_assiduidade_min",    85, "Assiduidade"),
        ("planos_sucesso_perc","eleg_planos_sucesso_min", 75, "Planos Sucesso %"),
    ]
    for field, regra_key, default_min, label in min_checks:
        if not _check_metric(metricas_manuais.get(field), regras_db.get(regra_key, default_min), label, motivo_inelegibilidade):
            elegivel = False

    # Verificações de contagem com limite máximo
    max_checks = [
        ("reclamacoes",       "eleg_reclamacoes_max",       1, "Reclamações"),
        ("perda_prazo",       "eleg_perda_prazo_max",       2, "Perda Prazo"),
        ("nao_preenchimento", "eleg_nao_preenchimento_max", 2, "Não Preenchimento"),
    ]
    for field, regra_key, default_max, label in max_checks:
        max_val = regras_db.get(regra_key, default_max)
        count = metricas_manuais.get(field, 0) or 0
        if count >= max_val + 1:
            elegivel = False
            motivo_inelegibilidade.append(f"{label} >= {max_val + 1}")

    # Média diária de reuniões — não é critério obrigatório de elegibilidade

    # Processos concluídos mínimos por cargo
    cargo_limites = {"Júnior": "eleg_finalizadas_junior", "Pleno": "eleg_finalizadas_pleno", "Sênior": "eleg_finalizadas_senior"}
    cargo_defaults = {"Júnior": 4, "Pleno": 5, "Sênior": 5}
    min_processos_concluidos = regras_db.get(cargo_limites[cargo], cargo_defaults.get(cargo, 0)) if cargo in cargo_limites else 0
    if count_finalizadas < min_processos_concluidos:
        elegivel = False
        motivo_inelegibilidade.append(f"Impl. Finalizadas ({count_finalizadas}) < {min_processos_concluidos} ({cargo})")

    # Piso absoluto de qualidade (independente de configuração)
    nq = metricas_manuais.get("nota_qualidade")
    if nq is not None and nq < 80:
        elegivel = False
        motivo_inelegibilidade.append("Nota Qualidade < 80% (Eliminado)")

    return elegivel, motivo_inelegibilidade


# ---------------------------------------------------------------------------
# Cálculo de pontos base
# ---------------------------------------------------------------------------

def _calculate_points(
    metricas_manuais, regras_db, tma_medio, media_reunioes_dia, media_acoes_dia, count_iniciadas_final
):
    """Calcula a pontuação base do usuário usando regras de limiar configuráveis."""
    pontos = 0
    detalhamento_pontos = {}

    # Satisfação Processo (maior = melhor)
    satisfacao = metricas_manuais.get("satisfacao_processo")
    pts, val = _apply_threshold_rule(satisfacao, [
        (100, "pts_satisfacao_100", 25),
        (95,  "pts_satisfacao_95",  17),
        (90,  "pts_satisfacao_90",  15),
        (85,  "pts_satisfacao_85",  14),
        (80,  "pts_satisfacao_80",  12),
    ], regras_db)
    pontos += pts
    detalhamento_pontos["Satisfação Processo"] = f"{pts} pts ({val if val is not None else 'N/A'}%)"

    # Assiduidade (maior = melhor)
    assid = metricas_manuais.get("assiduidade")
    pts, val = _apply_threshold_rule(assid, [
        (100, "pts_assiduidade_100", 30),
        (98,  "pts_assiduidade_98",  20),
        (95,  "pts_assiduidade_95",  15),
    ], regras_db)
    pontos += pts
    detalhamento_pontos["Assiduidade"] = f"{pts} pts ({val if val is not None else 'N/A'}%)"

    # TMA Médio (menor = melhor)
    pts_tma, val_tma = _apply_max_threshold_rule(tma_medio, [
        (30, "pts_tma_30",      45),
        (35, "pts_tma_35",      32),
        (40, "pts_tma_40",      24),
        (45, "pts_tma_45",      16),
        (float("inf"), "pts_tma_46_mais", 8),  # Pior nível: TMA acima do limite máximo
    ], regras_db)
    pontos += pts_tma
    tma_display = f"{val_tma:.1f} dias" if val_tma is not None else "N/A"
    detalhamento_pontos["TMA Médio"] = f"{pts_tma} pts ({tma_display})"

    # Média Reuniões/Dia (maior = melhor)
    pts_reun, _ = _apply_threshold_rule(media_reunioes_dia, [
        (5, "pts_reunioes_5", 35),
        (4, "pts_reunioes_4", 30),
        (3, "pts_reunioes_3", 25),
        (2, "pts_reunioes_2", 15),
    ], regras_db)
    pontos += pts_reun
    detalhamento_pontos["Média Reuniões/Dia"] = f"{pts_reun} pts ({media_reunioes_dia:.2f})"

    # Média Ações/Dia (maior = melhor)
    pts_acoes, _ = _apply_threshold_rule(media_acoes_dia, [
        (5, "pts_acoes_5", 15),
        (4, "pts_acoes_4", 10),
        (3, "pts_acoes_3",  7),
        (2, "pts_acoes_2",  5),
    ], regras_db)
    pontos += pts_acoes
    detalhamento_pontos["Média Ações/Dia"] = f"{pts_acoes} pts ({media_acoes_dia:.2f})"

    # Planos Sucesso % (maior = melhor)
    psp = metricas_manuais.get("planos_sucesso_perc")
    pts_planos, val_psp = _apply_threshold_rule(psp, [
        (100, "pts_planos_100", 45),
        (80,  "pts_planos_95",  35),
        (60,  "pts_planos_90",  30),
        (40,  "pts_planos_85",  20),
        (20,  "pts_planos_80",  10),
    ], regras_db)
    pontos += pts_planos
    detalhamento_pontos["Planos Sucesso"] = f"{pts_planos} pts ({val_psp if val_psp is not None else 'N/A'}%)"

    # Impl. Iniciadas (maior = melhor)
    pts_inic, _ = _apply_threshold_rule(count_iniciadas_final, [
        (10, "pts_iniciadas_10", 25),
        (9,  "pts_iniciadas_9",  20),
        (8,  "pts_iniciadas_8",  18),
        (7,  "pts_iniciadas_7",  14),
        (6,  "pts_iniciadas_6",  10),
    ], regras_db)
    pontos += pts_inic
    detalhamento_pontos["Impl. Iniciadas"] = f"{pts_inic} pts ({count_iniciadas_final})"

    # Nota Qualidade (maior = melhor)
    nq = metricas_manuais.get("nota_qualidade")
    pts_qualidade, val_nq = _apply_threshold_rule(nq, [
        (100, "pts_qualidade_100", 55),
        (95,  "pts_qualidade_95",  40),
        (90,  "pts_qualidade_90",  30),
        (85,  "pts_qualidade_85",  15),
        (80,  "pts_qualidade_80",   0),
    ], regras_db)
    pontos += pts_qualidade
    detalhamento_pontos["Nota Qualidade"] = f"{pts_qualidade} pts ({val_nq if val_nq is not None else 'N/A'}%)"

    return pontos, detalhamento_pontos


# ---------------------------------------------------------------------------
# Bônus
# ---------------------------------------------------------------------------

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
    pts_reun_pres, _ = _apply_threshold_rule(reun_pres, [
        (10, "bonus_reun_pres_10", 35),
        (7,  "bonus_reun_pres_7",  30),
        (5,  "bonus_reun_pres_5",  25),
        (3,  "bonus_reun_pres_3",  20),
        (1,  "bonus_reun_pres_1",  15),
    ], regras_db)
    pts_bonus += pts_reun_pres
    if reun_pres > 0:
        detalhamento_bonus["Bônus Reuniões Presenciais"] = f"+{pts_reun_pres} pts ({reun_pres} ocorr.)"

    return pts_bonus, detalhamento_bonus


# ---------------------------------------------------------------------------
# Penalidades
# ---------------------------------------------------------------------------

def _calculate_penalties(metricas_manuais, regras_db):
    """Calcula as penalidades do usuário."""
    pts_penalidade_total = 0
    detalhamento_penalidades = {}

    penalty_fields = [
        ("reclamacoes",         "penal_reclamacao",    -50,  "Penalidade Reclamação"),
        ("perda_prazo",         "penal_perda_prazo",   -10,  "Penalidade Perda Prazo"),
        ("desc_incompreensivel","penal_desc_incomp",   -10,  "Penalidade Desc. Incomp."),
        ("cancelamentos_resp",  "penal_cancel_resp",   -100, "Penalidade Cancelamento Resp."),
        ("nao_envolvimento",    "penal_nao_envolv",    -10,  "Penalidade Não Envolv."),
        ("nao_preenchimento",   "penal_nao_preench",   -10,  "Penalidade Não Preench."),
        ("perda_sla_grupo",     "penal_sla_grupo",      -5,  "Penalidade SLA Grupo"),
        ("finalizacao_incompleta", "penal_final_incomp", -10, "Penalidade Finaliz. Incomp."),
        ("hora_extra",          "penal_hora_extra",    -10,  "Penalidade Hora Extra"),
    ]

    for field, regra_key, default_neg, label in penalty_fields:
        count = metricas_manuais.get(field, 0) or 0
        if count <= 0:
            continue
        pts = count * abs(regras_db.get(regra_key, default_neg))
        pts_penalidade_total += pts
        detalhamento_penalidades[label] = f"-{pts} pts ({count} ocorr.)"

    return pts_penalidade_total, detalhamento_penalidades


# ---------------------------------------------------------------------------
# Resolução de métricas automáticas
# ---------------------------------------------------------------------------

def _resolve_automatic_metrics(metricas_manuais, dados_tma, count_iniciadas, dados_tarefas, dias_no_mes):
    """Resolve métricas automáticas: usa valor manual se disponível, senão calcula a partir dos dados do DB."""
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

    return count_finalizadas, tma_medio, count_iniciadas_final, media_reunioes_dia, media_acoes_dia


# ---------------------------------------------------------------------------
# Orquestrador principal
# ---------------------------------------------------------------------------

_DEFAULTS_NONE = [
    "nota_qualidade", "assiduidade", "planos_sucesso_perc", "satisfacao_processo",
    "impl_finalizadas_mes", "tma_medio_mes", "impl_iniciadas_mes",
    "reunioes_concluidas_dia_media", "acoes_concluidas_dia_media",
]
_DEFAULTS_ZERO = [
    "reclamacoes", "perda_prazo", "nao_preenchimento", "elogios", "recomendacoes",
    "certificacoes", "treinamentos_pacto_part", "treinamentos_pacto_aplic",
    "reunioes_presenciais", "cancelamentos_resp", "nao_envolvimento",
    "desc_incompreensivel", "hora_extra", "perda_sla_grupo", "finalizacao_incompleta",
]


def _calculate_user_gamification_score(
    perfil, metricas_manuais, regras_db, dias_no_mes, dados_tma, count_iniciadas, dados_tarefas
):
    """
    Calcula a pontuação de gamificação de um usuário.
    Esta função APENAS calcula. Não faz NENHUMA query ao DB.
    Recebe os dados pré-buscados.
    """
    cargo = perfil.get("cargo", "N/A")

    for key in _DEFAULTS_NONE:
        metricas_manuais.setdefault(key, None)
    for key in _DEFAULTS_ZERO:
        metricas_manuais.setdefault(key, 0)

    count_finalizadas, tma_medio, count_iniciadas_final, media_reunioes_dia, media_acoes_dia = (
        _resolve_automatic_metrics(metricas_manuais, dados_tma, count_iniciadas, dados_tarefas, dias_no_mes)
    )

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

    def _auto(key, val):
        """Retorna val apenas se o campo não foi fornecido manualmente."""
        return val if metricas_manuais.get(key) is None else None

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
        "impl_finalizadas_mes": _auto("impl_finalizadas_mes", count_finalizadas),
        "tma_medio_mes": _auto("tma_medio_mes", tma_medio),
        "impl_iniciadas_mes": _auto("impl_iniciadas_mes", count_iniciadas_final),
        "reunioes_concluidas_dia_media": _auto("reunioes_concluidas_dia_media", media_reunioes_dia),
        "acoes_concluidas_dia_media": _auto("acoes_concluidas_dia_media", media_acoes_dia),
    }

    return resultado, dados_automaticos_calculados
