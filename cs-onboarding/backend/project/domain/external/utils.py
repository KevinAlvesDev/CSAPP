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
        except Exception:
            pass

    # Converter Decimal para string
    if isinstance(v, Decimal):
        return str(v)

    # Converter bytes para string UTF-8
    if isinstance(v, (bytes, bytearray, memoryview)):
        try:
            return bytes(v).decode("utf-8", "replace")
        except Exception:
            return str(v)

    # Converter listas recursivamente
    if isinstance(v, (list, tuple)):
        try:
            return [json_safe_value(x) for x in v]
        except Exception:
            return [str(x) for x in v]

    # Converter dicts recursivamente
    if isinstance(v, dict):
        try:
            return {str(k): json_safe_value(val) for k, val in v.items()}
        except Exception:
            return {str(k): str(val) for k, val in v.items()}

    # Verificar se já é JSON-serializável
    try:
        json.dumps(v)
        return v
    except Exception:
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


def extract_infra_code(empresa, id_favorecido=None):
    """
    Extrai o código de infraestrutura (ZW_###) dos dados da empresa.

    Args:
        empresa: Dicionário com dados da empresa
        id_favorecido: ID favorecido para fallback

    Returns:
        str: Código de infra no formato 'ZW_###' ou string vazia
    """
    digits_pref = None

    # 1. Tentar extrair de qualquer campo que contenha ZW_###
    for _k, _v in empresa.items():
        if isinstance(_v, str) and _v:
            m = re.search(r"(?i)\bZW[_\-]?(\d{2,})\b", _v)
            if m:
                digits_pref = m.group(1)
                break

    # 2. Tentar extrair do nomeempresazw
    if not digits_pref:
        nomezw = str(empresa.get("nomeempresazw") or "").strip()
        if nomezw:
            mname = re.search(r"zw[_\-]?(\d+)", nomezw, re.IGNORECASE)
            if mname:
                digits_pref = mname.group(1)

    # 3. Tentar extrair de campos que contenham URL
    if not digits_pref:
        for k, v in empresa.items():
            if k and "url" in str(k).lower() and v:
                murl = re.search(r"zw(\d+)", str(v), re.IGNORECASE)
                if murl:
                    digits_pref = murl.group(1)
                    break

    # 4. Tentar usar empresazw diretamente
    if not digits_pref:
        empzw = empresa.get("empresazw")
        try:
            ci = int(empzw) if empzw is not None else None
            if ci is not None and ci > 0 and ci != 1:
                digits_pref = str(ci)
        except Exception:
            pass

    # 5. Fallback: usar codigofinanceiro (ID Favorecido)
    if not digits_pref and id_favorecido:
        with contextlib.suppress(Exception):
            digits_pref = str(int(id_favorecido))

    # Formatar resultado
    if digits_pref and len(digits_pref) >= 2:
        return f"ZW_{digits_pref}"

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
