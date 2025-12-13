
import json
import os
from decimal import Decimal
from flask import current_app
from sqlalchemy.exc import OperationalError

from ..config.logging_config import api_logger
from ..database.external_db import query_external_db
from ..common.validation import validate_integer


def _consultar_via_proxy(id_favorecido=None, infra_req=None):
    """
    Fallback: Consulta via proxy HTTP quando banco direto não está acessível.
    """
    import requests
    
    proxy_url = os.getenv('OAMD_PROXY_URL', 'http://localhost:5001')
    proxy_token = os.getenv('OAMD_PROXY_TOKEN', '')
    
    if not proxy_url:
        return None
    
    try:
        params = {}
        if id_favorecido:
            params['id_favorecido'] = id_favorecido
        if infra_req:
            params['infra'] = infra_req
        
        headers = {}
        if proxy_token:
            headers['X-API-Token'] = proxy_token
        
        response = requests.get(
            f"{proxy_url}/api/consultar_empresa",
            params=params,
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            api_logger.info(f"Consulta OAMD via proxy bem-sucedida para ID {id_favorecido}")
            return data
        else:
            api_logger.warning(f"Proxy retornou status {response.status_code}: {response.text}")
            return None
            
    except Exception as e:
        api_logger.error(f"Erro ao consultar via proxy: {e}")
        return None


def consultar_empresa_oamd(id_favorecido=None, infra_req=None):
    """
    Consulta dados da empresa no banco externo (OAMD) via ID Favorecido ou Infra.
    Tenta conexão direta primeiro, depois proxy HTTP como fallback.
    Retorna um dicionário com 'ok', 'empresa', 'mapped' ou 'error'.
    """
    if not id_favorecido and not infra_req:
        return {'ok': False, 'error': 'Informe ID Favorecido ou Infra (ZW_###).', 'status_code': 400}

    # Tentar conexão direta primeiro
    try:
        # Consulta melhorada: inclui codigo e prioriza busca por ele
        query = """
            SELECT 
                ef.codigo,
                ef.codigofinanceiro,
                ef.nomefantasia,
                ef.razaosocial,
                ef.cnpj,
                ef.email,
                ef.telefone,
                ef.datacadastro,
                ef.chavezw,
                ef.nomeempresazw,
                ef.empresazw
            FROM empresafinanceiro ef
            WHERE {where_clause}
            LIMIT 1
        """
        params = {}
        
        # Lógica de busca: Tentar ef.codigofinanceiro primeiro (pedido do usuario), depois ef.codigo
        if infra_req and not id_favorecido:
            import re as _re
            digits = ''.join(_re.findall(r"\d+", str(infra_req)))
            try:
                emp_int = int(digits)
            except Exception:
                emp_int = None
            if emp_int:
                where_clause = "ef.empresazw = :empresazw"
                params['empresazw'] = emp_int
            else:
                where_clause = "LOWER(ef.nomeempresazw) LIKE :nomezw"
                params['nomezw'] = f"%{str(infra_req).lower()}%"
            
            results = query_external_db(query.format(where_clause=where_clause), params) or []

        else:
            # Busca por ID Favorecido
            params['id_favorecido'] = id_favorecido
            
            # 1. Tentar por ef.codigofinanceiro (Lógica original/preferida)
            try:
                where_clause = "ef.codigofinanceiro = :id_favorecido"
                results = query_external_db(query.format(where_clause=where_clause), params) or []
            except Exception as e:
                api_logger.warning(f"Erro ao buscar por ef.codigofinanceiro: {e}")
                results = []

            # 2. Se não achou, tentar por ef.codigo (Fallback)
            if not results:
                try:
                    where_clause = "ef.codigo = :id_favorecido"
                    results = query_external_db(query.format(where_clause=where_clause), params) or []
                except Exception as e:
                    api_logger.warning(f"Erro ao buscar por ef.codigo: {e}")
                    pass

        if not results:
            return {'ok': False, 'error': 'Empresa não encontrada para este ID Favorecido.', 'status_code': 404}

        empresa = results[0]

        def _json_safe(v):
            if v is None:
                return ""
            if hasattr(v, 'isoformat'):
                try:
                    return v.isoformat()
                except Exception:
                    pass
            if isinstance(v, Decimal):
                return str(v)
            if isinstance(v, (bytes, bytearray, memoryview)):
                try:
                    return bytes(v).decode('utf-8', 'replace')
                except Exception:
                    return str(v)
            if isinstance(v, (list, tuple)):
                try:
                    return [_json_safe(x) for x in v]
                except Exception:
                    return [str(x) for x in v]
            if isinstance(v, dict):
                try:
                    return {str(k): _json_safe(val) for k, val in v.items()}
                except Exception:
                    return {str(k): str(val) for k, val in v.items()}
            try:
                json.dumps(v)
                return v
            except Exception:
                return str(v)

        tipos = {}
        for k, v in list(empresa.items()):
            tipos[k] = type(v).__name__
            empresa[k] = _json_safe(v)
        try:
            api_logger.info(f"consulta_oamd_tipos: {tipos}")
        except Exception:
            pass

        # Mapeamento de campos OAMD para campos do Frontend
        mapped = {}

        # Função auxiliar para buscar chaves insensíveis a maiúsculas/minúsculas e variações
        def find_value(keys_to_try):
            for k in keys_to_try:
                for emp_k in empresa.keys():
                    if emp_k.lower().replace('_', '').replace(' ', '') == k.lower().replace('_', '').replace(' ', ''):
                        return empresa[emp_k]
            return None

        mapped['data_inicio_producao'] = find_value(['iniciodeproducao', 'inicioproducao', 'inicio_producao', 'dt_inicio_producao', 'dataproducao'])
        mapped['data_inicio_efetivo'] = find_value(['inicioimplantacao', 'inicio_implantacao', 'dt_inicio_implantacao', 'dataimplantacao'])
        mapped['data_final_implantacao'] = find_value(['finalimplantacao', 'final_implantacao', 'dt_final_implantacao', 'fimimplantacao', 'datafinalimplantacao'])
        mapped['status_implantacao'] = find_value(['status', 'statusimplantacao', 'situacao'])
        mapped['nivel_atendimento'] = find_value(['nivelatendimento', 'nivel_atendimento', 'classificacao'])
        mapped['nivel_receita'] = find_value(['nivelreceita', 'nivel_receita', 'faixareceita', 'mrr', 'nivelreceitamensal'])
        mapped['chave_oamd'] = empresa.get('chavezw')
        
        try:
            infra_code = None
            digits_pref = None
            import re as _re
            for _k, _v in empresa.items():
                if isinstance(_v, str) and _v:
                    m = _re.search(r"(?i)\bZW[_\-]?(\d{2,})\b", _v)
                    if m:
                        digits_pref = m.group(1)
                        break
            nomezw = str(empresa.get('nomeempresazw') or '').strip()
            if nomezw:
                mname = _re.search(r"zw[_\-]?(\d+)", nomezw, _re.IGNORECASE)
                if mname:
                    digits_pref = mname.group(1)
            if not digits_pref:
                # tentar extrair de qualquer URL presente nos campos retornados
                for k, v in empresa.items():
                    if k and 'url' in str(k).lower() and v:
                        murl = _re.search(r"zw(\d+)", str(v), _re.IGNORECASE)
                        if murl:
                            digits_pref = murl.group(1)
                            break
            if not digits_pref:
                empzw = empresa.get('empresazw')
                try:
                    ci = int(empzw) if empzw is not None else None
                    if ci is not None and ci > 0 and ci != 1:
                        digits_pref = str(ci)
                except Exception:
                    pass
            if digits_pref and len(digits_pref) >= 2:
                infra_code = f"ZW_{digits_pref}"
                mapped['informacao_infra'] = infra_code
            else:
                mapped['informacao_infra'] = mapped.get('informacao_infra') or ''
            
            # Forçar padrão de Tela de Apoio com ID Favorecido
            if id_favorecido:
                mapped['tela_apoio_link'] = f"https://app.pactosolucoes.com.br/apoio/apoio/{id_favorecido}"
        except Exception:
            mapped['informacao_infra'] = mapped.get('informacao_infra') or ''
            mapped['tela_apoio_link'] = mapped.get('tela_apoio_link') or ''
            
        mapped['cnpj'] = empresa.get('cnpj')
        mapped['data_cadastro'] = find_value(['datacadastro', 'data_cadastro', 'created_at', 'dt_cadastro'])

        try:
            # Tenta serializar para garantir que não há objetos complexos
            test_payload = {'ok': True, 'empresa': empresa, 'mapped': mapped}
            json.dumps(test_payload)
            return test_payload
        except Exception as se:
            try:
                api_logger.error(f"json_serialize_error consultar_empresa: {se}")
            except Exception:
                pass
            empresa_safe = {str(k): str(v) if not isinstance(v, (dict, list)) else json.dumps(v, ensure_ascii=False) for k, v in empresa.items()}
            mapped_safe = {str(k): str(v) if not isinstance(v, (dict, list)) else json.dumps(v, ensure_ascii=False) for k, v in mapped.items()}
            return {'ok': True, 'empresa': empresa_safe, 'mapped': mapped_safe}

    except OperationalError as e:
        api_logger.error(f"Erro de conexão OAMD ao consultar ID {id_favorecido}: {e}")
        
        # Tentar via proxy como fallback
        proxy_result = _consultar_via_proxy(id_favorecido, infra_req)
        if proxy_result and proxy_result.get('ok'):
            return proxy_result
        
        error_msg = str(e).lower()
        if "timeout" in error_msg or "timed out" in error_msg:
            return {'ok': False, 'error': 'Tempo limite excedido. Verifique sua conexão com a VPN/Rede.', 'status_code': 504}
        return {'ok': False, 'error': 'Falha na conexão com o banco externo. Proxy também indisponível.', 'status_code': 502}

    except Exception as e:
        api_logger.error(f"Erro ao consultar empresa ID {id_favorecido}: {e}", exc_info=True)
        
        # Tentar via proxy como fallback
        proxy_result = _consultar_via_proxy(id_favorecido, infra_req)
        if proxy_result and proxy_result.get('ok'):
            return proxy_result
            
        return {'ok': False, 'error': 'Erro ao consultar banco de dados externo. Proxy também indisponível.', 'status_code': 500}
