import click
import sqlite3
import psycopg2
import psycopg2.extras
import re # Importa regex
from flask import current_app, g
from datetime import datetime

# --- Conexão ---

def get_db():
    """Retorna uma conexão com o banco de dados (PostgreSQL ou SQLite)."""
    if 'db' not in g:
        if current_app.config.get('USE_SQLITE_LOCALLY', False):
            db_path = current_app.config['LOCAL_SQLITE_DB']
            g.db = sqlite3.connect(db_path)
            g.db.row_factory = sqlite3.Row # Retorna dicts em vez de tuplas
            print(f"Conectado ao SQLite: {db_path}")
        else:
            try:
                g.db = psycopg2.connect(
                    current_app.config['DATABASE_URL'],
                    cursor_factory=psycopg2.extras.DictCursor # Retorna dicts
                )
                print("Conectado ao PostgreSQL.")
            except psycopg2.OperationalError as e:
                print(f"ERRO: Falha ao conectar ao PostgreSQL. Verifique DATABASE_URL. Erro: {e}")
                raise
        g.is_sqlite = current_app.config.get('USE_SQLITE_LOCALLY', False)
    return g.db

def close_connection(e=None):
    """Fecha a conexão com o banco de dados."""
    db = g.pop('db', None)
    if db is not None:
        db.close()
        g.pop('is_sqlite', None)
        # print("Conexão com o DB fechada.")

# --- Funções de Execução (Query/Execute) ---

def _adapt_query_args(query, args):
    """Adapta os placeholders da query (%s) para o formato do SQLite (?)."""
    if g.get('is_sqlite', False):
        # Substitui %s por ? (exceto se for %%s)
        query = re.sub(r'(?<!%)%s', '?', query)
    return query, args

def query_db(query, args=(), one=False):
    """Executa uma consulta SELECT."""
    db = get_db()
    cursor = db.cursor()
    adapted_query, adapted_args = _adapt_query_args(query, args)
    
    try:
        cursor.execute(adapted_query, adapted_args)
        if one:
            result = cursor.fetchone()
            return dict(result) if result else None
        else:
            results = cursor.fetchall()
            return [dict(row) for row in results] if results else []
    except Exception as e:
        print(f"ERRO DE QUERY: {e}\nQuery: {adapted_query}\nArgs: {adapted_args}")
        return None # Retorna None em caso de erro de SELECT
    finally:
        cursor.close()


def execute_db(query, args=()):
    """Executa uma operação (INSERT, UPDATE, DELETE) e retorna o ID (se aplicável)."""
    db = get_db()
    cursor = db.cursor()
    adapted_query, adapted_args = _adapt_query_args(query, args)
    
    # Define a cláusula de retorno de ID
    return_id_clause = "RETURNING id"
    if g.get('is_sqlite', False):
        return_id_clause = "" # SQLite não suporta RETURNING em INSERT/UPDATE assim

    # Verifica se é INSERT e ajusta a query
    is_insert = adapted_query.strip().upper().startswith("INSERT")
    
    try:
        if is_insert and not g.get('is_sqlite', False):
            # PostgreSQL: Usa RETURNING id
            if not adapted_query.strip().endswith(";"):
                adapted_query = adapted_query.rstrip() + f" {return_id_clause};"
            else:
                adapted_query = adapted_query.rstrip().rstrip(";") + f" {return_id_clause};"
            
            cursor.execute(adapted_query, adapted_args)
            new_id = cursor.fetchone()
            db.commit()
            return new_id[0] if new_id else None
        
        else:
            # SQLite (ou non-INSERT)
            cursor.execute(adapted_query, adapted_args)
            db.commit()
            
            if is_insert and g.get('is_sqlite', False):
                # SQLite: Pega o lastrowid
                return cursor.lastrowid
            
            return cursor.rowcount # Para UPDATE/DELETE, retorna o nro de linhas
            
    except Exception as e:
        db.rollback()
        print(f"ERRO DE EXECUÇÃO: {e}\nQuery: {adapted_query}\nArgs: {adapted_args}")
        raise # Re-lança a exceção para que a rota possa tratá-la (ex: flash message)
    finally:
        cursor.close()


def logar_timeline(implantacao_id, usuario_cs, tipo_evento, detalhe):
    """Registra um evento na timeline da implantação."""
    try:
        execute_db(
            "INSERT INTO timeline_log (implantacao_id, usuario_cs, tipo_evento, detalhe, data_criacao) VALUES (%s, %s, %s, %s, %s)",
            (implantacao_id, usuario_cs, tipo_evento, detalhe, datetime.now())
        )
    except Exception as e:
        print(f"ERRO CRÍTICO: Falha ao logar timeline para Impl. ID {implantacao_id}. Erro: {e}")
        # Não re-lança a exceção para não quebrar a operação principal
        
# --- Funções de Schema (init-db) ---

def _get_existing_columns(cursor, table_name):
    """Busca as colunas existentes de uma tabela."""
    if g.get('is_sqlite', False):
        cursor.execute(f"PRAGMA table_info({table_name})")
        return [row['name'] for row in cursor.fetchall()]
    else: # PostgreSQL
        cursor.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = %s
        """, (table_name,))
        return [row['column_name'] for row in cursor.fetchall()]

def check_and_add_column(cursor, table_name, column_name, column_type):
    """Verifica e adiciona uma coluna se ela não existir."""
    existing_columns = _get_existing_columns(cursor, table_name)
    if column_name not in existing_columns:
        try:
            query = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"
            cursor.execute(query)
            print(f"Coluna '{column_name}' adicionada à tabela '{table_name}'.")
        except Exception as e:
            print(f"AVISO: Falha ao adicionar coluna '{column_name}' ({table_name}): {e}")
            # Em Postgres, pode falhar se estiver em transação, mas tentamos mesmo assim
            if not g.get('is_sqlite', False):
                 g.db.rollback() # Desfaz o ALTER TABLE falho

# --- INÍCIO AJUSTE 3: Novas funções para a tabela de regras ---

def _create_table_gamificacao_regras(cursor):
    """Cria a tabela para armazenar as regras editáveis da gamificação."""
    if g.get('is_sqlite', False):
        pk_type = "INTEGER PRIMARY KEY AUTOINCREMENT"
    else: # Postgres
        pk_type = "SERIAL PRIMARY KEY"

    query = f"""
    CREATE TABLE IF NOT EXISTS gamificacao_regras (
        id {pk_type},
        regra_id VARCHAR(100) UNIQUE NOT NULL,
        categoria VARCHAR(100) NOT NULL,
        descricao TEXT NOT NULL,
        valor_pontos INTEGER NOT NULL DEFAULT 0,
        tipo_valor VARCHAR(20) DEFAULT 'pontos' -- 'pontos', 'percentual', 'dias', 'quantidade', 'penalidade'
    );
    """
    cursor.execute(query)
    print("Tabela 'gamificacao_regras' verificada/criada.")

def _populate_gamificacao_regras(cursor):
    """Insere as regras padrão (hard-coded) no banco de dados, se não existirem."""
    
    # Lista de regras (baseado no services.py)
    # (regra_id, categoria, descricao, valor_pontos, tipo_valor)
    regras_padrao = [
        # Elegibilidade (tipo_valor 'percentual' ou 'quantidade')
        ('eleg_nota_qualidade_min', 'Elegibilidade', 'Nota de Qualidade Mínima', 80, 'percentual'),
        ('eleg_assiduidade_min', 'Elegibilidade', 'Assiduidade Mínima', 85, 'percentual'),
        ('eleg_planos_sucesso_min', 'Elegibilidade', 'Planos de Sucesso em Dia Mínimo', 75, 'percentual'),
        ('eleg_reclamacoes_max', 'Elegibilidade', 'Reclamações (Máximo)', 1, 'quantidade'), # (regra é >= max+1)
        ('eleg_perda_prazo_max', 'Elegibilidade', 'Perda de Prazo (Máximo)', 2, 'quantidade'),
        ('eleg_nao_preenchimento_max', 'Elegibilidade', 'Não Preenchimento (Máximo)', 2, 'quantidade'),
        ('eleg_finalizadas_junior', 'Elegibilidade', 'Impl. Finalizadas Mín. (Júnior)', 4, 'quantidade'),
        ('eleg_finalizadas_pleno', 'Elegibilidade', 'Impl. Finalizadas Mín. (Pleno)', 5, 'quantidade'),
        ('eleg_finalizadas_senior', 'Elegibilidade', 'Impl. Finalizadas Mín. (Sênior)', 5, 'quantidade'),

        # Pontuação: Satisfação
        ('pts_satisfacao_100', 'Pontos: Satisfação', 'Satisfação >= 100%', 25, 'pontos'),
        ('pts_satisfacao_95', 'Pontos: Satisfação', 'Satisfação >= 95%', 17, 'pontos'),
        ('pts_satisfacao_90', 'Pontos: Satisfação', 'Satisfação >= 90%', 15, 'pontos'),
        ('pts_satisfacao_85', 'Pontos: Satisfação', 'Satisfação >= 85%', 14, 'pontos'),
        ('pts_satisfacao_80', 'Pontos: Satisfação', 'Satisfação >= 80%', 12, 'pontos'),

        # Pontuação: Assiduidade
        ('pts_assiduidade_100', 'Pontos: Assiduidade', 'Assiduidade >= 100%', 30, 'pontos'),
        ('pts_assiduidade_98', 'Pontos: Assiduidade', 'Assiduidade >= 98%', 20, 'pontos'),
        ('pts_assiduidade_95', 'Pontos: Assiduidade', 'Assiduidade >= 95%', 15, 'pontos'),

        # Pontuação: TMA (Dias)
        ('pts_tma_30', 'Pontos: TMA', 'TMA <= 30 dias', 45, 'pontos'),
        ('pts_tma_35', 'Pontos: TMA', 'TMA <= 35 dias', 32, 'pontos'),
        ('pts_tma_40', 'Pontos: TMA', 'TMA <= 40 dias', 24, 'pontos'),
        ('pts_tma_45', 'Pontos: TMA', 'TMA <= 45 dias', 16, 'pontos'),
        ('pts_tma_46_mais', 'Pontos: TMA', 'TMA >= 46 dias', 8, 'pontos'),

        # Pontuação: Média Reuniões/Dia
        ('pts_reunioes_5', 'Pontos: Média Reuniões', 'Média Reuniões/Dia >= 5', 40, 'pontos'),
        ('pts_reunioes_4', 'Pontos: Média Reuniões', 'Média Reuniões/Dia >= 4', 35, 'pontos'),
        ('pts_reunioes_3', 'Pontos: Média Reuniões', 'Média Reuniões/Dia >= 3', 25, 'pontos'),
        ('pts_reunioes_2', 'Pontos: Média Reuniões', 'Média Reuniões/Dia >= 2', 10, 'pontos'),

        # Pontuação: Média Ações/Dia
        ('pts_acoes_7', 'Pontos: Média Ações', 'Média Ações/Dia >= 7', 20, 'pontos'),
        ('pts_acoes_6', 'Pontos: Média Ações', 'Média Ações/Dia >= 6', 15, 'pontos'),
        ('pts_acoes_5', 'Pontos: Média Ações', 'Média Ações/Dia >= 5', 10, 'pontos'),
        ('pts_acoes_4', 'Pontos: Média Ações', 'Média Ações/Dia >= 4', 5, 'pontos'),
        ('pts_acoes_3', 'Pontos: Média Ações', 'Média Ações/Dia >= 3', 3, 'pontos'),

        # Pontuação: Planos de Sucesso
        ('pts_planos_100', 'Pontos: Planos Sucesso', 'Planos Sucesso >= 100%', 45, 'pontos'),
        ('pts_planos_95', 'Pontos: Planos Sucesso', 'Planos Sucesso >= 95%', 35, 'pontos'),
        ('pts_planos_90', 'Pontos: Planos Sucesso', 'Planos Sucesso >= 90%', 30, 'pontos'),
        ('pts_planos_85', 'Pontos: Planos Sucesso', 'Planos Sucesso >= 85%', 20, 'pontos'),
        ('pts_planos_80', 'Pontos: Planos Sucesso', 'Planos Sucesso >= 80%', 10, 'pontos'),

        # Pontuação: Impl. Iniciadas
        ('pts_iniciadas_10', 'Pontos: Impl. Iniciadas', 'Impl. Iniciadas >= 10', 45, 'pontos'),
        ('pts_iniciadas_9', 'Pontos: Impl. Iniciadas', 'Impl. Iniciadas = 9', 32, 'pontos'),
        ('pts_iniciadas_8', 'Pontos: Impl. Iniciadas', 'Impl. Iniciadas = 8', 24, 'pontos'),
        ('pts_iniciadas_7', 'Pontos: Impl. Iniciadas', 'Impl. Iniciadas = 7', 16, 'pontos'),
        ('pts_iniciadas_6', 'Pontos: Impl. Iniciadas', 'Impl. Iniciadas = 6', 8, 'pontos'),

        # Pontuação: Qualidade
        ('pts_qualidade_100', 'Pontos: Qualidade', 'Nota Qualidade >= 100%', 55, 'pontos'),
        ('pts_qualidade_95', 'Pontos: Qualidade', 'Nota Qualidade >= 95%', 40, 'pontos'),
        ('pts_qualidade_90', 'Pontos: Qualidade', 'Nota Qualidade >= 90%', 30, 'pontos'),
        ('pts_qualidade_85', 'Pontos: Qualidade', 'Nota Qualidade >= 85%', 15, 'pontos'),
        ('pts_qualidade_80', 'Pontos: Qualidade', 'Nota Qualidade >= 80%', 0, 'pontos'),

        # Bônus (Pontos por ocorrência)
        ('bonus_elogios', 'Bônus', 'Elogio de cliente (máx 1)', 15, 'pontos'),
        ('bonus_recomendacoes', 'Bônus', 'Recomendações estratégicas (por ocorrência)', 1, 'pontos'),
        ('bonus_certificacoes', 'Bônus', 'Novas certificações (máx 1)', 15, 'pontos'),
        ('bonus_trein_pacto_part', 'Bônus', 'Treinamentos Pacto (Participação, por ocorr.)', 15, 'pontos'),
        ('bonus_trein_pacto_aplic', 'Bônus', 'Treinamentos Pacto (Aplicação, por ocorr.)', 30, 'pontos'),
        
        # Bônus: Reuniões Presenciais (faixa)
        ('bonus_reun_pres_10', 'Bônus: Reuniões Pres.', 'Reuniões Presenciais > 10', 35, 'pontos'),
        ('bonus_reun_pres_7', 'Bônus: Reuniões Pres.', 'Reuniões Presenciais >= 7', 30, 'pontos'),
        ('bonus_reun_pres_5', 'Bônus: Reuniões Pres.', 'Reuniões Presenciais >= 5', 25, 'pontos'),
        ('bonus_reun_pres_3', 'Bônus: Reuniões Pres.', 'Reuniões Presenciais >= 3', 20, 'pontos'),
        ('bonus_reun_pres_1', 'Bônus: Reuniões Pres.', 'Reuniões Presenciais >= 1', 15, 'pontos'),

        # Penalidades (Pontos negativos por ocorrência)
        ('penal_reclamacao', 'Penalidades', 'Reclamação de atendimento (por ocorrência)', -50, 'penalidade'),
        ('penal_perda_prazo', 'Penalidades', 'Perda de prazo (por ocorrência)', -10, 'penalidade'),
        ('penal_desc_incomp', 'Penalidades', 'Descrição incompreensível (por ocorrência)', -10, 'penalidade'),
        ('penal_cancel_resp', 'Penalidades', 'Cancelamento por resp. implantador (por ocorr.)', -100, 'penalidade'),
        ('penal_nao_envolv', 'Penalidades', 'Não envolvimento outras áreas (por ocorr.)', -10, 'penalidade'),
        ('penal_nao_preench', 'Penalidades', 'Não preenchimento tela apoio/CX (por ocorr.)', -10, 'penalidade'),
        ('penal_sla_grupo', 'Penalidades', 'Perda prazo - SLA grupo cliente (por ocorr.)', -5, 'penalidade'),
        ('penal_final_incomp', 'Penalidades', 'Finalização processos incompleta (por ocorr.)', -10, 'penalidade'),
        ('penal_hora_extra', 'Penalidades', 'Hora extra s/ autorização (por ocorr.)', -10, 'penalidade'),
    ]

    # Prepara a query de inserção (INSERT OR IGNORE / ON CONFLICT DO NOTHING)
    if g.get('is_sqlite', False):
        sql_insert = "INSERT OR IGNORE INTO gamificacao_regras (regra_id, categoria, descricao, valor_pontos, tipo_valor) VALUES (?, ?, ?, ?, ?)"
    else: # Postgres
        sql_insert = """
            INSERT INTO gamificacao_regras (regra_id, categoria, descricao, valor_pontos, tipo_valor) 
            VALUES (%s, %s, %s, %s, %s) 
            ON CONFLICT (regra_id) DO NOTHING
        """
        
    try:
        # Usa executemany para eficiência
        args_list = [(r[0], r[1], r[2], r[3], r[4]) for r in regras_padrao]
        adapted_query, _ = _adapt_query_args(sql_insert, ()) # Adapta a query base
        
        if g.get('is_sqlite', False):
             cursor.executemany(adapted_query, args_list)
        else:
             psycopg2.extras.execute_batch(cursor, adapted_query, args_list)
             
        print(f"Verificadas/Inseridas {len(regras_padrao)} regras padrão de gamificação.")
    except Exception as e:
        print(f"ERRO ao popular 'gamificacao_regras': {e}")
        if not g.get('is_sqlite', False):
            g.db.rollback()

# --- FIM AJUSTE 3 ---


def init_db():
    """Função principal para inicializar/atualizar o schema do DB."""
    db = get_db()
    cursor = db.cursor()

    # --- Criação de Tabelas (IF NOT EXISTS) ---
    # (Tabelas existentes omitidas para brevidade...)
    # Tabela 1: usuarios
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id_usuario INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario TEXT UNIQUE NOT NULL,
        senha TEXT NOT NULL
    )
    """)
    # Tabela 2: implantacoes
    if g.get('is_sqlite', False):
        pk_type_impl = "INTEGER PRIMARY KEY AUTOINCREMENT"
    else:
        pk_type_impl = "SERIAL PRIMARY KEY"
    
    cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS implantacoes (
        id {pk_type_impl},
        usuario_cs TEXT NOT NULL,
        nome_empresa TEXT NOT NULL,
        data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        status TEXT DEFAULT 'andamento',
        tipo TEXT DEFAULT 'completa',
        data_inicio_previsto DATE,
        data_inicio_efetivo TIMESTAMP,
        data_finalizacao TIMESTAMP,
        motivo_parada TEXT
    )
    """)
    # Tabela 3: tarefas
    if g.get('is_sqlite', False):
        pk_type_tarefas = "INTEGER PRIMARY KEY AUTOINCREMENT"
    else:
        pk_type_tarefas = "SERIAL PRIMARY KEY"
        
    cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS tarefas (
        id {pk_type_tarefas},
        implantacao_id INTEGER NOT NULL,
        tarefa_pai TEXT NOT NULL,
        tarefa_filho TEXT NOT NULL,
        ordem INTEGER DEFAULT 0,
        concluida BOOLEAN DEFAULT FALSE,
        tag TEXT,
        data_conclusao TIMESTAMP,
        FOREIGN KEY (implantacao_id) REFERENCES implantacoes (id) ON DELETE CASCADE
    )
    """)
    # Tabela 4: comentarios
    if g.get('is_sqlite', False):
        pk_type_comentarios = "INTEGER PRIMARY KEY AUTOINCREMENT"
    else:
        pk_type_comentarios = "SERIAL PRIMARY KEY"
        
    cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS comentarios (
        id {pk_type_comentarios},
        tarefa_id INTEGER NOT NULL,
        usuario_cs TEXT NOT NULL,
        comentario TEXT NOT NULL,
        imagem_url TEXT,
        data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (tarefa_id) REFERENCES tarefas (id) ON DELETE CASCADE
    )
    """)
    # Tabela 5: perfil_usuario
    if g.get('is_sqlite', False):
        pk_type_perfil = "INTEGER PRIMARY KEY AUTOINCREMENT"
    else:
        pk_type_perfil = "SERIAL PRIMARY KEY"
        
    cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS perfil_usuario (
        id {pk_type_perfil},
        usuario TEXT UNIQUE NOT NULL,
        nome TEXT,
        cargo TEXT,
        foto_url TEXT,
        impl_andamento_total INTEGER DEFAULT 0,
        implantacoes_atrasadas INTEGER DEFAULT 0,
        impl_finalizadas INTEGER DEFAULT 0,
        impl_paradas INTEGER DEFAULT 0,
        perfil_acesso TEXT
    )
    """)
    # Tabela 6: timeline_log
    if g.get('is_sqlite', False):
        pk_type_timeline = "INTEGER PRIMARY KEY AUTOINCREMENT"
    else:
        pk_type_timeline = "SERIAL PRIMARY KEY"
        
    cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS timeline_log (
        id {pk_type_timeline},
        implantacao_id INTEGER NOT NULL,
        usuario_cs TEXT NOT NULL,
        tipo_evento TEXT NOT NULL,
        detalhe TEXT,
        data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (implantacao_id) REFERENCES implantacoes (id) ON DELETE CASCADE
    )
    """)
    
    # Tabela 7: gamificacao_metricas_mensais (REQ 4)
    if g.get('is_sqlite', False):
        pk_type_gamificacao = "INTEGER PRIMARY KEY AUTOINCREMENT"
        float_type = "REAL"
    else:
        pk_type_gamificacao = "SERIAL PRIMARY KEY"
        float_type = "NUMERIC(10, 2)" # Postgres
        
    cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS gamificacao_metricas_mensais (
        id {pk_type_gamificacao},
        usuario_cs TEXT NOT NULL,
        mes INTEGER NOT NULL,
        ano INTEGER NOT NULL,
        data_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        
        -- Métricas Manuais
        nota_qualidade {float_type},
        assiduidade {float_type},
        planos_sucesso_perc {float_type},
        satisfacao_processo {float_type},
        reclamacoes INTEGER DEFAULT 0,
        perda_prazo INTEGER DEFAULT 0,
        nao_preenchimento INTEGER DEFAULT 0,
        elogios INTEGER DEFAULT 0,
        recomendacoes INTEGER DEFAULT 0,
        certificacoes INTEGER DEFAULT 0,
        treinamentos_pacto_part INTEGER DEFAULT 0,
        treinamentos_pacto_aplic INTEGER DEFAULT 0,
        reunioes_presenciais INTEGER DEFAULT 0,
        cancelamentos_resp INTEGER DEFAULT 0,
        nao_envolvimento INTEGER DEFAULT 0,
        desc_incompreensivel INTEGER DEFAULT 0,
        hora_extra INTEGER DEFAULT 0,
        perda_sla_grupo INTEGER DEFAULT 0,
        finalizacao_incompleta INTEGER DEFAULT 0,

        -- Métricas Calculadas (para relatório)
        pontuacao_calculada INTEGER,
        elegivel BOOLEAN,
        impl_finalizadas_mes INTEGER,
        tma_medio_mes {float_type},
        impl_iniciadas_mes INTEGER,
        reunioes_concluidas_dia_media {float_type},
        acoes_concluidas_dia_media {float_type},

        UNIQUE(usuario_cs, mes, ano)
    )
    """)

    # --- INÍCIO AJUSTE 3 ---
    # Tabela 8: gamificacao_regras (REQ AJUSTE 3)
    _create_table_gamificacao_regras(cursor)
    # --- FIM AJUSTE 3 ---


    print("Tabelas verificadas/criadas.")

    # --- Migrações (Adição de Colunas) ---
    # (Omitido para brevidade... colunas existentes)
    check_and_add_column(cursor, 'implantacoes', 'responsavel_cliente', 'VARCHAR(255)')
    check_and_add_column(cursor, 'implantacoes', 'cargo_responsavel', 'VARCHAR(100)')
    check_and_add_column(cursor, 'implantacoes', 'telefone_responsavel', 'VARCHAR(20)')
    check_and_add_column(cursor, 'implantacoes', 'email_responsavel', 'VARCHAR(255)')
    check_and_add_column(cursor, 'implantacoes', 'data_inicio_producao', 'DATE')
    check_and_add_column(cursor, 'implantacoes', 'data_final_implantacao', 'DATE')
    check_and_add_column(cursor, 'implantacoes', 'id_favorecido', 'VARCHAR(100)')
    check_and_add_column(cursor, 'implantacoes', 'nivel_receita', 'VARCHAR(100)')
    check_and_add_column(cursor, 'implantacoes', 'chave_oamd', 'VARCHAR(255)')
    check_and_add_column(cursor, 'implantacoes', 'catraca', 'VARCHAR(20)')
    check_and_add_column(cursor, 'implantacoes', 'facial', 'VARCHAR(20)')
    check_and_add_column(cursor, 'implantacoes', 'valor_atribuido', 'VARCHAR(50)')
    check_and_add_column(cursor, 'implantacoes', 'tela_apoio_link', 'TEXT')
    check_and_add_column(cursor, 'implantacoes', 'resp_estrategico_nome', 'VARCHAR(255)')
    check_and_add_column(cursor, 'implantacoes', 'resp_onb_nome', 'VARCHAR(255)')
    check_and_add_column(cursor, 'implantacoes', 'resp_estrategico_obs', 'TEXT')
    check_and_add_column(cursor, 'implantacoes', 'contatos', 'TEXT')
    check_and_add_column(cursor, 'implantacoes', 'seguimento', 'TEXT')
    check_and_add_column(cursor, 'implantacoes', 'tipos_planos', 'TEXT')
    check_and_add_column(cursor, 'implantacoes', 'modalidades', 'TEXT')
    check_and_add_column(cursor, 'implantacoes', 'horarios_func', 'TEXT')
    check_and_add_column(cursor, 'implantacoes', 'formas_pagamento', 'TEXT')
    check_and_add_column(cursor, 'implantacoes', 'diaria', 'VARCHAR(20)')
    check_and_add_column(cursor, 'implantacoes', 'freepass', 'VARCHAR(20)')
    check_and_add_column(cursor, 'implantacoes', 'alunos_ativos', 'INTEGER')
    check_and_add_column(cursor, 'implantacoes', 'sistema_anterior', 'VARCHAR(100)')
    check_and_add_column(cursor, 'implantacoes', 'importacao', 'VARCHAR(20)')
    check_and_add_column(cursor, 'implantacoes', 'recorrencia_usa', 'VARCHAR(100)')
    check_and_add_column(cursor, 'implantacoes', 'boleto', 'VARCHAR(20)')
    check_and_add_column(cursor, 'implantacoes', 'nota_fiscal', 'VARCHAR(20)')

    print("Migrações de colunas verificadas.")
    
    # --- Populações Padrão ---
    
    # --- INÍCIO AJUSTE 3 ---
    # Popula a nova tabela de regras (só insere se não existir)
    _populate_gamificacao_regras(cursor)
    # --- FIM AJUSTE 3 ---

    # Commit final para garantir que tudo (criação e migração) seja salvo
    try:
        db.commit()
    except Exception as e:
        print(f"AVISO: Erro durante o commit final do init_db (pode ocorrer em transações complexas): {e}")
        db.rollback()

    cursor.close()

# --- Comandos Flask ---

@click.command('init-db')
def init_db_command():
    """Limpa os dados existentes (se houver) e cria novas tabelas."""
    try:
        init_db()
        click.echo('Banco de dados inicializado e migrações aplicadas.')
    except Exception as e:
        click.echo(f'Falha ao inicializar o banco de dados: {e}', err=True)

def init_app(app):
    """Registra as funções de teardown e o comando init-db no app Flask."""
    app.teardown_appcontext(close_connection)
    app.cli.add_command(init_db_command)