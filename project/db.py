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
            try:
                g.db = psycopg2.connect(current_app.config['DATABASE_URL'])
                print("Conectado ao PostgreSQL.")
            except psycopg2.Error as e:
                print(f"ERRO CRÍTICO ao conectar ao PostgreSQL: {e}")
                raise e # Re-lança para parar a app se o DB não estiver disponível
        elif current_app.config['USE_SQLITE_LOCALLY']:
            try:
                g.db = sqlite3.connect(
                    current_app.config['LOCAL_SQLITE_DB'],
                    detect_types=sqlite3.PARSE_DECLTYPES
                )
                g.db.row_factory = sqlite3.Row
                print(f"Conectado ao SQLite local: {current_app.config['LOCAL_SQLITE_DB']}")
            except sqlite3.Error as e:
                print(f"ERRO CRÍTICO ao conectar ao SQLite local: {e}")
                raise e # Re-lança
        else:
            raise Exception("Configuração de banco de dados inválida. Verifique DATABASE_URL ou USE_SQLITE_LOCALLY.")
    return g.db

def close_connection(exception=None):
    """Fecha a conexão com o banco de dados no final do request."""
    db = g.pop('db', None)
    if db is not None:
        try:
            db.close()
        except Exception as e:
            print(f"AVISO: Erro ao fechar conexão com DB: {e}")


def _db_query(query, args=(), one=False):
    db = get_db()
    cur = None
    try:
        is_postgres = isinstance(db, psycopg2.extensions.connection)
        if is_postgres:
            cur = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        else: # SQLite
            query = query.replace('%s', '?')
            # Garante que args seja uma tupla
            args = tuple(args) if isinstance(args, list) else args
            cur = db.cursor()

        cur.execute(query, args)
        # Fetchall retorna lista vazia se não houver resultados
        rv = cur.fetchall()

        if not is_postgres:
            # Converte Row do SQLite para dict
            # rv será uma lista de sqlite3.Row ou lista vazia
            rv = [dict(row) for row in rv]

        # Fecha o cursor ANTES de retornar
        cur.close()
        cur = None # Garante que não será fechado novamente no finally

        return (rv[0] if rv else None) if one else rv
    except Exception as e:
        print(f"ERRO ao executar SELECT: {e}\nQuery SQL: {query}\nArgumentos: {args}")
        # Tenta fechar o cursor se ainda estiver aberto
        if cur:
            try: cur.close()
            except: pass
        # Re-lança a exceção para ser tratada em camadas superiores
        raise e


def _db_execute(command, args=()):
    db = get_db()
    cur = None
    returned_id = None
    try:
        is_postgres = isinstance(db, psycopg2.extensions.connection)
        if not is_postgres:
            command = command.replace('%s', '?')
            # Garante que args seja uma tupla
            args = tuple(args) if isinstance(args, list) else args

        cur = db.cursor()

        if is_postgres:
            command_upper = command.strip().upper()
            needs_returning_id = command_upper.startswith("INSERT") and \
                                 any(tbl in command_upper for tbl in ["INTO IMPLANTACOES", "INTO TAREFAS", "INTO COMENTARIOS", "INTO TIMELINE_LOG", "INTO GAMIFICACAO_METRICAS_MENSAIS", "INTO USUARIOS", "INTO PERFIL_USUARIO"])

            if needs_returning_id and "RETURNING" not in command_upper:
                command += " RETURNING id" # Assumindo que a PK é 'id'
                cur.execute(command, args)
                # Pega o ID retornado se a inserção foi bem-sucedida
                returned_id_tuple = cur.fetchone()
                returned_id = returned_id_tuple[0] if returned_id_tuple else None
            else:
                cur.execute(command, args)
                # Se for UPDATE/DELETE, não tentamos pegar ID via fetchone
                returned_id = cur.rowcount # Pode retornar o número de linhas afetadas
        else: # SQLite
            cur.execute(command, args)
            if command.strip().upper().startswith("INSERT"):
                returned_id = cur.lastrowid # Pega o ID no SQLite para INSERT
            else:
                returned_id = cur.rowcount # Retorna linhas afetadas para UPDATE/DELETE

        db.commit()
        # Fecha o cursor ANTES de retornar
        cur.close()
        cur = None
        return returned_id
    except Exception as e:
        print(f"ERRO ao executar comando: {e}\nComando SQL: {command}\nArgumentos: {args}")
        if db:
            try: db.rollback()
            except: pass
        if cur:
            try: cur.close()
            except: pass
        raise e


def logar_timeline(implantacao_id, usuario_cs, tipo_evento, detalhes):
    """Registra um evento na timeline de uma implantação."""
    try:
        execute_db(
            "INSERT INTO timeline_log (implantacao_id, usuario_cs, tipo_evento, detalhes) VALUES (%s, %s, %s, %s)",
            (implantacao_id, usuario_cs, tipo_evento, detalhes)
        )
    except Exception as e:
        # Log mais detalhado do erro
        print(f"AVISO/ERRO: Falha ao logar evento '{tipo_evento}' para implantação {implantacao_id}. Usuário: {usuario_cs}. Detalhes erro: {e}")


def query_db(query, args=(), one=False):
    """Helper para SELECTs."""
    return _db_query(query, args, one)

def execute_db(command, args=()):
    """Helper para INSERT, UPDATE, DELETE."""
    return _db_execute(command, args)

# --- Setup do DB ---

# Helper para verificar e adicionar colunas (importante para migrações)
def check_and_add_column(cursor, table, column, definition, db_connection):
    try:
        # Tenta selecionar a coluna. LIMIT 1 é mais eficiente que LIMIT 0 em alguns DBs.
        cursor.execute(f"SELECT {column} FROM {table} LIMIT 1")
        # print(f"Coluna '{column}' já existe na tabela '{table}'.") # Comentado
        return False # Coluna já existe
    except (psycopg2.errors.UndefinedColumn, sqlite3.OperationalError): # Erros esperados
         # Desfaz SELECT falho (importante no PostgreSQL dentro de uma transação)
         try: db_connection.rollback()
         except: pass # Ignora erro se rollback falhar ou não for necessário
         print(f"Adicionando coluna '{column}' à tabela '{table}'...")
         try:
             # Executa ALTER TABLE fora da transação principal inicial se necessário
             # No SQLite, ALTER TABLE ADD COLUMN geralmente não precisa de commit separado se o autocommit estiver off
             # No PostgreSQL, faz parte da transação
             cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
             # Commit explícito após ALTER TABLE para garantir persistência, especialmente em PostgreSQL
             db_connection.commit()
             print(f"Coluna '{column}' adicionada com sucesso.")
             return True # Coluna adicionada
         except Exception as alter_err:
             print(f"ERRO CRÍTICO ao adicionar coluna '{column}' à tabela '{table}': {alter_err}")
             # Tenta rollback novamente
             try: db_connection.rollback()
             except: pass
             raise alter_err # Re-lança o erro
    except Exception as e:
        print(f"ERRO INESPERADO ao verificar coluna '{column}' na tabela '{table}': {e}")
        try: db_connection.rollback()
        except: pass
        raise e

def init_db():
    """Função para criar as tabelas do banco de dados e adicionar colunas faltantes."""
    db = get_db()
    cur = db.cursor()
    is_postgres = isinstance(db, psycopg2.extensions.connection)

    # Define tipos de dados baseados no SGBD
    pk_type = "SERIAL PRIMARY KEY" if is_postgres else "INTEGER PRIMARY KEY AUTOINCREMENT"
    boolean_type = "BOOLEAN" if is_postgres else "INTEGER" # SQLite usa 0/1
    timestamp_type = "TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP" if is_postgres else "DATETIME DEFAULT CURRENT_TIMESTAMP"
    timestamp_nullable_type = "TIMESTAMP WITH TIME ZONE" if is_postgres else "DATETIME" # Sem default
    date_type = "DATE" if is_postgres else "TEXT" # SQLite armazena datas como TEXT (ISO)
    text_type = "TEXT"
    integer_type = "INTEGER"
    real_type = "REAL" # Adequado para ambos

    print("Inicializando/Verificando schema do banco de dados...")

    # Tabela usuarios
    cur.execute(f"CREATE TABLE IF NOT EXISTS usuarios (usuario VARCHAR(255) PRIMARY KEY, senha TEXT NOT NULL)")
    print("- Tabela 'usuarios' verificada/criada.")

    # Tabela perfil_usuario
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS perfil_usuario (
            usuario VARCHAR(255) PRIMARY KEY REFERENCES usuarios(usuario) ON DELETE CASCADE,
            nome TEXT,
            cargo TEXT,
            perfil_acesso VARCHAR(100) DEFAULT NULL,
            foto_url TEXT,
            impl_andamento {integer_type} DEFAULT 0,
            impl_finalizadas {integer_type} DEFAULT 0,
            impl_paradas {integer_type} DEFAULT 0,
            progresso_medio_carteira {integer_type} DEFAULT 0,
            impl_andamento_total {integer_type} DEFAULT 0,
            implantacoes_atrasadas {integer_type} DEFAULT 0,
            data_criacao {timestamp_type}
        )
    """)
    print("- Tabela 'perfil_usuario' verificada/criada.")
    # Adiciona colunas faltantes a perfil_usuario (exemplo - ajuste conforme necessário)
    check_and_add_column(cur, 'perfil_usuario', 'perfil_acesso', 'VARCHAR(100) DEFAULT NULL', db)

    # Tabela implantacoes
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS implantacoes (
            id {pk_type},
            usuario_cs VARCHAR(255) REFERENCES usuarios(usuario) ON DELETE SET NULL,
            nome_empresa TEXT NOT NULL,
            status VARCHAR(50) DEFAULT 'andamento' CHECK(status IN ('andamento', 'futura', 'finalizada', 'parada')),
            tipo VARCHAR(50) DEFAULT 'agora' CHECK(tipo IN ('agora', 'futura', 'modulo')),
            data_criacao {timestamp_type}, -- Data de criação do registro
            data_inicio_efetivo {timestamp_nullable_type} DEFAULT NULL, -- Data que iniciou de fato
            data_finalizacao {timestamp_nullable_type} DEFAULT NULL,
            data_inicio_previsto {date_type} DEFAULT NULL,
            motivo_parada TEXT DEFAULT NULL,
            responsavel_cliente TEXT DEFAULT NULL,
            cargo_responsavel TEXT DEFAULT NULL,
            telefone_responsavel VARCHAR(50) DEFAULT NULL,
            email_responsavel VARCHAR(255) DEFAULT NULL,
            data_inicio_producao {date_type} DEFAULT NULL,
            data_final_implantacao {date_type} DEFAULT NULL,
            chave_oamd TEXT DEFAULT NULL,
            catraca VARCHAR(20) DEFAULT 'Não definido',
            facial VARCHAR(20) DEFAULT 'Não definido',
            nivel_receita VARCHAR(100) DEFAULT NULL,
            valor_atribuido VARCHAR(100) DEFAULT NULL,
            id_favorecido VARCHAR(50) DEFAULT NULL,
            tela_apoio_link TEXT DEFAULT NULL,
            seguimento VARCHAR(100) DEFAULT NULL,
            tipos_planos VARCHAR(100) DEFAULT NULL,
            modalidades VARCHAR(100) DEFAULT NULL,
            horarios_func VARCHAR(100) DEFAULT NULL,
            formas_pagamento VARCHAR(100) DEFAULT NULL,
            diaria VARCHAR(20) DEFAULT 'Não definido',
            freepass VARCHAR(20) DEFAULT 'Não definido',
            alunos_ativos {integer_type} DEFAULT 0,
            sistema_anterior VARCHAR(100) DEFAULT NULL,
            importacao VARCHAR(20) DEFAULT 'Não definido',
            recorrencia_usa VARCHAR(100) DEFAULT NULL,
            boleto VARCHAR(20) DEFAULT 'Não definido',
            nota_fiscal VARCHAR(20) DEFAULT 'Não definido',
            resp_estrategico_nome VARCHAR(255) DEFAULT NULL,
            resp_onb_nome VARCHAR(255) DEFAULT NULL,
            resp_estrategico_obs TEXT DEFAULT NULL,
            contatos TEXT DEFAULT NULL
        )
    """)
    print("- Tabela 'implantacoes' verificada/criada.")
    # Adiciona colunas faltantes a implantacoes (exemplos - liste todas as novas se necessário)
    impl_cols_to_check = {
        'data_inicio_efetivo': f'{timestamp_nullable_type} DEFAULT NULL', # COLUNA ADICIONADA
        'data_inicio_previsto': f'{date_type} DEFAULT NULL',
        'nivel_receita': 'VARCHAR(100) DEFAULT NULL', 'valor_atribuido': 'VARCHAR(100) DEFAULT NULL',
        'id_favorecido': 'VARCHAR(50) DEFAULT NULL', 'tela_apoio_link': f'{text_type} DEFAULT NULL',
        'seguimento': 'VARCHAR(100) DEFAULT NULL', 'tipos_planos': 'VARCHAR(100) DEFAULT NULL',
        'modalidades': 'VARCHAR(100) DEFAULT NULL', 'horarios_func': 'VARCHAR(100) DEFAULT NULL',
        'formas_pagamento': 'VARCHAR(100) DEFAULT NULL', 'diaria': 'VARCHAR(20) DEFAULT \'Não definido\'',
        'freepass': 'VARCHAR(20) DEFAULT \'Não definido\'', 'alunos_ativos': f'{integer_type} DEFAULT 0',
        'sistema_anterior': 'VARCHAR(100) DEFAULT NULL', 'importacao': 'VARCHAR(20) DEFAULT \'Não definido\'',
        'recorrencia_usa': 'VARCHAR(100) DEFAULT NULL', 'boleto': 'VARCHAR(20) DEFAULT \'Não definido\'',
        'nota_fiscal': 'VARCHAR(20) DEFAULT \'Não definido\'', 'resp_estrategico_nome': 'VARCHAR(255) DEFAULT NULL',
        'resp_onb_nome': 'VARCHAR(255) DEFAULT NULL', 'resp_estrategico_obs': f'{text_type} DEFAULT NULL',
        'contatos': f'{text_type} DEFAULT NULL', 'catraca': 'VARCHAR(20) DEFAULT \'Não definido\'',
        'facial': 'VARCHAR(20) DEFAULT \'Não definido\''
    }
    for col, definition in impl_cols_to_check.items():
        check_and_add_column(cur, 'implantacoes', col, definition, db)

    # Tabela tarefas
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS tarefas (
            id {pk_type},
            implantacao_id INTEGER NOT NULL REFERENCES implantacoes(id) ON DELETE CASCADE,
            tarefa_pai TEXT NOT NULL,
            tarefa_filho TEXT NOT NULL,
            concluida {boolean_type} DEFAULT 0, -- SQLite usa 0/1
            ordem {integer_type} DEFAULT 0,
            tag VARCHAR(100) DEFAULT NULL,
            data_conclusao {timestamp_nullable_type} DEFAULT NULL
        )
    """)
    print("- Tabela 'tarefas' verificada/criada.")
    check_and_add_column(cur, 'tarefas', 'data_conclusao', f'{timestamp_nullable_type} DEFAULT NULL', db)
    check_and_add_column(cur, 'tarefas', 'tag', 'VARCHAR(100) DEFAULT NULL', db) # Garante tag

    # Tabela comentarios
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS comentarios (
            id {pk_type},
            tarefa_id INTEGER NOT NULL REFERENCES tarefas(id) ON DELETE CASCADE,
            usuario_cs VARCHAR(255) REFERENCES usuarios(usuario) ON DELETE SET NULL,
            texto TEXT NOT NULL,
            data_criacao {timestamp_type},
            imagem_url TEXT DEFAULT NULL
        )
    """)
    print("- Tabela 'comentarios' verificada/criada.")
    check_and_add_column(cur, 'comentarios', 'imagem_url', f'{text_type} DEFAULT NULL', db)

    # Tabela timeline_log
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS timeline_log (
            id {pk_type},
            implantacao_id INTEGER NOT NULL REFERENCES implantacoes(id) ON DELETE CASCADE,
            usuario_cs VARCHAR(255) REFERENCES usuarios(usuario) ON DELETE SET NULL,
            tipo_evento VARCHAR(100) NOT NULL,
            detalhes TEXT NOT NULL,
            data_criacao {timestamp_type}
        )
    """)
    print("- Tabela 'timeline_log' verificada/criada.")

    # --- TABELA PARA GAMIFICAÇÃO ---
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS gamificacao_metricas_mensais (
            id {pk_type},
            usuario_cs VARCHAR(255) NOT NULL REFERENCES usuarios(usuario) ON DELETE CASCADE,
            mes {integer_type} NOT NULL CHECK (mes >= 1 AND mes <= 12),
            ano {integer_type} NOT NULL,
            -- Métricas Manuais (podem ser NULL se não preenchidas)
            nota_qualidade {integer_type} DEFAULT NULL CHECK (nota_qualidade IS NULL OR (nota_qualidade >= 0 AND nota_qualidade <= 100)),
            assiduidade {integer_type} DEFAULT NULL CHECK (assiduidade IS NULL OR (assiduidade >= 0 AND assiduidade <= 100)),
            planos_sucesso_perc {integer_type} DEFAULT NULL CHECK (planos_sucesso_perc IS NULL OR (planos_sucesso_perc >= 0 AND planos_sucesso_perc <= 100)),
            satisfacao_processo {integer_type} DEFAULT NULL CHECK (satisfacao_processo IS NULL OR (satisfacao_processo >= 0 AND satisfacao_processo <= 100)),
            reclamacoes {integer_type} DEFAULT 0 CHECK(reclamacoes >= 0),
            perda_prazo {integer_type} DEFAULT 0 CHECK(perda_prazo >= 0),
            nao_preenchimento {integer_type} DEFAULT 0 CHECK(nao_preenchimento >= 0),
            elogios {integer_type} DEFAULT 0 CHECK(elogios >= 0),
            recomendacoes {integer_type} DEFAULT 0 CHECK(recomendacoes >= 0),
            certificacoes {integer_type} DEFAULT 0 CHECK(certificacoes >= 0),
            treinamentos_pacto_part {integer_type} DEFAULT 0 CHECK(treinamentos_pacto_part >= 0),
            treinamentos_pacto_aplic {integer_type} DEFAULT 0 CHECK(treinamentos_pacto_aplic >= 0),
            reunioes_presenciais {integer_type} DEFAULT 0 CHECK(reunioes_presenciais >= 0),
            cancelamentos_resp {integer_type} DEFAULT 0 CHECK(cancelamentos_resp >= 0),
            nao_envolvimento {integer_type} DEFAULT 0 CHECK(nao_envolvimento >= 0),
            desc_incompreensivel {integer_type} DEFAULT 0 CHECK(desc_incompreensivel >= 0),
            hora_extra {integer_type} DEFAULT 0 CHECK(hora_extra >= 0),
            perda_sla_grupo {integer_type} DEFAULT 0 CHECK(perda_sla_grupo >= 0),
            finalizacao_incompleta {integer_type} DEFAULT 0 CHECK(finalizacao_incompleta >= 0),
            -- Métricas Calculadas (armazenadas opcionalmente)
            impl_finalizadas_mes {integer_type} DEFAULT NULL,
            tma_medio_mes {real_type} DEFAULT NULL,
            impl_iniciadas_mes {integer_type} DEFAULT NULL,
            reunioes_concluidas_dia_media {real_type} DEFAULT NULL,
            acoes_concluidas_dia_media {real_type} DEFAULT NULL,
            -- Pontuação e Status
            pontuacao_calculada {integer_type} DEFAULT NULL,
            elegivel {boolean_type} DEFAULT NULL,
            -- Controle
            data_registro {timestamp_type}, -- Atualizado sempre
            registrado_por VARCHAR(255) REFERENCES usuarios(usuario) ON DELETE SET NULL,
            UNIQUE (usuario_cs, mes, ano) -- Garante uma entrada por usuário/mês/ano
        )
    """)
    print("- Tabela 'gamificacao_metricas_mensais' verificada/criada.")
    gamif_cols_to_check = {
        'perda_sla_grupo': f'{integer_type} DEFAULT 0 CHECK(perda_sla_grupo >= 0)',
        'finalizacao_incompleta': f'{integer_type} DEFAULT 0 CHECK(finalizacao_incompleta >= 0)'
    }
    for col, definition in gamif_cols_to_check.items():
         check_and_add_column(cur, 'gamificacao_metricas_mensais', col, definition, db)

    # Índices (Criar se não existirem)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_impl_usuario_cs ON implantacoes (usuario_cs)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_impl_status ON implantacoes (status)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_tarefas_implantacao_id ON tarefas (implantacao_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_tarefas_pai_ordem ON tarefas (tarefa_pai, ordem)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_comentarios_tarefa_id ON comentarios (tarefa_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_timeline_log_implantacao_id ON timeline_log (implantacao_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_timeline_data ON timeline_log (data_criacao DESC)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_gamificacao_user_period ON gamificacao_metricas_mensais (usuario_cs, ano, mes)")
    print("- Índices verificados/criados.")

    db.commit() # Commit final para garantir tudo
    cur.close()
    print("Schema DB verificado/inicializado com sucesso.")


@click.command('init-db')
def init_db_command():
    """Comando do Flask para inicializar o banco de dados."""
    try:
        init_db()
        click.echo('Banco de dados inicializado com sucesso.')
    except Exception as e:
        click.echo(f'Erro ao inicializar o banco de dados: {e}', err=True)


def init_app(app):
    """Registra as funções do DB com a instância da app Flask."""
    app.teardown_appcontext(close_connection)
    app.cli.add_command(init_db_command)