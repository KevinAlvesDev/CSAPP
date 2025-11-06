import sqlite3
import psycopg2
from psycopg2.extras import DictCursor
from flask import current_app, g
from datetime import datetime
import os

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
            base_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__))) 
            db_path = os.path.join(base_dir, 'dashboard_simples.db')

            if not os.path.exists(db_path):
                raise ValueError(f"Arquivo do banco de dados SQLite não encontrado em: {db_path}")

            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row 
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
    conn, db_type = None, None
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
    conn, db_type = None, None
    try:
        conn, db_type = get_db_connection()
        cursor = conn.cursor()
        
        if db_type == 'sqlite':
            query = query.replace('%s', '?')

        cursor.execute(query, args)
        conn.commit()
        
        try:
            if query.strip().upper().startswith("INSERT") and db_type == 'postgres':
                pass 
        except Exception:
            pass 

        if cursor.lastrowid: # Funciona bem para SQLite
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
    conn, db_type = None, None
    try:
        conn, db_type = get_db_connection()
        cursor = conn.cursor()
        
        sql = "INSERT INTO timeline_log (implantacao_id, usuario_cs, tipo_evento, detalhes, data_criacao) VALUES (%s, %s, %s, %s, %s)"
        
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

# --- INÍCIO DA CORREÇÃO (init_db) ---
# Esta função agora cria as tabelas em PostgreSQL ou SQLite
def init_db():
    """Inicializa o schema do banco de dados (SQLite ou PostgreSQL)."""
    conn, db_type = None, None
    try:
        conn, db_type = get_db_connection()
        cursor = conn.cursor()

        if db_type == 'postgres':
            # --- Sintaxe PostgreSQL ---
            print("Executando init_db para PostgreSQL...")
            
            # 1. Tabela usuarios
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                usuario VARCHAR(255) PRIMARY KEY,
                senha TEXT NOT NULL
            );
            """)

            # 2. Tabela perfil_usuario
            cursor.execute("""
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
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """)

            # 3. Tabela implantacoes
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS implantacoes (
                id SERIAL PRIMARY KEY,
                usuario_cs VARCHAR(255) REFERENCES usuarios(usuario) ON DELETE SET NULL,
                nome_empresa TEXT NOT NULL,
                status VARCHAR(50) DEFAULT 'nova' CHECK(status IN ('nova', 'andamento', 'futura', 'finalizada', 'parada')),
                tipo VARCHAR(50) DEFAULT 'completa' CHECK(tipo IN ('completa', 'modulo')),
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data_inicio_efetivo TIMESTAMP DEFAULT NULL,
                data_finalizacao TIMESTAMP DEFAULT NULL,
                data_inicio_previsto TEXT DEFAULT NULL,
                motivo_parada TEXT DEFAULT NULL,
                responsavel_cliente TEXT DEFAULT NULL,
                cargo_responsavel TEXT DEFAULT NULL,
                telefone_responsavel VARCHAR(50) DEFAULT NULL,
                email_responsavel VARCHAR(255) DEFAULT NULL,
                data_inicio_producao TEXT DEFAULT NULL,
                data_final_implantacao TEXT DEFAULT NULL,
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
                alunos_ativos INTEGER DEFAULT 0,
                sistema_anterior VARCHAR(100) DEFAULT NULL,
                importacao VARCHAR(20) DEFAULT 'Não definido',
                recorrencia_usa VARCHAR(100) DEFAULT NULL,
                boleto VARCHAR(20) DEFAULT 'Não definido',
                nota_fiscal VARCHAR(20) DEFAULT 'Não definido',
                resp_estrategico_nome VARCHAR(255) DEFAULT NULL,
                resp_onb_nome VARCHAR(255) DEFAULT NULL,
                resp_estrategico_obs TEXT DEFAULT NULL,
                contatos TEXT DEFAULT NULL
            );
            """)

            # 4. Tabela tarefas
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS tarefas (
                id SERIAL PRIMARY KEY,
                implantacao_id INTEGER NOT NULL REFERENCES implantacoes(id) ON DELETE CASCADE,
                tarefa_pai TEXT NOT NULL,
                tarefa_filho TEXT NOT NULL,
                concluida BOOLEAN DEFAULT FALSE,
                ordem INTEGER DEFAULT 0,
                tag VARCHAR(100) DEFAULT NULL,
                data_conclusao TIMESTAMP DEFAULT NULL
            );
            """)

            # 5. Tabela comentarios
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS comentarios (
                id SERIAL PRIMARY KEY,
                tarefa_id INTEGER NOT NULL REFERENCES tarefas(id) ON DELETE CASCADE,
                usuario_cs VARCHAR(255) REFERENCES usuarios(usuario) ON DELETE SET NULL,
                texto TEXT NOT NULL,
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                imagem_url TEXT DEFAULT NULL
            );
            """)
            
            # 6. Tabela timeline_log
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS timeline_log (
                id SERIAL PRIMARY KEY,
                implantacao_id INTEGER NOT NULL REFERENCES implantacoes(id) ON DELETE CASCADE,
                usuario_cs VARCHAR(255) REFERENCES usuarios(usuario) ON DELETE SET NULL,
                tipo_evento VARCHAR(100) NOT NULL,
                detalhes TEXT NOT NULL,
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """)

            # 7. Tabela gamificacao_regras
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS gamificacao_regras (
                id SERIAL PRIMARY KEY,
                regra_id VARCHAR(100) UNIQUE NOT NULL,
                categoria VARCHAR(100) NOT NULL,
                descricao TEXT NOT NULL,
                valor_pontos INTEGER NOT NULL DEFAULT 0,
                tipo_valor VARCHAR(20) DEFAULT 'pontos'
            );
            """)

            # 8. Tabela gamificacao_metricas_mensais
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS gamificacao_metricas_mensais (
                id SERIAL PRIMARY KEY,
                usuario_cs VARCHAR(255) NOT NULL REFERENCES usuarios(usuario) ON DELETE CASCADE,
                mes INTEGER NOT NULL CHECK (mes >= 1 AND mes <= 12),
                ano INTEGER NOT NULL,
                nota_qualidade REAL DEFAULT NULL,
                assiduidade REAL DEFAULT NULL,
                planos_sucesso_perc REAL DEFAULT NULL,
                satisfacao_processo REAL DEFAULT NULL,
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
                impl_finalizadas_mes INTEGER DEFAULT NULL,
                tma_medio_mes REAL DEFAULT NULL,
                impl_iniciadas_mes INTEGER DEFAULT NULL,
                reunioes_concluidas_dia_media REAL DEFAULT NULL,
                acoes_concluidas_dia_media REAL DEFAULT NULL,
                pontuacao_calculada INTEGER DEFAULT NULL,
                elegivel BOOLEAN DEFAULT NULL,
                data_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                registrado_por VARCHAR(255) REFERENCES usuarios(usuario) ON DELETE SET NULL,
                UNIQUE (usuario_cs, mes, ano)
            );
            """)
            
            # Criar Índices (Opcional, mas bom para performance)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_impl_usuario_cs ON implantacoes (usuario_cs);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_impl_status ON implantacoes (status);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tarefas_implantacao_id ON tarefas (implantacao_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_comentarios_tarefa_id ON comentarios (tarefa_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_timeline_log_implantacao_id ON timeline_log (implantacao_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_gamificacao_user_period ON gamificacao_metricas_mensais (usuario_cs, ano, mes);")

        
        elif db_type == 'sqlite':
            # --- Sintaxe SQLite (como estava antes) ---
            print("Executando init_db para SQLite...")
            
            # (O código original para criar tabelas SQLite permanece aqui)
            # Tabela de Implantações (SQLite)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS implantacoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_cs VARCHAR(255) REFERENCES usuarios(usuario) ON DELETE SET NULL,
                nome_empresa TEXT NOT NULL,
                status VARCHAR(50) DEFAULT 'nova' CHECK(status IN ('nova', 'andamento', 'futura', 'finalizada', 'parada')),
                tipo VARCHAR(50) DEFAULT 'completa' CHECK(tipo IN ('completa', 'modulo')),
                data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP,
                data_inicio_efetivo DATETIME DEFAULT NULL,
                data_finalizacao DATETIME DEFAULT NULL,
                data_inicio_previsto TEXT DEFAULT NULL,
                motivo_parada TEXT DEFAULT NULL,
                responsavel_cliente TEXT DEFAULT NULL,
                cargo_responsavel TEXT DEFAULT NULL,
                telefone_responsavel VARCHAR(50) DEFAULT NULL,
                email_responsavel VARCHAR(255) DEFAULT NULL,
                data_inicio_producao TEXT DEFAULT NULL,
                data_final_implantacao TEXT DEFAULT NULL,
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
                alunos_ativos INTEGER DEFAULT 0,
                sistema_anterior VARCHAR(100) DEFAULT NULL,
                importacao VARCHAR(20) DEFAULT 'Não definido',
                recorrencia_usa VARCHAR(100) DEFAULT NULL,
                boleto VARCHAR(20) DEFAULT 'Não definido',
                nota_fiscal VARCHAR(20) DEFAULT 'Não definido',
                resp_estrategico_nome VARCHAR(255) DEFAULT NULL,
                resp_onb_nome VARCHAR(255) DEFAULT NULL,
                resp_estrategico_obs TEXT DEFAULT NULL,
                contatos TEXT DEFAULT NULL
            );
            """)
            
            # Tabela de Tarefas (SQLite)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS tarefas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                implantacao_id INTEGER NOT NULL REFERENCES implantacoes(id) ON DELETE CASCADE,
                tarefa_pai TEXT NOT NULL,
                tarefa_filho TEXT NOT NULL,
                concluida BOOLEAN DEFAULT FALSE,
                ordem INTEGER DEFAULT 0,
                tag VARCHAR(100) DEFAULT NULL,
                data_conclusao DATETIME DEFAULT NULL
            );
            """)
            
            # Tabela de Comentários (SQLite)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS comentarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tarefa_id INTEGER NOT NULL REFERENCES tarefas(id) ON DELETE CASCADE,
                usuario_cs VARCHAR(255) REFERENCES usuarios(usuario) ON DELETE SET NULL,
                texto TEXT NOT NULL,
                data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP,
                imagem_url TEXT DEFAULT NULL
            );
            """)
            
            # Tabela de Log da Timeline (SQLite)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS timeline_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                implantacao_id INTEGER NOT NULL REFERENCES implantacoes(id) ON DELETE CASCADE,
                usuario_cs VARCHAR(255) REFERENCES usuarios(usuario) ON DELETE SET NULL,
                tipo_evento VARCHAR(100) NOT NULL,
                detalhes TEXT NOT NULL,
                data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            """)

            # Tabela de Perfil de Usuário (SQLite)
            cursor.execute("""
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
                data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            """)
            
            # Tabela de Usuários (SQLite)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                usuario VARCHAR(255) PRIMARY KEY, 
                senha TEXT NOT NULL
            );
            """)

            # Tabelas de Gamificação (SQLite)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS gamificacao_regras (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                regra_id VARCHAR(100) UNIQUE NOT NULL,
                categoria VARCHAR(100) NOT NULL,
                descricao TEXT NOT NULL,
                valor_pontos INTEGER NOT NULL DEFAULT 0,
                tipo_valor VARCHAR(20) DEFAULT 'pontos'
            );
            """)
            
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS gamificacao_metricas_mensais (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_cs VARCHAR(255) NOT NULL REFERENCES usuarios(usuario) ON DELETE CASCADE,
                mes INTEGER NOT NULL CHECK (mes >= 1 AND mes <= 12),
                ano INTEGER NOT NULL,
                nota_qualidade REAL DEFAULT NULL,
                assiduidade REAL DEFAULT NULL,
                planos_sucesso_perc REAL DEFAULT NULL,
                satisfacao_processo REAL DEFAULT NULL,
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
                impl_finalizadas_mes INTEGER DEFAULT NULL,
                tma_medio_mes REAL DEFAULT NULL,
                impl_iniciadas_mes INTEGER DEFAULT NULL,
                reunioes_concluidas_dia_media REAL DEFAULT NULL,
                acoes_concluidas_dia_media REAL DEFAULT NULL,
                pontuacao_calculada INTEGER DEFAULT NULL,
                elegivel BOOLEAN DEFAULT NULL,
                data_registro DATETIME DEFAULT CURRENT_TIMESTAMP,
                registrado_por VARCHAR(255) REFERENCES usuarios(usuario) ON DELETE SET NULL,
                UNIQUE (usuario_cs, mes, ano)
            );
            """)

        conn.commit()
        print(f"Banco de dados ({db_type}) inicializado/verificado com sucesso.")
        
    except Exception as e:
        print(f"ERRO ao inicializar DB: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()
# --- FIM DA CORREÇÃO ---