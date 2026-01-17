"""
Helpers para processamento de formulários de implantação.
Extrai a lógica de processamento de formulários das rotas.
Princípio SOLID: Single Responsibility
"""

from datetime import date, datetime

from flask import request

from ...config.logging_config import app_logger
from ...constants import NAO_DEFINIDO_BOOL


def get_form_value(key):
    """Obtém valor do form, retornando None se vazio."""
    value = request.form.get(key, "").strip()
    if value == "":
        return None
    return value


def get_boolean_value(key):
    """Obtém valor booleano do form."""
    value = request.form.get(key, NAO_DEFINIDO_BOOL).strip()
    if value == NAO_DEFINIDO_BOOL or value == "":
        return None
    return value


def get_multiple_value(key):
    """Retorna valores de seleção múltipla como string separada por vírgula."""
    values = request.form.getlist(key)
    # Remover valores vazios e "Selecione..."
    values = [v.strip() for v in values if v and v.strip() and v.strip() != "Selecione..."]
    return ",".join(values) if values else None


def get_integer_value(key, default=0):
    """Obtém valor inteiro do form."""
    try:
        raw = request.form.get(key, str(default)).strip()
        return int(raw) if raw else default
    except (ValueError, TypeError):
        return default


def normalize_date_str(s):
    """
    Converte DD/MM/AAAA para YYYY-MM-DD ou retorna None.
    Aceita formatos: DD/MM/AAAA, YYYY-MM-DD
    """
    try:
        if not s:
            return None

        s = str(s).strip()
        if not s or s == "":
            return None

        # Formato YYYY-MM-DD
        if len(s) == 10 and s[4] == "-" and s[7] == "-":
            try:
                datetime.strptime(s, "%Y-%m-%d")
                return s
            except Exception:
                pass

        # Formato DD/MM/YYYY
        if "/" in s:
            parts = s.split("/")
            if len(parts) == 3:
                day = parts[0].strip().zfill(2)
                month = parts[1].strip().zfill(2)
                year = parts[2].strip()

                result = f"{year}-{month}-{day}"

                try:
                    datetime.strptime(result, "%Y-%m-%d")
                    return result
                except Exception:
                    return None

        return None

    except Exception as e:
        app_logger.error(f"ERRO ao normalizar data '{s}': {e}")
        return None


def parse_valor_monetario(valor_raw):
    """
    Processa valor monetário do formulário.
    Aceita formatos: R$ 1.234,56 ou 1234.56
    Retorna string formatada ou None.
    """
    if valor_raw is None:
        return None

    v = valor_raw.replace("R$", "").replace(" ", "").strip()

    if not v:
        return None

    try:
        # Se tem vírgula, é formato BR: 1.234,56
        if "," in v:
            v = v.replace(".", "").replace(",", ".")  # 1.234,56 -> 1234.56
        # Se não tem vírgula mas tem ponto, remove pontos (são separadores de milhar BR)
        elif "." in v:
            v = v.replace(".", "")  # 1.000 -> 1000

        v_float = float(v)
        return f"{v_float:.2f}"
    except (ValueError, AttributeError) as e:
        app_logger.error(f"Erro ao converter valor monetário: {e}")
        return None


def validate_telefone(telefone_raw):
    """
    Valida e formata número de telefone brasileiro.
    Aceita 10 ou 11 dígitos.
    Retorna telefone formatado ou None se inválido.
    """
    if not telefone_raw:
        return None, None

    # Remove caracteres não numéricos
    telefone_numeros = "".join(filter(str.isdigit, telefone_raw))

    # Valida: deve ter 10 ou 11 dígitos
    if len(telefone_numeros) >= 10 and len(telefone_numeros) <= 11:
        # Formata: (XX) XXXXX-XXXX ou (XX) XXXX-XXXX
        if len(telefone_numeros) == 11:
            return f"({telefone_numeros[:2]}) {telefone_numeros[2:7]}-{telefone_numeros[7:]}", None
        else:
            return f"({telefone_numeros[:2]}) {telefone_numeros[2:6]}-{telefone_numeros[6:]}", None
    else:
        return None, "Telefone inválido. Use o formato (XX) XXXXX-XXXX ou (XX) XXXX-XXXX"


def build_detalhes_campos():
    """
    Constrói dicionário de campos para atualização de detalhes de implantação.
    Extrai todos os valores do request.form e aplica validações.

    Returns:
        tuple: (campos_dict, error_message ou None)
    """
    # Validar telefone primeiro
    telefone_raw = get_form_value("telefone_responsavel")
    telefone_validado, telefone_error = validate_telefone(telefone_raw)
    if telefone_error:
        return None, telefone_error

    # Processar datas
    data_inicio_producao = normalize_date_str(get_form_value("data_inicio_producao"))
    data_final_implantacao = normalize_date_str(get_form_value("data_final_implantacao"))
    data_inicio_efetivo = normalize_date_str(get_form_value("data_inicio_efetivo"))

    # Processar valor monetário
    valor_monetario = parse_valor_monetario(get_form_value("valor_monetario"))

    # Processar campos múltiplos
    seguimento_val = get_multiple_value("seguimento")
    tipos_planos_val = get_multiple_value("tipos_planos")
    modalidades_val = get_multiple_value("modalidades")
    horarios_val = get_multiple_value("horarios_func")
    formas_pagamento_val = get_multiple_value("formas_pagamento")

    # Processar campos simples
    cargo_responsavel_val = get_form_value("cargo_responsavel")
    nivel_receita_val = get_form_value("nivel_receita")
    sistema_anterior_val = get_form_value("sistema_anterior")
    recorrencia_usa_val = get_form_value("recorrencia_usa")

    # Processar alunos ativos
    alunos_ativos = get_integer_value("alunos_ativos", 0)

    # Construir dicionário de campos
    campos = {
        "responsavel_cliente": get_form_value("responsavel_cliente"),
        "cargo_responsavel": cargo_responsavel_val,
        "telefone_responsavel": telefone_validado,
        "email_responsavel": get_form_value("email_responsavel"),
        "data_inicio_producao": data_inicio_producao,
        "data_final_implantacao": data_final_implantacao,
        "data_inicio_efetivo": data_inicio_efetivo,
        "id_favorecido": get_form_value("id_favorecido"),
        "nivel_receita": nivel_receita_val,
        "chave_oamd": get_form_value("chave_oamd"),
        "tela_apoio_link": get_form_value("tela_apoio_link"),
        "informacao_infra": get_form_value("informacao_infra"),
        "seguimento": seguimento_val,
        "tipos_planos": tipos_planos_val,
        "modalidades": modalidades_val,
        "horarios_func": horarios_val,
        "formas_pagamento": formas_pagamento_val,
        "diaria": get_boolean_value("diaria"),
        "freepass": get_boolean_value("freepass"),
        "alunos_ativos": alunos_ativos,
        "sistema_anterior": sistema_anterior_val,
        "importacao": get_boolean_value("importacao"),
        "recorrencia_usa": recorrencia_usa_val,
        "boleto": get_boolean_value("boleto"),
        "nota_fiscal": get_boolean_value("nota_fiscal"),
        "catraca": get_boolean_value("catraca"),
        "modelo_catraca": get_form_value("modelo_catraca") if get_boolean_value("catraca") == "Sim" else None,
        "facial": get_boolean_value("facial"),
        "modelo_facial": get_form_value("modelo_facial") if get_boolean_value("facial") == "Sim" else None,
        "wellhub": get_boolean_value("wellhub"),
        "totalpass": get_boolean_value("totalpass"),
        "cnpj": get_form_value("cnpj"),
        "status_implantacao_oamd": get_form_value("status_implantacao_oamd"),
        "nivel_atendimento": get_form_value("nivel_atendimento"),
        "valor_monetario": valor_monetario,
        "resp_estrategico_nome": get_form_value("resp_estrategico_nome"),
        "resp_onb_nome": get_form_value("resp_onb_nome"),
        "resp_estrategico_obs": get_form_value("resp_estrategico_obs"),
        "contatos": get_form_value("contatos"),
    }

    # Limpar chave OAMD
    co = campos.get("chave_oamd")
    if co and isinstance(co, str):
        campos["chave_oamd"] = co.strip() if co.strip() else None

    # Preparar campos finais (converter datas)
    final_campos = {}
    for k, v in campos.items():
        if v is None:
            final_campos[k] = None
        elif isinstance(v, str):
            final_campos[k] = v
        elif isinstance(v, (datetime, date)):
            try:
                final_campos[k] = v.strftime("%Y-%m-%d")
            except Exception:
                final_campos[k] = str(v)
        else:
            final_campos[k] = v

    return final_campos, None
