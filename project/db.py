import sqlite3
import psycopg2
import psycopg2.extras
import click
from flask import current_app, g
from .constants import (
    CHECKLIST_OBRIGATORIO_ITEMS, MODULO_OBRIGATORIO, 
    TAREFAS_TREINAMENTO_PADRAO
)

# --- Camada de Acesso a Dados (DAO) ---

def get_db():
    """Conecta ao banco de dados, usando 'g' para cachear a conexão por request."""
    if 'db' not in g:
        if not current_app.config['USE_SQLITE_LOCALLY'] and current_app.config['DATABASE_URL']:
            g.db = psycopg2.connect(current_app.config['DATABASE_URL'])
            print("Conectado ao PostgreSQL.")
        elif current_app.config['USE_SQLITE_LOCALLY']:
            g.db = sqlite3.connect(
                current_app.config['LOCAL_SQLITE_DB'],
                detect_types=sqlite3.PARSE_DECLTYPES
            )
            g.db.row_factory = sqlite3.Row
            print(f"Conectado ao SQLite local: {current_app.config['LOCAL_SQLITE_DB']}")
        else:
            raise Exception("Configuração de banco de dados inválida.")
    return g.db

def close_connection(exception=None):
    """Fecha a conexão com o banco de dados no final do request."""
    db = g.pop('db', None)
    if db is not None:
        db.close()

def _db_query(query, args=(), one=False):
    db = get_db()
    cur = None
    try:
        is_postgres = isinstance(db, psycopg2.extensions.connection)
        if is_postgres:
            cur = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        else:
            query = query.replace('%s', '?')
            cur = db.cursor()
        
        cur.execute(query, args)
        rv = cur.fetchall()
        cur.close()
        
        if not is_postgres:
            rv = [dict(row) for row in rv] # Converte Row do SQLite para dict
            
        return (rv[0] if rv else None) if one else rv
    except Exception as e:
        print(f"ERRO ao executar SELECT: {e}\nQuery SQL: {query}\nArgumentos: {args}")
        if cur: cur.close()
        raise e

def _db_execute(command, args=()):
    db = get_db()
    cur = None
    returned_id = None
    try:
        is_postgres = isinstance(db, psycopg2.extensions.connection)
        if not is_postgres:
            command = command.replace('%s', '?')
        
        cur = db.cursor()
        
        if is_postgres:
            command_upper = command.strip().upper()
            # Verifica se é um INSERT que precisa de ID de retorno
            needs_returning_id = command_upper.startswith("INSERT") and \
                                 any(tbl in command_upper for tbl in ["INTO IMPLANTACOES", "INTO TAREFAS", "INTO COMENTARIOS", "INTO TIMELINE_LOG"])
            
            if needs_returning_id and "RETURNING" not in command_upper:
                command += " RETURNING id"
                cur.execute(command, args)
                returned_id = cur.fetchone()[0] if cur.rowcount > 0 else None
            else:
                cur.execute(command, args)
        else:
            cur.execute(command, args)
            returned_id = cur.lastrowid # Pega o ID no SQLite

        db.commit()
        cur.close()
        return returned_id
    except Exception as e:
        print(f"ERRO ao executar comando: {e}\nComando SQL: {command}\nArgumentos: {args}")
        if db: db.rollback()
        if cur: cur.close()
        raise e

def logar_timeline(implantacao_id, usuario_cs, tipo_evento, detalhes):
    """Registra um evento na timeline de uma implantação (Movida para cá)."""
    try:
        _db_execute(
            "INSERT INTO timeline_log (implantacao_id, usuario_cs, tipo_evento, detalhes) VALUES (%s, %s, %s, %s)",
            (implantacao_id, usuario_cs, tipo_evento, detalhes)
        )
    except Exception as e:
        print(f"AVISO/ERRO: Falha ao logar evento '{tipo_evento}' para implantação {implantacao_id}: {e}")


def query_db(query, args=(), one=False):
    """Helper para SELECTs."""
    return _db_query(query, args, one)

def execute_db(command, args=()):
    """Helper para INSERT, UPDATE, DELETE."""
    return _db_execute(command, args)

# --- Setup do DB ---

def init_db():
    """Função para criar as tabelas do banco de dados."""
    db = get_db()
    cur = db.cursor()
    is_postgres = isinstance(db, psycopg2.extensions.connection)
    
    # Define tipos de dados baseados no SGBD
    pk_type = "SERIAL PRIMARY KEY" if is_postgres else "INTEGER PRIMARY KEY AUTOINCREMENT"
    boolean_type = "BOOLEAN" if is_postgres else "INTEGER"
    timestamp_type = "TIMESTAMP WITH TIME ZONE" if is_postgres else "DATETIME"
    date_type = "DATE" if is_postgres else "TEXT"

    # Criação das tabelas
    cur.execute(f"CREATE TABLE IF NOT EXISTS usuarios (usuario VARCHAR(255) PRIMARY KEY, senha TEXT NOT NULL)")
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS perfil_usuario (
            usuario VARCHAR(255) PRIMARY KEY REFERENCES usuarios(usuario) ON DELETE CASCADE,
            nome TEXT,
            cargo TEXT,
            perfil_acesso VARCHAR(100) DEFAULT NULL,
            foto_url TEXT,
            impl_andamento INTEGER DEFAULT 0,
            impl_finalizadas INTEGER DEFAULT 0,
            impl_paradas INTEGER DEFAULT 0,
            progresso_medio_carteira INTEGER DEFAULT 0,
            impl_andamento_total INTEGER DEFAULT 0,
            implantacoes_atrasadas INTEGER DEFAULT 0,
            data_criacao {timestamp_type} DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Adiciona a nova coluna caso o DB já exista, mas sem o campo
    try:
        cur.execute("SELECT perfil_acesso FROM perfil_usuario LIMIT 1")
    except Exception:
        print("Adicionando coluna 'perfil_acesso' à tabela 'perfil_usuario'...")
        cur.execute(f"ALTER TABLE perfil_usuario ADD COLUMN perfil_acesso VARCHAR(100) DEFAULT NULL")

    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS implantacoes (
            id {pk_type},
            usuario_cs VARCHAR(255) NOT NULL REFERENCES usuarios(usuario) ON DELETE NO ACTION,
            nome_empresa TEXT NOT NULL,
            status VARCHAR(50) DEFAULT 'andamento' CHECK(status IN ('andamento', 'futura', 'finalizada', 'parada')),
            tipo VARCHAR(50) DEFAULT 'agora' CHECK(tipo IN ('agora', 'futura')),
            data_criacao {timestamp_type} DEFAULT CURRENT_TIMESTAMP,
            data_finalizacao {timestamp_type},
            motivo_parada TEXT DEFAULT '',
            responsavel_cliente TEXT DEFAULT '',
            cargo_responsavel TEXT DEFAULT '',
            telefone_responsavel VARCHAR(50) DEFAULT '',
            email_responsavel VARCHAR(255) DEFAULT '',
            data_inicio_producao {date_type} DEFAULT NULL,
            data_final_implantacao {date_type} DEFAULT NULL,
            chave_oamd TEXT DEFAULT '',
            catraca TEXT DEFAULT '',
            facial TEXT DEFAULT ''
        )
    """)
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS tarefas (
            id {pk_type},
            implantacao_id INTEGER NOT NULL REFERENCES implantacoes(id) ON DELETE CASCADE,
            tarefa_pai TEXT NOT NULL,
            tarefa_filho TEXT NOT NULL,
            concluida {boolean_type} DEFAULT FALSE,
            ordem INTEGER DEFAULT 0,
            tag VARCHAR(100) DEFAULT '',
            data_conclusao {timestamp_type} DEFAULT NULL -- NOVO CAMPO
        )
    """)
    
    # Adiciona a nova coluna caso a tabela já exista sem ela
    try:
        cur.execute("SELECT data_conclusao FROM tarefas LIMIT 1")
    except Exception:
        print("Adicionando coluna 'data_conclusao' à tabela 'tarefas'...")
        cur.execute(f"ALTER TABLE tarefas ADD COLUMN data_conclusao {timestamp_type} DEFAULT NULL")
    
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS comentarios (
            id {pk_type},
            tarefa_id INTEGER NOT NULL REFERENCES tarefas(id) ON DELETE CASCADE,
            usuario_cs VARCHAR(255) NOT NULL REFERENCES usuarios(usuario) ON DELETE NO ACTION,
            texto TEXT NOT NULL,
            data_criacao {timestamp_type} DEFAULT CURRENT_TIMESTAMP,
            imagem_url TEXT DEFAULT NULL
        )
    """)
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS timeline_log (
            id {pk_type},
            implantacao_id INTEGER NOT NULL REFERENCES implantacoes(id) ON DELETE CASCADE,
            usuario_cs VARCHAR(255) NOT NULL REFERENCES usuarios(usuario) ON DELETE NO ACTION,
            tipo_evento VARCHAR(100) NOT NULL,
            detalhes TEXT NOT NULL,
            data_criacao {timestamp_type} DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Índices
    cur.execute("CREATE INDEX IF NOT EXISTS idx_tarefas_implantacao_id ON tarefas (implantacao_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_comentarios_tarefa_id ON comentarios (tarefa_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_timeline_log_implantacao_id ON timeline_log (implantacao_id)")
    
    db.commit()
    cur.close()
    print("Schema DB verificado/inicializado.")

@click.command('init-db')
def init_db_command():
    """Comando do Flask para inicializar o banco de dados."""
    init_db()
    click.echo('Banco de dados inicializado.')

def init_app(app):
    """Registra as funções do DB com a instância da app Flask."""
    app.teardown_appcontext(close_connection)
    app.cli.add_command(init_db_command)