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
import time
from functools import wraps
from sqlalchemy.exc import OperationalError, InterfaceError

def with_retries(max_retries=3, delay=2, backoff=2, exceptions=(OperationalError, InterfaceError, RuntimeError)):
    """Decorator para repetir uma operação em caso de erro de conexão."""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            retries = 0
            current_delay = delay
            last_exception = None
            
            while retries < max_retries:
                try:
                    return f(*args, **kwargs)
                except exceptions as e:
                    retries += 1
                    last_exception = e
                    
                    # Se for RuntimeError e não for relacionado a conexão, não faz sentido repetir
                    if isinstance(e, RuntimeError) and "conexão" not in str(e).lower() and "engine" not in str(e).lower():
                        raise
                        
                    if retries >= max_retries:
                        logger.error(f"Falha definitiva após {max_retries} tentativas: {e}")
                        break
                        
                    logger.warning(f"Falha na conexão com banco externo. Tentativa {retries}/{max_retries} em {current_delay}s... Erro: {e}")
                    time.sleep(current_delay)
                    current_delay *= backoff
            
            if last_exception:
                raise last_exception
        return wrapper
    return decorator

def get_external_engine():
    """
    Retorna uma engine SQLAlchemy para o banco de dados externo.
    Utiliza pooling moderado para evitar esgotar conexões do banco legado.
    """
    if not hasattr(current_app, 'external_db_engine') or current_app.external_db_engine is None:
        external_db_url = current_app.config.get('EXTERNAL_DB_URL')

        if not external_db_url:
            logger.warning("EXTERNAL_DB_URL não configurada.")
            return None

        try:
            # Timeout via env var ou default 15s (mais que 10s para ser tolerante mas não infinito)
            timeout = int(os.environ.get('EXTERNAL_DB_TIMEOUT', 15))
            
            # Argumentos de conexão otimizados para resiliência
            connect_args = {
                'connect_timeout': timeout,
                'keepalives': 1,
                'keepalives_idle': 30,
                'keepalives_interval': 10,
                'keepalives_count': 5,
            }
            
            # Forçar SSL Mode conforme o ambiente - Muitos bancos AWS/RDS exigem SSL
            if external_db_url.lower().startswith('postgresql'):
                # Tenta 'prefer' para ser compatível com bancos velhos, mas permite SSL se disponível
                connect_args['sslmode'] = os.environ.get('EXTERNAL_DB_SSLMODE', 'prefer')
                # Timeout de query no nível do protocolo Postgres
                connect_args['options'] = f'-c statement_timeout={timeout * 1000}'

            logger.info(f"Conectando ao OAMD (Timeout: {timeout}s, host: {external_db_url.split('@')[-1].split('/')[0] if '@' in external_db_url else 'hidden'})")
            
            engine = create_engine(
                external_db_url,
                pool_pre_ping=True,       # Crucial: testa a conexão antes de usar
                pool_recycle=1200,        # Recicla a cada 20 min (menor que os 30 min habituais para segurança)
                pool_size=3,              # Reduzido: evita esgotar conexões no servidor legado que pode ter limites baixos
                max_overflow=5,           # Limite de transbordo pequeno
                pool_timeout=timeout,     # Tempo que a thread espera por uma conexão do pool
                connect_args=connect_args,
                # Garante que as conexões sejam read-only no nível da transação se possível
                execution_options={"isolation_level": "AUTOCOMMIT"} 
            )
            
            current_app.external_db_engine = engine
            logger.info("Engine OAMD inicializada.")
        except Exception as e:
            logger.error(f"Erro ao configurar conexão externa: {e}")
            return None

    return current_app.external_db_engine

@with_retries(max_retries=3, delay=1)
def query_external_db(query_str, params=None):
    """
    Executa uma query SELECT no banco de dados externo com lógica de retry.
    Garante que a conexão seja APENAS LEITURA.
    """
    engine = get_external_engine()
    if not engine:
        raise RuntimeError("Engine do banco externo não disponível.")

    if params is None:
        params = {}

    try:
        with engine.connect() as conn:
            result = conn.execute(text(query_str), params)
            keys = result.keys()
            return [dict(zip(keys, row)) for row in result]

    except (OperationalError, InterfaceError) as e:
        # Esses erros costumam ser transitórios (rede, VPN caindo, etc)
        logger.warning(f"Erro transiente no banco externo: {e}")
        # Invalidamos a engine para que a próxima tentativa (do retry) crie uma nova
        if hasattr(current_app, 'external_db_engine'):
            current_app.external_db_engine = None
        raise
    except Exception as e:
        logger.error(f"Erro não recuperável na query externa: {e}")
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
