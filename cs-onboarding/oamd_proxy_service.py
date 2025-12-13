"""
Proxy Service para consultas OAMD
Este serviço deve rodar em um servidor com acesso ao banco OAMD
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)  # Permitir requisições do app principal

# Configuração do banco OAMD
OAMD_CONFIG = {
    'host': 'oamd.pactosolucoes.com.br',
    'port': 5432,
    'user': 'cs_pacto',
    'password': 'pacto@db',
    'database': 'oamd'
}

# Token de segurança (gere um aleatório)
API_TOKEN = os.getenv('PROXY_API_TOKEN', 'seu-token-secreto-aqui-mude-isso')


def get_db_connection():
    """Cria conexão com o banco OAMD"""
    return psycopg2.connect(**OAMD_CONFIG, cursor_factory=RealDictCursor)


@app.before_request
def verify_token():
    """Verifica token de autenticação"""
    if request.path == '/health':
        return None
    
    token = request.headers.get('X-API-Token')
    if token != API_TOKEN:
        return jsonify({'error': 'Unauthorized'}), 401


@app.route('/health')
def health():
    """Health check"""
    try:
        conn = get_db_connection()
        conn.close()
        return jsonify({'status': 'ok', 'database': 'connected'})
    except Exception as e:
        return jsonify({'status': 'error', 'database': str(e)}), 500


@app.route('/api/consultar_empresa', methods=['GET'])
def consultar_empresa():
    """
    Consulta empresa no banco OAMD
    Query params: id_favorecido ou infra
    """
    id_favorecido = request.args.get('id_favorecido')
    infra_req = request.args.get('infra')
    
    if not id_favorecido and not infra_req:
        return jsonify({'ok': False, 'error': 'Informe ID Favorecido ou Infra'}), 400
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
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
        
        if id_favorecido:
            # Tentar por codigofinanceiro primeiro
            cursor.execute(
                query.format(where_clause="ef.codigofinanceiro = %s"),
                (id_favorecido,)
            )
            result = cursor.fetchone()
            
            # Se não encontrou, tentar por codigo
            if not result:
                cursor.execute(
                    query.format(where_clause="ef.codigo = %s"),
                    (id_favorecido,)
                )
                result = cursor.fetchone()
        else:
            # Busca por infra
            import re
            digits = ''.join(re.findall(r"\d+", str(infra_req)))
            if digits:
                cursor.execute(
                    query.format(where_clause="ef.empresazw = %s"),
                    (int(digits),)
                )
                result = cursor.fetchone()
            else:
                result = None
        
        cursor.close()
        conn.close()
        
        if not result:
            return jsonify({
                'ok': False,
                'error': 'Empresa não encontrada para este ID Favorecido.',
                'status_code': 404
            }), 404
        
        # Converter para formato esperado
        empresa = dict(result)
        
        # Processar datas
        if empresa.get('datacadastro'):
            empresa['datacadastro'] = empresa['datacadastro'].isoformat()
        
        return jsonify({
            'ok': True,
            'empresa': empresa,
            'mapped': {
                'chave_oamd': empresa.get('chavezw'),
                'cnpj': empresa.get('cnpj'),
                'data_cadastro': empresa.get('datacadastro'),
                'informacao_infra': f"ZW_{empresa.get('empresazw')}" if empresa.get('empresazw') else None,
                'tela_apoio_link': f"https://app.pactosolucoes.com.br/apoio/apoio/{empresa.get('codigofinanceiro')}" if empresa.get('codigofinanceiro') else None
            }
        })
        
    except Exception as e:
        app.logger.error(f"Erro ao consultar OAMD: {e}", exc_info=True)
        return jsonify({'ok': False, 'error': str(e)}), 500


if __name__ == '__main__':
    # Rodar na porta 5001 para não conflitar com o app principal
    app.run(host='0.0.0.0', port=5001, debug=True)
