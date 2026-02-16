"""
Módulo de Consulta OAMD
Função principal para consulta de empresas no banco externo OAMD.
Princípio SOLID: Single Responsibility (orquestração)
"""

import contextlib
import json

from sqlalchemy.exc import OperationalError

from .....config.logging_config import api_logger
from .mapper import map_oamd_to_frontend
from .query import execute_oamd_search
from .utils import sanitize_empresa_data


def consultar_empresa_oamd(id_favorecido=None, infra_req=None):
    """
    Consulta dados da empresa no banco externo (OAMD) via ID Favorecido ou Infra.

    Esta função é o ponto de entrada principal para consultas ao banco OAMD.
    Ela orquestra a busca, sanitização e mapeamento dos dados.

    Args:
        id_favorecido: ID do favorecido no sistema financeiro
        infra_req: Código de infraestrutura (ex: 'ZW_123')

    Returns:
        dict: {
            'ok': bool,
            'empresa': dict (dados brutos sanitizados),
            'mapped': dict (dados mapeados para o frontend),
            'error': str (se houver erro),
            'status_code': int (código HTTP sugerido em caso de erro)
        }
    """
    # Validação de entrada
    if not id_favorecido and not infra_req:
        return {"ok": False, "error": "Informe ID Favorecido ou Infra (ZW_###).", "status_code": 400}

    try:
        # Executar busca no banco OAMD
        results = execute_oamd_search(id_favorecido=id_favorecido, infra_req=infra_req)

        # Verificar se encontrou resultados
        if not results:
            return {"ok": False, "error": "Empresa não encontrada para este ID Favorecido.", "status_code": 404}

        # Processar primeiro resultado
        empresa_raw = results[0]

        # Sanitizar dados para JSON
        empresa, tipos = sanitize_empresa_data(empresa_raw)

        # Logar tipos para debugging
        with contextlib.suppress(Exception):
            api_logger.info(f"consulta_oamd_tipos: {tipos}")

        # Mapear campos para o frontend
        mapped = map_oamd_to_frontend(empresa, id_favorecido)

        # Construir resposta
        response = {"ok": True, "empresa": empresa, "mapped": mapped}

        # Validar que a resposta é JSON-serializável
        return _ensure_json_serializable(response)

    except OperationalError as e:
        return _handle_connection_error(e, id_favorecido)

    except Exception as e:
        return _handle_general_error(e, id_favorecido)


def _ensure_json_serializable(response):
    """
    Garante que a resposta seja JSON-serializável.

    Args:
        response: Dicionário de resposta

    Returns:
        dict: Resposta garantidamente serializável
    """
    try:
        # Testa serialização
        json.dumps(response)
        return response

    except Exception as se:
        api_logger.error(f"json_serialize_error consultar_empresa: {se}")

        # Fallback: converter tudo para strings
        empresa_safe = _force_string_values(response.get("empresa", {}))
        mapped_safe = _force_string_values(response.get("mapped", {}))

        return {"ok": True, "empresa": empresa_safe, "mapped": mapped_safe}


def _force_string_values(data):
    """
    Força todos os valores para strings.

    Args:
        data: Dicionário com dados

    Returns:
        dict: Dicionário com valores convertidos para string
    """
    result = {}
    for k, v in data.items():
        if isinstance(v, (dict, list)):
            result[str(k)] = json.dumps(v, ensure_ascii=False)
        else:
            result[str(k)] = str(v) if v is not None else ""
    return result


def _handle_connection_error(error, id_favorecido):
    """
    Trata erros de conexão com o banco OAMD.

    Args:
        error: Exceção OperationalError
        id_favorecido: ID usado na consulta (para logging)

    Returns:
        dict: Resposta de erro formatada
    """
    api_logger.error(f"Erro de conexão OAMD ao consultar ID {id_favorecido}: {error}")

    error_msg = str(error).lower()

    if "timeout" in error_msg or "timed out" in error_msg:
        return {
            "ok": False,
            "error": "Tempo limite excedido. Verifique sua conexão com a VPN/Rede.",
            "status_code": 504,
        }

    return {"ok": False, "error": "Falha na conexão com o banco externo.", "status_code": 502}


def _handle_general_error(error, id_favorecido):
    """
    Trata erros gerais na consulta.

    Args:
        error: Exceção genérica
        id_favorecido: ID usado na consulta (para logging)

    Returns:
        dict: Resposta de erro formatada
    """
    api_logger.error(f"Erro ao consultar empresa ID {id_favorecido}: {error}", exc_info=True)

    return {"ok": False, "error": "Erro ao consultar banco de dados externo.", "status_code": 500}
