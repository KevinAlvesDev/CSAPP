import logging
logger = logging.getLogger(__name__)
"""
Módulo de Regras de Gamificação
Buscar e salvar regras de gamificação.
Princípio SOLID: Single Responsibility
"""

from collections import OrderedDict

from flask import current_app, g

from ....db import execute_db, query_db
from .utils import clear_gamification_cache

# Regras validadas para permanecer no sistema (conforme definição de negócio).
ALLOWED_RULE_IDS = {
    # Bônus
    "bonus_elogios",
    "bonus_recomendacoes",
    "bonus_certificacoes",
    "bonus_trein_pacto_part",
    "bonus_trein_pacto_aplic",
    "bonus_ajuda_lideranca",
    # Bônus: Reuniões Pres.
    "bonus_reun_pres_10",
    "bonus_reun_pres_7",
    "bonus_reun_pres_5",
    "bonus_reun_pres_3",
    "bonus_reun_pres_1",
    # Elegibilidade
    "eleg_nota_qualidade_min",
    "eleg_assiduidade_min",
    "eleg_planos_sucesso_min",
    "eleg_reclamacoes_max",
    "eleg_perda_prazo_max",
    "eleg_nao_preenchimento_max",
    "eleg_finalizadas_junior",
    "eleg_finalizadas_pleno",
    "eleg_finalizadas_senior",
    "eleg_reunioes_min",
    # Penalidades
    "penal_reclamacao",
    "penal_perda_prazo",
    "penal_desc_incomp",
    "penal_cancel_resp",
    "penal_nao_envolv",
    "penal_nao_preench",
    "penal_sla_grupo",
    "penal_final_incomp",
    "penal_hora_extra",
    # Pontos: Ações/Dia
    "pts_acoes_5",
    "pts_acoes_4",
    "pts_acoes_3",
    "pts_acoes_2",
    # Pontos: Assiduidade
    "pts_assiduidade_100",
    "pts_assiduidade_98",
    "pts_assiduidade_95",
    # Pontos: Impl. Iniciadas
    "pts_iniciadas_10",
    "pts_iniciadas_9",
    "pts_iniciadas_8",
    "pts_iniciadas_7",
    "pts_iniciadas_6",
    # Pontos: Planos Sucesso
    "pts_planos_100",
    "pts_planos_95",
    "pts_planos_90",
    "pts_planos_85",
    "pts_planos_80",
    # Pontos: Qualidade
    "pts_qualidade_100",
    "pts_qualidade_95",
    "pts_qualidade_90",
    "pts_qualidade_85",
    "pts_qualidade_80",
    # Pontos: Reuniões/Dia
    "pts_reunioes_5",
    "pts_reunioes_4",
    "pts_reunioes_3",
    "pts_reunioes_2",
    # Pontos: Satisfação
    "pts_satisfacao_100",
    "pts_satisfacao_95",
    "pts_satisfacao_90",
    "pts_satisfacao_85",
    "pts_satisfacao_80",
    # Pontos: TMA
    "pts_tma_30",
    "pts_tma_35",
    "pts_tma_40",
    "pts_tma_45",
    "pts_tma_46_mais",
}


def _canonical_rule_category(regra_id: str, categoria_atual: str) -> str:
    """Normaliza categoria por regra_id para evitar grupos quebrados por dados legados."""
    if regra_id.startswith("bonus_reun_pres_"):
        return "Bônus: Reuniões Pres."
    if regra_id.startswith("bonus_"):
        return "Bônus"
    if regra_id.startswith("eleg_"):
        return "Elegibilidade"
    if regra_id.startswith("penal_"):
        return "Penalidades"
    if regra_id.startswith("pts_acoes_"):
        return "Pontos: Ações/Dia"
    if regra_id.startswith("pts_assiduidade_"):
        return "Pontos: Assiduidade"
    if regra_id.startswith("pts_iniciadas_"):
        return "Pontos: Impl. Iniciadas"
    if regra_id.startswith("pts_planos_"):
        return "Pontos: Planos Sucesso"
    if regra_id.startswith("pts_qualidade_"):
        return "Pontos: Qualidade"
    if regra_id.startswith("pts_reunioes_"):
        return "Pontos: Reuniões/Dia"
    if regra_id.startswith("pts_satisfacao_"):
        return "Pontos: Satisfação"
    if regra_id.startswith("pts_tma_"):
        return "Pontos: TMA"
    return categoria_atual


def _get_gamification_rules_as_dict():
    """Busca todas as regras do DB e retorna um dicionário (com cache)."""
    from ....core.extensions import gamification_rules_cache

    cache_key = "gamification_rules_dict"
    if cache_key in gamification_rules_cache:
        cached_result = gamification_rules_cache[cache_key]
        if cached_result:
            return cached_result

    try:
        contexto = getattr(g, "modulo_atual", "onboarding")
        regras_raw = query_db("SELECT regra_id, valor_pontos FROM gamificacao_regras")
        regras_filtradas = [r for r in regras_raw if r.get("regra_id") in ALLOWED_RULE_IDS]
        if not regras_filtradas:
            current_app.logger.warning("Tabela gamificacao_regras está vazia. Verifique se as regras foram inseridas.")
            from typing import Any
            result: dict[str, Any] = {}
        else:
            result = {r["regra_id"]: r["valor_pontos"] for r in regras_filtradas}
            current_app.logger.info(f"Carregadas {len(result)} regras de gamificação do banco de dados.")

        gamification_rules_cache[cache_key] = result
        return result
    except Exception as e:
        current_app.logger.error(f"Erro ao buscar regras de gamificação: {e}", exc_info=True)
        return {}


def _get_all_gamification_rules_grouped():
    """Busca todas as regras de gamificação e as agrupa por categoria (com cache)."""
    from ....core.extensions import gamification_rules_cache

    cache_key = "gamification_rules_grouped"
    if cache_key in gamification_rules_cache:
        return gamification_rules_cache[cache_key]

    try:
        contexto = getattr(g, "modulo_atual", "onboarding")
        regras = query_db("SELECT * FROM gamificacao_regras ORDER BY categoria, id")
        from typing import Any
        result: dict[str, Any] = {}
        regras_filtradas = [r for r in regras if r.get("regra_id") in ALLOWED_RULE_IDS]
        if not regras_filtradas:
            result = {}
        else:
            regras_agrupadas: OrderedDict[str, list[dict[str, Any]]] = OrderedDict()
            for regra in regras_filtradas:
                regra_id = regra.get("regra_id", "")
                categoria = _canonical_rule_category(regra_id, regra.get("categoria", ""))
                regra = dict(regra)
                regra["categoria"] = categoria
                if categoria not in regras_agrupadas:
                    regras_agrupadas[categoria] = []
                regras_agrupadas[categoria].append(regra)
            result = regras_agrupadas

        gamification_rules_cache[cache_key] = result
        return result
    except Exception as exc:
        logger.exception("Unhandled exception", exc_info=True)
        return {}


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
    contexto = getattr(g, "modulo_atual", "onboarding")
    
    for valor, regra_id in updates_list:
        execute_db(
            "UPDATE gamificacao_regras SET valor_pontos = %s WHERE regra_id = %s",
            (valor, regra_id)
        )
        total_atualizado += 1

    clear_gamification_cache()
    return total_atualizado


def criar_regra_gamificacao(regra_id, categoria, descricao, valor_pontos, tipo_valor):
    """
    Cria uma nova regra de gamificação.
    """
    try:
        from ....db import get_db_connection
        conn, db_type = get_db_connection()
    except Exception as exc:
        logger.exception("Unhandled exception", exc_info=True)
        db_type = "postgres"

    contexto = getattr(g, "modulo_atual", "onboarding")
    if db_type == "postgres":
        sql = """
            INSERT INTO gamificacao_regras
            (regra_id, categoria, descricao, valor_pontos, tipo_valor)
            SELECT %s, %s, %s, %s, %s
            WHERE NOT EXISTS (
                SELECT 1 FROM gamificacao_regras
                WHERE regra_id = %s
            )
        """
        execute_db(sql, (regra_id, categoria, descricao, valor_pontos, tipo_valor, regra_id))
    else:
        sql = """
            INSERT OR IGNORE INTO gamificacao_regras
            (regra_id, categoria, descricao, valor_pontos, tipo_valor)
            VALUES (?, ?, ?, ?, ?)
        """
        execute_db(sql, (regra_id, categoria, descricao, valor_pontos, tipo_valor))
    clear_gamification_cache()
    return True

def deletar_regra_gamificacao(regra_id):
    """
    Deleta uma regra pelo seu ID.
    """
    try:
        from ....db import get_db_connection
        conn, db_type = get_db_connection()
    except Exception as exc:
        logger.exception("Unhandled exception", exc_info=True)
        db_type = "postgres"

    contexto = getattr(g, "modulo_atual", "onboarding")
    if db_type == "postgres":
        sql = "DELETE FROM gamificacao_regras WHERE regra_id = %s"
    else:
        sql = "DELETE FROM gamificacao_regras WHERE regra_id = ?"

    execute_db(sql, (regra_id,))
    clear_gamification_cache()
    return True


# reload