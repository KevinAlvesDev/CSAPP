import logging
logger = logging.getLogger(__name__)
"""
Módulo de Utilitários do External Service
Funções auxiliares para serialização e extração de códigos.
Princípio SOLID: Single Responsibility
"""

import contextlib
import json
import re
from decimal import Decimal


def json_safe_value(v):
    """
    Converte um valor para formato JSON-serializável.
    Trata tipos especiais como Decimal, datetime, bytes, etc.

    Args:
        v: Valor a ser convertido

    Returns:
        Valor convertido para tipo JSON-serializável
    """
    if v is None:
        return ""

    # Converter datetime/date para ISO format
    if hasattr(v, "isoformat"):
        try:
            return v.isoformat()
        except Exception as exc:
            logger.exception("Unhandled exception", exc_info=True)
            pass

    # Converter Decimal para string
    if isinstance(v, Decimal):
        return str(v)

    # Converter bytes para string UTF-8
    if isinstance(v, (bytes, bytearray, memoryview)):
        try:
            return bytes(v).decode("utf-8", "replace")
        except Exception as exc:
            logger.exception("Unhandled exception", exc_info=True)
            return str(v)

    # Converter listas recursivamente
    if isinstance(v, (list, tuple)):
        try:
            return [json_safe_value(x) for x in v]
        except Exception as exc:
            logger.exception("Unhandled exception", exc_info=True)
            return [str(x) for x in v]

    # Converter dicts recursivamente
    if isinstance(v, dict):
        try:
            return {str(k): json_safe_value(val) for k, val in v.items()}
        except Exception as exc:
            logger.exception("Unhandled exception", exc_info=True)
            return {str(k): str(val) for k, val in v.items()}

    # Verificar se já é JSON-serializável
    try:
        json.dumps(v)
        return v
    except Exception as exc:
        logger.exception("Unhandled exception", exc_info=True)
        return str(v)


def sanitize_empresa_data(empresa):
    """
    Converte todos os campos de uma empresa para formato JSON-seguro.

    Args:
        empresa: Dicionário com dados da empresa

    Returns:
        tuple: (empresa_sanitizada, tipos_originais)
    """
    tipos = {}
    empresa_safe = {}

    for k, v in empresa.items():
        tipos[k] = type(v).__name__
        empresa_safe[k] = json_safe_value(v)

    return empresa_safe, tipos


def _extract_digits_from_any_field(empresa) -> str | None:
    """Estratégia 1: busca padrão ZW_### em qualquer campo string da empresa."""
    for _v in empresa.values():
        if isinstance(_v, str) and _v:
            m = re.search(r"(?i)\bZW[_\-]?(\d{2,})\b", _v)
            if m:
                return m.group(1)
    return None


def _extract_digits_from_nomeempresazw(empresa) -> str | None:
    """Estratégia 2: busca no campo nomeempresazw."""
    nomezw = str(empresa.get("nomeempresazw") or "").strip()
    if not nomezw:
        return None
    m = re.search(r"zw[_\-]?(\d+)", nomezw, re.IGNORECASE)
    return m.group(1) if m else None


def _extract_digits_from_url_fields(empresa) -> str | None:
    """Estratégia 3: busca em campos cujo nome contenha 'url'."""
    for k, v in empresa.items():
        if k and "url" in str(k).lower() and v:
            m = re.search(r"zw(\d+)", str(v), re.IGNORECASE)
            if m:
                return m.group(1)
    return None


def _extract_digits_from_empresazw(empresa) -> str | None:
    """Estratégia 4: usa o campo empresazw diretamente como número."""
    empzw = empresa.get("empresazw")
    with contextlib.suppress(Exception):
        ci = int(empzw) if empzw is not None else None
        if ci is not None and ci > 0 and ci != 1:
            return str(ci)
    return None


def _extract_digits_from_id_favorecido(id_favorecido) -> str | None:
    """Estratégia 5: fallback usando o ID Favorecido."""
    if not id_favorecido:
        return None
    with contextlib.suppress(Exception):
        return str(int(id_favorecido))
    return None


def extract_infra_code(empresa, id_favorecido=None):
    """
    Extrai o código de infraestrutura (ZW_###) dos dados da empresa.
    Tenta 5 estratégias em ordem de prioridade, retornando a primeira que funcionar.

    Returns:
        str: Código de infra no formato 'ZW_###' ou string vazia
    """
    strategies = [
        _extract_digits_from_any_field(empresa),
        _extract_digits_from_nomeempresazw(empresa),
        _extract_digits_from_url_fields(empresa),
        _extract_digits_from_empresazw(empresa),
        _extract_digits_from_id_favorecido(id_favorecido),
    ]

    for digits in strategies:
        if digits and len(digits) >= 2:
            return f"ZW_{digits}"

    return ""


def build_tela_apoio_link(id_favorecido):
    """
    Constrói o link da Tela de Apoio com o ID Favorecido.

    Args:
        id_favorecido: ID do favorecido

    Returns:
        str: URL da tela de apoio ou string vazia
    """
    if id_favorecido:
        return f"https://app.pactosolucoes.com.br/apoio/apoio/{id_favorecido}"
    return ""