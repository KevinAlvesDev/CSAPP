import sqlite3
import psycopg2
from psycopg2.extras import DictCursor
from flask import current_app, g
from datetime import datetime
import os # <-- Importado para construir o caminho

# --- CORREÇÃO (ImportError) ---
def init_app(app):
    """
    Registra funções no app Flask (como teardown).
    Esta função é necessária para o create_app() em __init__.py.
    """
    pass

def get_db_connection():
    """Retorna uma conexão com o banco de dados (SQLite ou PostgreSQL)."""
    use_sqlite = current_app.config.get('USE_SQLITE_LOCALLY', False)
    
    if use_sqlite:
        try:
            # --- CORREÇÃO (Erro "Configuração inválida") ---
            # Ignora o DATABASE_URL do .env e constrói o caminho manualmente
            # __file__ é project/db.py -> dirname é project/ -> dirname é CSAPP/
            base_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__))) 
            db_path = os.path.join(base_dir, 'dashboard_simples.db')
            # --- FIM DA CORREÇÃO ---

            if not os.path.exists(db_path):
                raise ValueError(f"Arquivo do banco de dados SQLite não encontrado em: {db_path}")

            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row # Retorna dicts em vez de tuplas
            print(f"Conectado ao SQLite: {db_path}")
            return conn, 'sqlite'
        except sqlite3.Error as e:
            print(f"ERRO SQLite (ao conectar): {e}")
            raise
        except ValueError as e:
            print(f"ERRO de Caminho SQLite: {e}")
            raise
            
    else: # Modo Produção (PostgreSQL)
        database_url = current_app.config.get('DATABASE_URL')
        if not database_url:
             raise ValueError("Configuração de produção: DATABASE_URL não definida.")
        try:
            conn = psycopg2.connect(database_url, cursor_factory=DictCursor)
            print("Conectado ao PostgreSQL.")
            return conn, 'postgres'
        except psycopg2.Error as e:
            print(f"ERRO PostgreSQL (ao conectar): {e}")
            raise

def query_db(query, args=(), one=False):
    """Executa uma query SELECT no banco de dados."""
    conn, db_type = None, None # <-- CORREÇÃO (UnboundLocalError)
    try:
        conn, db_type = get_db_connection()
        cursor = conn.cursor()
        
        if db_type == 'sqlite':
            query = query.replace('%s', '?')
            
        cursor.execute(query, args)
        
        if one:
            result = cursor.fetchone()
            return dict(result) if result else None
        else:
            results = cursor.fetchall()
            return [dict(row) for row in results] if results else []
            
    except Exception as e:
        print(f"ERRO DE QUERY: {e}\nQuery: {query}\nArgs: {args}")
        return None 
    finally:
        if conn:
            conn.close()

def execute_db(query, args=()):
    """Executa uma query de INSERT, UPDATE ou DELETE no banco de dados."""
    conn, db_type = None, None # <-- CORREÇÃO (UnboundLocalError)
    try:
        conn, db_type = get_db_connection()
        cursor = conn.cursor()
        
        if db_type == 'sqlite':
            query = query.replace('%s', '?')

        cursor.execute(query, args)
        conn.commit()
        
        if cursor.lastrowid:
            return cursor.lastrowid
        return True 
        
    except Exception as e:
        print(f"ERRO DE EXECUÇÃO: {e}\nQuery: {query}\nArgs: {args}")
        if conn:
            conn.rollback()
        return None 
    finally:
        if conn:
            conn.close()

def logar_timeline(implantacao_id, usuario_cs, tipo_evento, detalhe):
    """Registra um evento na timeline. Falha silenciosamente."""
    conn, db_type = None, None # <-- CORREÇÃO (UnboundLocalError)
    try:
        conn, db_type = get_db_connection()
        cursor = conn.cursor()
        
        # --- CORREÇÃO (Erro "detalhe") ---
        # A coluna no DB chama-se 'detalhes' (com "s")
        sql = "INSERT INTO timeline_log (implantacao_id, usuario_cs, tipo_evento, detalhes, data_criacao) VALUES (%s, %s, %s, %s, %s)"
        # --- FIM CORREÇÃO ---

        if db_type == 'sqlite':
            sql = sql.replace('%s', '?')
            
        cursor.execute(sql, (implantacao_id, usuario_cs, tipo_evento, detalhe, datetime.now()))
        conn.commit()
        
    except Exception as e:
        print(f"ERRO CRÍTICO: Falha ao logar timeline para Impl. ID {implantacao_id}. Erro: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

def init_db():
    """Função (opcional) para inicializar o schema do DB (apenas SQLite)."""
    conn, db_type = None, None # <-- CORREÇÃO (UnboundLocalError)
    try:
        conn, db_type = get_db_connection()
        if db_type != 'sqlite':
            print("init_db só é suportado para SQLite.")
            return

        cursor = conn.cursor()
        
        # Tabela de Implantações
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS implantacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome_empresa TEXT NOT NULL,
            usuario_cs TEXT NOT NULL,
            status TEXT DEFAULT 'nova',
            tipo TEXT DEFAULT 'agora',
            data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP,
            data_inicio_previsto TEXT,
            data_inicio_efetivo DATETIME,
            data_finalizacao DATETIME,
            motivo_parada TEXT,
            responsavel_cliente TEXT,
            cargo_responsavel TEXT,
            telefone_responsavel TEXT,
            email_responsavel TEXT,
            data_inicio_producao TEXT,
            data_final_implantacao TEXT,
            chave_oamd TEXT,
            catraca TEXT,
            facial TEXT,
            nivel_receita TEXT,
            valor_atribuido REAL DEFAULT 0,
            id_favorecido TEXT,
            tela_apoio_link TEXT,
            resp_estrategico_nome TEXT,
            resp_onb_nome TEXT,
            resp_estrategico_obs TEXT,
            contatos TEXT,
            seguimento TEXT,
            tipos_planos TEXT,
            modalidades TEXT,
            horarios_func TEXT,
            formas_pagamento TEXT,
            diaria TEXT,
            freepass TEXT,
            alunos_ativos INTEGER,
            sistema_anterior TEXT,
            importacao TEXT,
            recorrencia_usa TEXT,
            boleto TEXT,
            nota_fiscal TEXT
        );
        """)
        
        # Tabela de Tarefas
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS tarefas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            implantacao_id INTEGER NOT NULL,
            tarefa_pai TEXT NOT NULL,
            tarefa_filho TEXT NOT NULL,
            concluida BOOLEAN DEFAULT FALSE,
            ordem INTEGER DEFAULT 0,
            tag TEXT,
            data_conclusao DATETIME,
            FOREIGN KEY (implantacao_id) REFERENCES implantacoes (id) ON DELETE CASCADE
        );
        """)
        
        # Tabela de Comentários
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS comentarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tarefa_id INTEGER NOT NULL,
            usuario_cs TEXT NOT NULL,
            texto TEXT,
            data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP,
            imagem_url TEXT,
            FOREIGN KEY (tarefa_id) REFERENCES tarefas (id) ON DELETE CASCADE
        );
        """)
        
        # Tabela de Log da Timeline
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS timeline_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            implantacao_id INTEGER NOT NULL,
            usuario_cs TEXT,
            tipo_evento TEXT,
            detalhes TEXT,
            data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (implantacao_id) REFERENCES implantacoes (id) ON DELETE CASCADE
        );
        """)

        # Tabela de Perfil de Usuário
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS perfil_usuario (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT UNIQUE NOT NULL,
            nome TEXT,
            cargo TEXT,
            foto_url TEXT,
            perfil_acesso TEXT DEFAULT 'Visualizador',
            impl_andamento_total INTEGER DEFAULT 0,
            implantacoes_atrasadas INTEGER DEFAULT 0,
            impl_finalizadas INTEGER DEFAULT 0,
            impl_paradas INTEGER DEFAULT 0
        );
        """)
        
        # Tabelas de Gamificação (Ajuste 3)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS gamificacao_regras (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            regra_id TEXT UNIQUE NOT NULL,
            categoria TEXT NOT NULL,
            descricao TEXT NOT NULL,
            valor_pontos INTEGER NOT NULL
        );
        """)
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS gamificacao_metricas_mensais (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_cs TEXT NOT NULL,
            mes INTEGER NOT NULL,
            ano INTEGER NOT NULL,
            data_registro DATETIME,
            
            nota_qualidade REAL,
            assiduidade REAL,
            planos_sucesso_perc REAL,
            satisfacao_processo REAL,
            
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

            pontuacao_calculada INTEGER,
            elegivel BOOLEAN,
            impl_finalizadas_mes INTEGER,
            tma_medio_mes REAL,
            impl_iniciadas_mes INTEGER,
            reunioes_concluidas_dia_media REAL,
            acoes_concluidas_dia_media REAL,
            
            UNIQUE(usuario_cs, mes, ano)
        );
        """)

        conn.commit()
        print("Banco de dados (SQLite) inicializado/verificado com sucesso.")
        
    except Exception as e:
        print(f"ERRO ao inicializar DB: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()