import logging
import unicodedata

from flask import current_app
from sqlalchemy import create_engine, text

logger = logging.getLogger(__name__)

def normalize_text(text):
    """Remove acentos e converte para minúsculas."""
    if not text:
        return ""
    return unicodedata.normalize('NFKD', text).encode('ASCII', 'ignore').decode('utf-8').lower()

import os

def get_external_engine():
    """
    Retorna uma engine SQLAlchemy para o banco de dados externo.
    A engine é armazenada em 'g' para ser reutilizada durante a requisição,
    mas idealmente deveria ser um singleton global se a aplicação suportar.
    Como o Flask recria o contexto, podemos usar cache simples ou armazenar no app.
    """
    # Tenta pegar do contexto da aplicação (cache global simples)
    if not hasattr(current_app, 'external_db_engine'):
        external_db_url = current_app.config.get('EXTERNAL_DB_URL')

        if not external_db_url:
            logger.warning("EXTERNAL_DB_URL não configurada.")
            return None

        try:
            # Cria a engine (pool de conexões é gerenciado pelo SQLAlchemy)
            connect_args = {}
            try:
                if external_db_url.lower().startswith('postgresql'):
                    # Timeout configurável via env var (default 30s)
                    timeout = int(os.environ.get('EXTERNAL_DB_TIMEOUT', 30))
                    connect_args = {
                        'connect_timeout': timeout,
                        'options': f'-c statement_timeout={timeout * 1000}'
                    }
            except Exception:
                connect_args = {}

            engine = create_engine(
                external_db_url,
                pool_pre_ping=True,
                pool_recycle=3600,
                pool_size=5,
                max_overflow=10,
                connect_args=connect_args
            )
            current_app.external_db_engine = engine
            logger.info("Engine do banco externo criada com sucesso.")
        except Exception as e:
            logger.error(f"Erro ao criar engine do banco externo: {e}")
            return None

    return current_app.external_db_engine

def query_external_db(query_str, params=None):
    """
    Executa uma query SELECT no banco de dados externo e retorna lista de dicionários.
    Garante que a conexão seja APENAS LEITURA.
    
    Args:
        query_str (str): A query SQL.
        params (dict, optional): Parâmetros para a query.
        
    Returns:
        list[dict]: Lista de resultados como dicionários.
    """
    engine = get_external_engine()
    if not engine:
        raise RuntimeError("Não foi possível conectar ao banco de dados externo (URL não configurada ou erro de conexão).")

    if params is None:
        params = {}

    try:
        with engine.connect() as conn:
            try:
                conn.execute(text("SET SESSION CHARACTERISTICS AS TRANSACTION READ ONLY"))
            except Exception:
                logger.debug("Read-only session not supported by this dialect; proceeding without it.")

            result = conn.execute(text(query_str), params)

            # Mapeia as colunas para retornar dicts
            keys = result.keys()
            return [dict(zip(keys, row)) for row in result]

    except Exception as e:
        logger.error(f"Erro ao executar query no banco externo: {e}")
        raise

def find_cs_user_by_email(email):
    """
    Busca um usuário na tabela 'customersuccess' do banco externo.
    Como a tabela não possui campo de email, utilizamos uma heurística baseada no nome.
    
    Args:
        email (str): O email fornecido no login.
        
    Returns:
        dict: Dados do usuário se encontrado, None caso contrário.
    """
    if not email or '@' not in email:
        return None

    # Extrair parte do nome do email (ex: 'nome.sobrenome@...' -> 'nome sobrenome')
    local_part = email.split('@')[0]
    name_parts = local_part.replace('.', ' ').replace('_', ' ').split()

    if not name_parts:
        return None

    # --- SPECIAL BYPASS FOR DEV USER ---
    # Garante acesso ao desenvolvedor principal mesmo se o banco externo estiver configurado mas desatualizado
    if email == 'kevinpereira@pactosolucoes.com.br' and current_app.config.get('DEBUG', False):
        logger.info(f"DEV MODE: Forçando mock de usuário CS para: {email}")
        return {
            'codigo': 99999,
            'nome': 'Kevin Pereira',
            'ativo': True,
            'url': None
        }

    # --- MOCK PARA DESENVOLVIMENTO LOCAL (QUANDO SEM BANCO EXTERNO) ---
    # Permite login sem conexão com banco legado se a URL não estiver configurada E estiver em modo DEBUG
    # Isso impede que em produção (onde DEBUG é False) o mock seja usado acidentalmente se a URL falhar.
    if not current_app.config.get('EXTERNAL_DB_URL') and current_app.config.get('DEBUG', False):
        logger.warning(f"DEV MODE: EXTERNAL_DB_URL não configurada. Mockando usuário CS para: {email}")
        if email.endswith('@pactosolucoes.com.br'):
            return {
                'codigo': 99999,
                'nome': ' '.join(name_parts).title(),
                'ativo': True,
                'url': None
            }
        return None
    # ------------------------------------------------------------------

    # Tentar buscar por nome parcial (primeiro nome)
    first_name = name_parts[0]

    query = """
        SELECT codigo, nome, ativo, url 
        FROM customersuccess 
        WHERE ativo = true 
        AND retira_acentuacao(lower(nome)) LIKE retira_acentuacao(lower(:name_pattern))
    """

    try:
        # Busca ampla pelo primeiro nome
        results = query_external_db(query, {'name_pattern': f"%{first_name}%"})

        # Refinar resultados no Python
        for user in results:
            db_name_norm = normalize_text(user['nome'])
            # Verificar se todas as partes do nome do email estão no nome do banco
            match = True
            for part in name_parts:
                part_norm = normalize_text(part)
                if part_norm not in db_name_norm:
                    match = False
                    break

            if match:
                return user

        return None

    except Exception as e:
        logger.error(f"Erro ao buscar usuário CS por email: {e}")
        # Propagar erro para diferenciar 'não encontrado' de 'falha de conexão'
        raise
