"""
Módulo de Mapeamento do External Service
Mapeamento de campos OAMD para campos do Frontend.
Princípio SOLID: Single Responsibility
"""

from .utils import build_tela_apoio_link, extract_infra_code

# Mapeamento de campos OAMD → Frontend
FIELD_MAPPING = {
    # Dados de detalheempresa (datas e níveis)
    "data_inicio_producao": "inicioproducao",
    "data_inicio_efetivo": "inicioimplantacao",
    "data_final_implantacao": "finalimplantacao",
    "nivel_atendimento": "nivelatendimento",
    "nivel_receita": "nivelreceitamensal",
    "tipo_cliente": "tipocliente",
    "categoria": "categoria",
    "condicao_especial": "condicaoespecial",
    # Dados do plano de sucesso
    "plano_data_inicio": "plano_datainicio",
    "plano_data_final": "plano_datafinal",
    "plano_data_conclusao": "plano_dataconclusao",
    "plano_duracao": "plano_duracao",
    "plano_progresso": "plano_porcentagem",
    "plano_responsavel": "plano_responsavel",
    "plano_nome": "plano_nome",
    # Dados básicos
    "chave_oamd": "chavezw",
    "cnpj": "cnpj",
    "data_cadastro": "datacadastro",
    "grupo_favorecido": "grupofavorecido",
    "nicho": "nicho",
}

# Campos com fallback (campo_destino: [campo_principal, campo_fallback])
FIELD_FALLBACKS = {
    "status_implantacao": ["statusimplantacao", "grupofavorecido"],
}


def map_oamd_to_frontend(empresa, id_favorecido=None):
    """
    Mapeia os campos da resposta OAMD para o formato esperado pelo Frontend.

    Args:
        empresa: Dicionário com dados da empresa do OAMD
        id_favorecido: ID do favorecido para construção de links

    Returns:
        dict: Dados mapeados para o formato do frontend
    """
    mapped = {}

    # Mapeamento direto de campos
    for frontend_field, oamd_field in FIELD_MAPPING.items():
        mapped[frontend_field] = empresa.get(oamd_field)

    # Mapeamento de campos com fallback
    for frontend_field, oamd_fields in FIELD_FALLBACKS.items():
        value = None
        for field in oamd_fields:
            value = empresa.get(field)
            if value:
                break
        mapped[frontend_field] = value

    # Extrair código de infraestrutura
    try:
        infra_code = extract_infra_code(empresa, id_favorecido)
        mapped["informacao_infra"] = infra_code
    except Exception:
        mapped["informacao_infra"] = ""

    # Construir link da tela de apoio
    try:
        mapped["tela_apoio_link"] = build_tela_apoio_link(id_favorecido)
    except Exception:
        mapped["tela_apoio_link"] = ""

    return mapped


def validate_mapped_data(mapped):
    """
    Valida e limpa os dados mapeados.

    Args:
        mapped: Dicionário com dados mapeados

    Returns:
        dict: Dados validados e limpos
    """
    cleaned = {}

    for key, value in mapped.items():
        if value is None:
            cleaned[key] = ""
        elif isinstance(value, str):
            cleaned[key] = value.strip()
        else:
            cleaned[key] = value

    return cleaned


def get_mapped_field_list():
    """
    Retorna a lista de todos os campos mapeados.
    Útil para documentação e debugging.

    Returns:
        list: Lista de nomes de campos do frontend
    """
    fields = list(FIELD_MAPPING.keys())
    fields.extend(FIELD_FALLBACKS.keys())
    fields.extend(["informacao_infra", "tela_apoio_link"])
    return fields
