
import sqlite3
import psycopg2
from psycopg2.extras import DictCursor
from flask import current_app, g
from datetime import datetime
import os
import click
from flask.cli import with_appcontext
from contextlib import contextmanager

from .database import get_db_connection as get_pooled_connection

from .common.exceptions import DatabaseError

def get_db_connection():
    """
    Retorna uma conexão com o banco de dados (SQLite ou PostgreSQL).
    Agora usa connection pooling para PostgreSQL.
    """

    return get_pooled_connection()


@contextmanager
def db_connection():
    """
    Context manager para conexões de banco de dados.
    Garante que a conexão seja fechada corretamente, mesmo em caso de erro.

    Uso:
        with db_connection() as (conn, db_type):
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM usuarios")
            # Conexão é fechada automaticamente ao sair do bloco

    Yields:
        tuple: (conexão, tipo_db) onde tipo_db é 'sqlite' ou 'postgresql'
    """
    conn, db_type = None, None
    use_sqlite = current_app.config.get('USE_SQLITE_LOCALLY', False)

    try:
        conn, db_type = get_db_connection()
        yield conn, db_type
    except Exception as e:
        if conn:
            conn.rollback()
        raise
    finally:

        if use_sqlite and conn:
            conn.close()

def query_db(query, args=(), one=False, raise_on_error=False):
    """
    Executa uma query SELECT (APENAS LEITURA) e retorna o resultado.

    Args:
        query: Query SQL a executar
        args: Argumentos da query (tuple)
        one: Se True, retorna apenas um resultado
        raise_on_error: Se True, lança DatabaseError em caso de erro (padrão: False para retrocompatibilidade)

    Returns:
        Resultado da query (dict ou list de dicts) ou None/[] em caso de erro (se raise_on_error=False)

    Raises:
        DatabaseError: Se raise_on_error=True e ocorrer erro

    Nota: Usa connection pooling e logging adequado.
    """

    try:
        from .performance_monitoring import track_query
        track_query()
    except:
        pass                      

    conn, db_type = None, None
    use_sqlite = current_app.config.get('USE_SQLITE_LOCALLY', False)

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

        current_app.logger.error(f"Database query error: {e}", exc_info=True)
        current_app.logger.debug(f"Query: {query[:100]}...")                      
        if conn:
            conn.rollback()

        if raise_on_error:
            raise DatabaseError(f"Erro ao executar query: {e}", {'query': query[:100], 'args': args}) from e

        return None if one else []
    finally:

        if use_sqlite and conn:
            conn.close()

def execute_db(query, args=(), raise_on_error=False):
    """
    Executa uma query de INSERT, UPDATE ou DELETE no banco de dados.

    Args:
        query: Query SQL a executar
        args: Argumentos da query (tuple)
        raise_on_error: Se True, lança DatabaseError em caso de erro (padrão: False para retrocompatibilidade)

    Returns:
        Número de linhas afetadas ou None em caso de erro (se raise_on_error=False)

    Raises:
        DatabaseError: Se raise_on_error=True e ocorrer erro

    Nota: Usa connection pooling e logging adequado.
    """

    try:
        from .performance_monitoring import track_query
        track_query()
    except:
        pass                      

    conn, db_type = None, None
    use_sqlite = current_app.config.get('USE_SQLITE_LOCALLY', False)

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

        current_app.logger.error(f"Database execution error: {e}", exc_info=True)
        current_app.logger.debug(f"Query: {query[:100]}...")                      
        if conn:
            conn.rollback()

        if raise_on_error:
            raise DatabaseError(f"Erro ao executar query: {e}", {'query': query[:100], 'args': args}) from e

        return None
    finally:

        if use_sqlite and conn:
            conn.close()

def execute_and_fetch_one(query, args=()):
    """
    Executa uma query de MUTATION (INSERT/UPDATE) que retorna um
    valor (ex: RETURNING id) e faz commit.
    Agora usa connection pooling e logging adequado.
    """
    conn, db_type = None, None
    use_sqlite = current_app.config.get('USE_SQLITE_LOCALLY', False)

    try:
        conn, db_type = get_db_connection()
        cursor = conn.cursor()

        if db_type == 'sqlite':
            query = query.replace('%s', '?')

        cursor.execute(query, args)
        result = cursor.fetchone()
        conn.commit()

        return dict(result) if result else None

    except Exception as e:

        current_app.logger.error(f"Database execute_and_fetch error: {e}")
        current_app.logger.debug(f"Query: {query[:100]}...")                      
        if conn:
            conn.rollback()
        return None
    finally:

        if use_sqlite and conn:
            conn.close()


@contextmanager
def db_transaction_with_lock():
    """
    Context manager para transações com lock de linha.
    Garante atomicidade e previne race conditions.
    
    IMPORTANTE: 
    - Para PostgreSQL: usa SELECT FOR UPDATE para lock
    - Para SQLite: usa BEGIN IMMEDIATE TRANSACTION para lock
    - Não fecha conexões PostgreSQL que estão em g.db_conn (gerenciadas pelo pool)
    - Fecha conexões SQLite após uso
    
    Uso:
        with db_transaction_with_lock() as (conn, cursor, db_type):
            if db_type == 'postgres':
                cursor.execute("SELECT ... FROM tabela WHERE id = %s FOR UPDATE", (id,))
            else:
                cursor.execute("SELECT ... FROM tabela WHERE id = ?", (id,))
            
            row = cursor.fetchone()
            if db_type == 'postgres':
                # cursor retorna dict automaticamente (DictCursor)
                dados = row
            else:
                # SQLite retorna Row object
                dados = dict(row) if row else None
            
            # ... operações na mesma transação ...
            conn.commit()  # Commit automático no context manager
    
    Returns:
        tuple: (conexão, cursor, tipo_db) onde tipo_db é 'sqlite' ou 'postgres'
    
    Raises:
        Exception: Qualquer erro durante a transação (rollback automático)
    """
    conn, db_type = None, None
    use_sqlite = current_app.config.get('USE_SQLITE_LOCALLY', False)
    
    try:
        conn, db_type = get_db_connection()
        cursor = None
        
        # SQLite precisa de transação explícita para lock efetivo
        if db_type == 'sqlite':
            # BEGIN IMMEDIATE garante lock imediato (não espera)
            conn.execute("BEGIN IMMEDIATE TRANSACTION")
            cursor = conn.cursor()
        else:
            # PostgreSQL - cursor já é DictCursor via pool
            cursor = conn.cursor()
            # PostgreSQL lock é feito via SELECT FOR UPDATE
        
        yield conn, cursor, db_type
        
        # Commit automático se não houve exceção
        # Se já foi feito rollback manual, o commit pode falhar (ignoramos silenciosamente)
        if conn:
            try:
                conn.commit()
            except Exception:
                # Se commit falhar (provavelmente porque já foi feito rollback), ignorar
                pass
            
    except Exception as e:
        # Rollback em caso de erro
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass
        raise
    finally:
        # IMPORTANTE: Não fechar conexões PostgreSQL (gerenciadas pelo pool via g.db_conn)
        # Apenas fechar conexões SQLite que criamos localmente
        if use_sqlite and conn:
            try:
                conn.close()
            except Exception:
                pass


def logar_timeline(implantacao_id, usuario_cs, tipo_evento, detalhe):
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
        use_sqlite = current_app.config.get('USE_SQLITE_LOCALLY', False)
        if use_sqlite and conn:
            conn.close()


def init_db():
    """Inicializa o schema do banco de dados (SQLite ou PostgreSQL)."""
    conn, db_type = None, None
    try:
        conn, db_type = get_db_connection()
        cursor = conn.cursor()

        if db_type == 'postgres':

            print("Executando init_db para PostgreSQL...")
            
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                usuario VARCHAR(255) PRIMARY KEY,
                senha TEXT NOT NULL
            );
            """)

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

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS smtp_settings (
                usuario_email VARCHAR(255) PRIMARY KEY REFERENCES usuarios(usuario) ON DELETE CASCADE,
                host TEXT NOT NULL,
                port INTEGER NOT NULL,
                "user" VARCHAR(255) NOT NULL,
                password TEXT,
                use_tls BOOLEAN DEFAULT TRUE,
                use_ssl BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS implantacoes (
                id SERIAL PRIMARY KEY,
                usuario_cs VARCHAR(255) REFERENCES usuarios(usuario) ON DELETE SET NULL,
                nome_empresa TEXT NOT NULL,
                status VARCHAR(50) DEFAULT 'nova' CHECK(status IN ('nova', 'andamento', 'futura', 'finalizada', 'parada', 'cancelada', 'sem_previsao', 'atrasada')),
                tipo VARCHAR(50) DEFAULT 'completa' CHECK(tipo IN ('completa', 'modulo')),
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data_inicio_efetivo TIMESTAMP DEFAULT NULL,
                data_finalizacao TIMESTAMP DEFAULT NULL,
                data_inicio_previsto TEXT DEFAULT NULL,
                motivo_parada TEXT DEFAULT NULL,
                data_cancelamento TIMESTAMP DEFAULT NULL,
                motivo_cancelamento TEXT DEFAULT NULL,
                comprovante_cancelamento_url TEXT DEFAULT NULL,
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

            # Verificar se coluna 'visibilidade' existe antes de adicionar (PostgreSQL)
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='comentarios' AND column_name='visibilidade'
            """)
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE comentarios ADD COLUMN visibilidade VARCHAR(20) DEFAULT 'externo';")
                try:
                    cursor.execute("ALTER TABLE comentarios ADD CONSTRAINT comentarios_visibilidade_check CHECK (visibilidade IN ('interno','externo'));")
                except Exception:
                    pass  # Constraint pode já existir
            
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
            
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_impl_usuario_cs ON implantacoes (usuario_cs);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_impl_status ON implantacoes (status);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tarefas_implantacao_id ON tarefas (implantacao_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_comentarios_tarefa_id ON comentarios (tarefa_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_timeline_log_implantacao_id ON timeline_log (implantacao_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_gamificacao_user_period ON gamificacao_metricas_mensais (usuario_cs, ano, mes);")

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS fases (
                id SERIAL PRIMARY KEY,
                implantacao_id INTEGER NOT NULL REFERENCES implantacoes(id) ON DELETE CASCADE,
                nome TEXT NOT NULL,
                ordem INTEGER DEFAULT 0,
                responsavel VARCHAR(255) DEFAULT NULL
            );
            """)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS grupos (
                id SERIAL PRIMARY KEY,
                fase_id INTEGER NOT NULL REFERENCES fases(id) ON DELETE CASCADE,
                responsavel VARCHAR(255) DEFAULT NULL,
                nome TEXT NOT NULL
            );
            """)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS tarefas_h (
                id SERIAL PRIMARY KEY,
                grupo_id INTEGER NOT NULL REFERENCES grupos(id) ON DELETE CASCADE,
                nome TEXT NOT NULL,
                status VARCHAR(50) DEFAULT 'pendente',
                percentual_conclusao INTEGER DEFAULT 0,
                ordem INTEGER DEFAULT 0,
                responsavel VARCHAR(255) DEFAULT NULL
            );
            """)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS subtarefas_h (
                id SERIAL PRIMARY KEY,
                tarefa_id INTEGER NOT NULL REFERENCES tarefas_h(id) ON DELETE CASCADE,
                nome TEXT NOT NULL,
                concluido BOOLEAN DEFAULT FALSE,
                ordem INTEGER DEFAULT 0,
                responsavel VARCHAR(255) DEFAULT NULL
            );
            """)
            
            # Adicionar colunas de responsável para bancos já existentes
            cursor.execute("""
            DO $$ BEGIN
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='fases' AND column_name='responsavel') THEN
                    ALTER TABLE fases ADD COLUMN responsavel VARCHAR(255) DEFAULT NULL;
                END IF;
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='grupos' AND column_name='responsavel') THEN
                    ALTER TABLE grupos ADD COLUMN responsavel VARCHAR(255) DEFAULT NULL;
                END IF;
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='tarefas_h' AND column_name='responsavel') THEN
                    ALTER TABLE tarefas_h ADD COLUMN responsavel VARCHAR(255) DEFAULT NULL;
                END IF;
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='subtarefas_h' AND column_name='responsavel') THEN
                    ALTER TABLE subtarefas_h ADD COLUMN responsavel VARCHAR(255) DEFAULT NULL;
                END IF;
            END $$;
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS comentarios_h (
                id SERIAL PRIMARY KEY,
                tarefa_h_id INTEGER REFERENCES tarefas_h(id) ON DELETE CASCADE,
                subtarefa_h_id INTEGER REFERENCES subtarefas_h(id) ON DELETE CASCADE,
                usuario_cs VARCHAR(255) REFERENCES usuarios(usuario) ON DELETE SET NULL,
                texto TEXT NOT NULL,
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                imagem_url TEXT DEFAULT NULL,
                visibilidade VARCHAR(20) DEFAULT 'externo' CHECK (visibilidade IN ('interno','externo')),
                CHECK (tarefa_h_id IS NOT NULL OR subtarefa_h_id IS NOT NULL)
            );
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS planos_sucesso (
                id SERIAL PRIMARY KEY,
                nome VARCHAR(255) NOT NULL UNIQUE,
                descricao TEXT,
                ativo BOOLEAN DEFAULT TRUE,
                dias_duracao INTEGER DEFAULT NULL,
                criado_por VARCHAR(255) REFERENCES usuarios(usuario) ON DELETE SET NULL,
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """)
            
            # Adicionar coluna dias_duracao se não existir (para bancos já existentes)
            cursor.execute("""
            DO $$ BEGIN
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='planos_sucesso' AND column_name='dias_duracao') THEN
                    ALTER TABLE planos_sucesso ADD COLUMN dias_duracao INTEGER DEFAULT NULL;
                END IF;
            END $$;
            """)
            
            # Adicionar coluna data_previsao_termino se não existir
            cursor.execute("""
            DO $$ BEGIN
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='implantacoes' AND column_name='data_previsao_termino') THEN
                    ALTER TABLE implantacoes ADD COLUMN data_previsao_termino TIMESTAMP DEFAULT NULL;
                END IF;
            END $$;
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS planos_fases (
                id SERIAL PRIMARY KEY,
                plano_id INTEGER NOT NULL REFERENCES planos_sucesso(id) ON DELETE CASCADE,
                nome VARCHAR(255) NOT NULL,
                descricao TEXT,
                ordem INTEGER DEFAULT 0,
                UNIQUE(plano_id, ordem)
            );
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS planos_grupos (
                id SERIAL PRIMARY KEY,
                fase_id INTEGER NOT NULL REFERENCES planos_fases(id) ON DELETE CASCADE,
                nome VARCHAR(255) NOT NULL,
                descricao TEXT,
                ordem INTEGER DEFAULT 0
            );
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS planos_tarefas (
                id SERIAL PRIMARY KEY,
                grupo_id INTEGER NOT NULL REFERENCES planos_grupos(id) ON DELETE CASCADE,
                nome VARCHAR(255) NOT NULL,
                descricao TEXT,
                obrigatoria BOOLEAN DEFAULT FALSE,
                ordem INTEGER DEFAULT 0
            );
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS planos_subtarefas (
                id SERIAL PRIMARY KEY,
                tarefa_id INTEGER NOT NULL REFERENCES planos_tarefas(id) ON DELETE CASCADE,
                nome VARCHAR(255) NOT NULL,
                descricao TEXT,
                ordem INTEGER DEFAULT 0
            );
            """)

            # Verificar se colunas existem antes de adicionar (PostgreSQL)
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='implantacoes' AND column_name='plano_sucesso_id'
            """)
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE implantacoes ADD COLUMN plano_sucesso_id INTEGER REFERENCES planos_sucesso(id) ON DELETE SET NULL;")
            
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='implantacoes' AND column_name='data_atribuicao_plano'
            """)
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE implantacoes ADD COLUMN data_atribuicao_plano TIMESTAMP;")

            cursor.execute("CREATE INDEX IF NOT EXISTS idx_planos_sucesso_ativo ON planos_sucesso (ativo);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_planos_fases_plano_id ON planos_fases (plano_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_planos_grupos_fase_id ON planos_grupos (fase_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_planos_tarefas_grupo_id ON planos_tarefas (grupo_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_planos_subtarefas_tarefa_id ON planos_subtarefas (tarefa_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_implantacoes_plano_sucesso ON implantacoes (plano_sucesso_id);")

            # Tabela checklist_items para checklist hierárquico infinito
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS checklist_items (
                    id SERIAL PRIMARY KEY,
                    parent_id INTEGER REFERENCES checklist_items(id) ON DELETE CASCADE,
                    title VARCHAR(500) NOT NULL,
                    completed BOOLEAN NOT NULL DEFAULT false,
                    comment TEXT,
                    level INTEGER DEFAULT 0,
                    ordem INTEGER DEFAULT 0,
                    implantacao_id INTEGER,
                    plano_id INTEGER REFERENCES planos_sucesso(id) ON DELETE CASCADE,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT chk_title_not_empty CHECK (LENGTH(TRIM(title)) > 0)
                )
            """)
            
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_checklist_parent_id ON checklist_items(parent_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_checklist_implantacao_id ON checklist_items(implantacao_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_checklist_plano_id ON checklist_items(plano_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_checklist_completed ON checklist_items(completed);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_checklist_ordem ON checklist_items(ordem);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_checklist_parent_ordem ON checklist_items(parent_id, ordem);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_checklist_plano_ordem ON checklist_items(plano_id, ordem);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_checklist_plano_parent ON checklist_items(plano_id, parent_id);")
            
            # Trigger para atualizar updated_at automaticamente (PostgreSQL)
            cursor.execute("""
                CREATE OR REPLACE FUNCTION update_checklist_items_updated_at()
                RETURNS TRIGGER AS $$
                BEGIN
                    NEW.updated_at = CURRENT_TIMESTAMP;
                    RETURN NEW;
                END;
                $$ LANGUAGE plpgsql
            """)
            
            cursor.execute("DROP TRIGGER IF EXISTS trigger_checklist_items_updated_at ON checklist_items;")
            cursor.execute("""
                CREATE TRIGGER trigger_checklist_items_updated_at
                BEFORE UPDATE ON checklist_items
                FOR EACH ROW
                EXECUTE FUNCTION update_checklist_items_updated_at()
            """)

        
        elif db_type == 'sqlite':

            print("Executando init_db para SQLite...")
            
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS implantacoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_cs VARCHAR(255) REFERENCES usuarios(usuario) ON DELETE SET NULL,
                nome_empresa TEXT NOT NULL,
                status VARCHAR(50) DEFAULT 'nova' CHECK(status IN ('nova', 'andamento', 'futura', 'finalizada', 'parada', 'cancelada', 'sem_previsao', 'atrasada')),
                tipo VARCHAR(50) DEFAULT 'completa' CHECK(tipo IN ('completa', 'modulo')),
                data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP,
                data_inicio_efetivo DATETIME DEFAULT NULL,
                data_finalizacao DATETIME DEFAULT NULL,
                data_inicio_previsto TEXT DEFAULT NULL,
                motivo_parada TEXT DEFAULT NULL,
                data_cancelamento DATETIME DEFAULT NULL,
                motivo_cancelamento TEXT DEFAULT NULL,
                comprovante_cancelamento_url TEXT DEFAULT NULL,
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

            try:
                cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='implantacoes'")
                row = cursor.fetchone()
                schema_sql = row[0] if row else ''
                if schema_sql and "sem_previsao" not in schema_sql:
                    current_app.logger.info("Migrando tabela 'implantacoes' para incluir status 'sem_previsao' (SQLite)")
                    cursor.execute("PRAGMA foreign_keys=OFF")
                    cursor.execute("BEGIN TRANSACTION")
                    cursor.execute(
                        """
                        CREATE TABLE IF NOT EXISTS implantacoes_new (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            usuario_cs VARCHAR(255) REFERENCES usuarios(usuario) ON DELETE SET NULL,
                            nome_empresa TEXT NOT NULL,
                            status VARCHAR(50) DEFAULT 'nova' CHECK(status IN ('nova', 'andamento', 'futura', 'finalizada', 'parada', 'cancelada', 'sem_previsao', 'atrasada')),
                            tipo VARCHAR(50) DEFAULT 'completa' CHECK(tipo IN ('completa', 'modulo')),
                            data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP,
                            data_inicio_efetivo DATETIME DEFAULT NULL,
                            data_finalizacao DATETIME DEFAULT NULL,
                            data_inicio_previsto TEXT DEFAULT NULL,
                            motivo_parada TEXT DEFAULT NULL,
                            data_cancelamento DATETIME DEFAULT NULL,
                            motivo_cancelamento TEXT DEFAULT NULL,
                            comprovante_cancelamento_url TEXT DEFAULT NULL,
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
                        """
                    )
                    cursor.execute(
                        """
                        INSERT INTO implantacoes_new (
                            id, usuario_cs, nome_empresa, status, tipo, data_criacao, data_inicio_efetivo, data_finalizacao,
                            data_inicio_previsto, motivo_parada, data_cancelamento, motivo_cancelamento, comprovante_cancelamento_url,
                            responsavel_cliente, cargo_responsavel, telefone_responsavel, email_responsavel, data_inicio_producao,
                            data_final_implantacao, chave_oamd, catraca, facial, nivel_receita, valor_atribuido, id_favorecido,
                            tela_apoio_link, seguimento, tipos_planos, modalidades, horarios_func, formas_pagamento, diaria, freepass,
                            alunos_ativos, sistema_anterior, importacao, recorrencia_usa, boleto, nota_fiscal, resp_estrategico_nome,
                            resp_onb_nome, resp_estrategico_obs, contatos
                        )
                        SELECT 
                            id, usuario_cs, nome_empresa, status, tipo, data_criacao, data_inicio_efetivo, data_finalizacao,
                            data_inicio_previsto, motivo_parada, data_cancelamento, motivo_cancelamento, comprovante_cancelamento_url,
                            responsavel_cliente, cargo_responsavel, telefone_responsavel, email_responsavel, data_inicio_producao,
                            data_final_implantacao, chave_oamd, catraca, facial, nivel_receita, valor_atribuido, id_favorecido,
                            tela_apoio_link, seguimento, tipos_planos, modalidades, horarios_func, formas_pagamento, diaria, freepass,
                            alunos_ativos, sistema_anterior, importacao, recorrencia_usa, boleto, nota_fiscal, resp_estrategico_nome,
                            resp_onb_nome, resp_estrategico_obs, contatos
                        FROM implantacoes;
                        """
                    )
                    cursor.execute("DROP TABLE implantacoes")
                    cursor.execute("ALTER TABLE implantacoes_new RENAME TO implantacoes")
                    cursor.execute("COMMIT")
                    cursor.execute("PRAGMA foreign_keys=ON")
            except Exception as mig_err:
                current_app.logger.error(f"Falha na migração de status 'sem_previsao': {mig_err}")
            
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

            # Verificar se coluna 'visibilidade' existe antes de adicionar
            cursor.execute("PRAGMA table_info(comentarios)")
            columns = [col[1] for col in cursor.fetchall()]
            if 'visibilidade' not in columns:
                cursor.execute("ALTER TABLE comentarios ADD COLUMN visibilidade VARCHAR(20) DEFAULT 'externo'")
            
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

            # --- Tabelas de Planos de Sucesso (SQLite) ---
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS planos_sucesso (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome VARCHAR(255) NOT NULL UNIQUE,
                descricao TEXT,
                ativo BOOLEAN DEFAULT TRUE,
                dias_duracao INTEGER DEFAULT NULL,
                criado_por VARCHAR(255) REFERENCES usuarios(usuario) ON DELETE SET NULL,
                data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP,
                data_atualizacao DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            """)
            
            # Adicionar colunas para bancos já existentes (SQLite)
            try:
                cursor.execute("ALTER TABLE planos_sucesso ADD COLUMN dias_duracao INTEGER DEFAULT NULL")
            except:
                pass  # Coluna já existe
            
            try:
                cursor.execute("ALTER TABLE implantacoes ADD COLUMN data_previsao_termino DATETIME DEFAULT NULL")
            except:
                pass  # Coluna já existe

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS planos_fases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plano_id INTEGER NOT NULL REFERENCES planos_sucesso(id) ON DELETE CASCADE,
                nome VARCHAR(255) NOT NULL,
                descricao TEXT,
                ordem INTEGER DEFAULT 0,
                UNIQUE(plano_id, ordem)
            );
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS planos_grupos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fase_id INTEGER NOT NULL REFERENCES planos_fases(id) ON DELETE CASCADE,
                nome VARCHAR(255) NOT NULL,
                descricao TEXT,
                ordem INTEGER DEFAULT 0
            );
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS planos_tarefas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                grupo_id INTEGER NOT NULL REFERENCES planos_grupos(id) ON DELETE CASCADE,
                nome VARCHAR(255) NOT NULL,
                descricao TEXT,
                obrigatoria BOOLEAN DEFAULT FALSE,
                ordem INTEGER DEFAULT 0
            );
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS planos_subtarefas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tarefa_id INTEGER NOT NULL REFERENCES planos_tarefas(id) ON DELETE CASCADE,
                nome VARCHAR(255) NOT NULL,
                descricao TEXT,
                ordem INTEGER DEFAULT 0
            );
            """)

            # Adicionar colunas de relacionamento na tabela implantacoes se não existirem
            cursor.execute("PRAGMA table_info(implantacoes)")
            impl_columns = [col[1] for col in cursor.fetchall()]
            
            if 'plano_sucesso_id' not in impl_columns:
                cursor.execute("ALTER TABLE implantacoes ADD COLUMN plano_sucesso_id INTEGER REFERENCES planos_sucesso(id) ON DELETE SET NULL")
            
            if 'data_atribuicao_plano' not in impl_columns:
                cursor.execute("ALTER TABLE implantacoes ADD COLUMN data_atribuicao_plano DATETIME")

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
            
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                usuario VARCHAR(255) PRIMARY KEY, 
                senha TEXT NOT NULL
            );
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS smtp_settings (
                usuario_email VARCHAR(255) PRIMARY KEY,
                host TEXT NOT NULL,
                port INTEGER NOT NULL,
                "user" VARCHAR(255) NOT NULL,
                password TEXT,
                use_tls INTEGER DEFAULT 1,
                use_ssl INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            """)

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

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS fases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                implantacao_id INTEGER NOT NULL REFERENCES implantacoes(id) ON DELETE CASCADE,
                nome TEXT NOT NULL,
                ordem INTEGER DEFAULT 0,
                responsavel VARCHAR(255) DEFAULT NULL
            );
            """)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS grupos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fase_id INTEGER NOT NULL REFERENCES fases(id) ON DELETE CASCADE,
                responsavel VARCHAR(255) DEFAULT NULL,
                nome TEXT NOT NULL
            );
            """)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS tarefas_h (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                grupo_id INTEGER NOT NULL REFERENCES grupos(id) ON DELETE CASCADE,
                nome TEXT NOT NULL,
                status VARCHAR(50) DEFAULT 'pendente',
                percentual_conclusao INTEGER DEFAULT 0,
                ordem INTEGER DEFAULT 0,
                responsavel VARCHAR(255) DEFAULT NULL
            );
            """)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS subtarefas_h (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tarefa_id INTEGER NOT NULL REFERENCES tarefas_h(id) ON DELETE CASCADE,
                nome TEXT NOT NULL,
                concluido BOOLEAN DEFAULT FALSE,
                ordem INTEGER DEFAULT 0,
                responsavel VARCHAR(255) DEFAULT NULL
            );
            """)
            
            # Adicionar colunas de responsável para bancos já existentes (SQLite)
            try:
                cursor.execute("ALTER TABLE fases ADD COLUMN responsavel VARCHAR(255) DEFAULT NULL")
            except:
                pass
            try:
                cursor.execute("ALTER TABLE grupos ADD COLUMN responsavel VARCHAR(255) DEFAULT NULL")
            except:
                pass
            try:
                cursor.execute("ALTER TABLE tarefas_h ADD COLUMN responsavel VARCHAR(255) DEFAULT NULL")
            except:
                pass
            try:
                cursor.execute("ALTER TABLE subtarefas_h ADD COLUMN responsavel VARCHAR(255) DEFAULT NULL")
            except:
                pass

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS comentarios_h (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tarefa_h_id INTEGER REFERENCES tarefas_h(id) ON DELETE CASCADE,
                subtarefa_h_id INTEGER REFERENCES subtarefas_h(id) ON DELETE CASCADE,
                usuario_cs VARCHAR(255) REFERENCES usuarios(usuario) ON DELETE SET NULL,
                texto TEXT NOT NULL,
                data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP,
                imagem_url TEXT DEFAULT NULL,
                visibilidade VARCHAR(20) DEFAULT 'externo' CHECK (visibilidade IN ('interno','externo')),
                CHECK (tarefa_h_id IS NOT NULL OR subtarefa_h_id IS NOT NULL)
            );
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS planos_sucesso (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome VARCHAR(255) NOT NULL UNIQUE,
                descricao TEXT,
                ativo BOOLEAN DEFAULT TRUE,
                dias_duracao INTEGER DEFAULT NULL,
                criado_por VARCHAR(255) REFERENCES usuarios(usuario) ON DELETE SET NULL,
                data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP,
                data_atualizacao DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            """)
            
            # Adicionar colunas para bancos já existentes (SQLite)
            try:
                cursor.execute("ALTER TABLE planos_sucesso ADD COLUMN dias_duracao INTEGER DEFAULT NULL")
            except:
                pass  # Coluna já existe
            
            try:
                cursor.execute("ALTER TABLE implantacoes ADD COLUMN data_previsao_termino DATETIME DEFAULT NULL")
            except:
                pass  # Coluna já existe

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS planos_fases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plano_id INTEGER NOT NULL REFERENCES planos_sucesso(id) ON DELETE CASCADE,
                nome VARCHAR(255) NOT NULL,
                descricao TEXT,
                ordem INTEGER DEFAULT 0,
                UNIQUE(plano_id, ordem)
            );
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS planos_grupos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fase_id INTEGER NOT NULL REFERENCES planos_fases(id) ON DELETE CASCADE,
                nome VARCHAR(255) NOT NULL,
                descricao TEXT,
                ordem INTEGER DEFAULT 0
            );
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS planos_tarefas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                grupo_id INTEGER NOT NULL REFERENCES planos_grupos(id) ON DELETE CASCADE,
                nome VARCHAR(255) NOT NULL,
                descricao TEXT,
                obrigatoria BOOLEAN DEFAULT FALSE,
                ordem INTEGER DEFAULT 0
            );
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS planos_subtarefas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tarefa_id INTEGER NOT NULL REFERENCES planos_tarefas(id) ON DELETE CASCADE,
                nome VARCHAR(255) NOT NULL,
                descricao TEXT,
                ordem INTEGER DEFAULT 0
            );
            """)
            
            # Tabela checklist_items para checklist hierárquico infinito (SQLite)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS checklist_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                parent_id INTEGER,
                title TEXT NOT NULL,
                completed INTEGER NOT NULL DEFAULT 0,
                comment TEXT,
                level INTEGER DEFAULT 0,
                ordem INTEGER DEFAULT 0,
                implantacao_id INTEGER,
                plano_id INTEGER,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (parent_id) REFERENCES checklist_items(id) ON DELETE CASCADE,
                CHECK (LENGTH(TRIM(title)) > 0)
            );
            """)
            
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_checklist_parent_id ON checklist_items(parent_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_checklist_implantacao_id ON checklist_items(implantacao_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_checklist_plano_id ON checklist_items(plano_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_checklist_completed ON checklist_items(completed);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_checklist_ordem ON checklist_items(ordem);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_checklist_parent_ordem ON checklist_items(parent_id, ordem);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_checklist_plano_ordem ON checklist_items(plano_id, ordem);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_checklist_plano_parent ON checklist_items(plano_id, parent_id);")
            
            # Verificar se coluna plano_id já existe (para bancos antigos) e adicionar se necessário
            cursor.execute("PRAGMA table_info(checklist_items)")
            checklist_columns = [col[1] for col in cursor.fetchall()]
            
            if 'plano_id' not in checklist_columns:
                try:
                    cursor.execute("ALTER TABLE checklist_items ADD COLUMN plano_id INTEGER")
                    print("✅ Coluna plano_id adicionada à tabela checklist_items (SQLite)")
                except Exception as e:
                    print(f"⚠️ Erro ao adicionar coluna plano_id: {e}")
                    # Continuar mesmo se houver erro (coluna pode já existir)
            
            # Recriar índices se necessário
            try:
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_checklist_plano_id ON checklist_items(plano_id);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_checklist_plano_ordem ON checklist_items(plano_id, ordem);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_checklist_plano_parent ON checklist_items(plano_id, parent_id);")
            except Exception:
                pass  # Índices podem já existir
            
            # Trigger para atualizar updated_at automaticamente (SQLite)
            cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS trigger_checklist_items_updated_at
            AFTER UPDATE ON checklist_items
            FOR EACH ROW
            WHEN NEW.updated_at = OLD.updated_at
            BEGIN
                UPDATE checklist_items 
                SET updated_at = CURRENT_TIMESTAMP 
                WHERE id = NEW.id;
            END
            """)

            # Verificar se colunas existem antes de adicionar (duplicata da verificação anterior)
            cursor.execute("PRAGMA table_info(implantacoes)")
            impl_columns_2 = [col[1] for col in cursor.fetchall()]
            
            if 'plano_sucesso_id' not in impl_columns_2:
                cursor.execute("ALTER TABLE implantacoes ADD COLUMN plano_sucesso_id INTEGER REFERENCES planos_sucesso(id) ON DELETE SET NULL")
            
            if 'data_atribuicao_plano' not in impl_columns_2:
                cursor.execute("ALTER TABLE implantacoes ADD COLUMN data_atribuicao_plano DATETIME")

        sql_check = "SELECT COUNT(*) as c FROM gamificacao_regras"
        cursor.execute(sql_check)
        count_result = cursor.fetchone()
        count = count_result[0] if isinstance(count_result, (tuple, list)) else count_result['c']

        if count == 0:
             print("Populando 'gamificacao_regras' com os valores padrão...")
             regras = [
                ('eleg_nota_qualidade_min', 'Elegibilidade', 'Nota Qualidade (Mín %)', 80, 'percentual'),
                ('eleg_assiduidade_min', 'Elegibilidade', 'Assiduidade (Mín %)', 85, 'percentual'),
                ('eleg_planos_sucesso_min', 'Elegibilidade', 'Planos de Sucesso (Mín %)', 75, 'percentual'),
                ('eleg_reclamacoes_max', 'Elegibilidade', 'Reclamações (Máx)', 1, 'quantidade'),
                ('eleg_perda_prazo_max', 'Elegibilidade', 'Perda de Prazo (Máx)', 2, 'quantidade'),
                ('eleg_nao_preenchimento_max', 'Elegibilidade', 'Não Preenchimento (Máx)', 2, 'quantidade'),
                ('eleg_finalizadas_junior', 'Elegibilidade', 'Impl. Finalizadas (Mín Júnior)', 4, 'quantidade'),
                ('eleg_finalizadas_pleno', 'Elegibilidade', 'Impl. Finalizadas (Mín Pleno)', 5, 'quantidade'),
                ('eleg_finalizadas_senior', 'Elegibilidade', 'Impl. Finalizadas (Mín Sênior)', 5, 'quantidade'),
                ('eleg_reunioes_min', 'Elegibilidade', 'Média Reuniões/Dia (Mín)', 3, 'quantidade'),
                ('pts_satisfacao_100', 'Pontos: Satisfação', 'Satisfação >= 100%', 25, 'pontos'),
                ('pts_satisfacao_95', 'Pontos: Satisfação', 'Satisfação 95-99%', 17, 'pontos'),
                ('pts_satisfacao_90', 'Pontos: Satisfação', 'Satisfação 90-94%', 15, 'pontos'),
                ('pts_satisfacao_85', 'Pontos: Satisfação', 'Satisfação 85-89%', 14, 'pontos'),
                ('pts_satisfacao_80', 'Pontos: Satisfação', 'Satisfação 80-84%', 12, 'pontos'),
                ('pts_assiduidade_100', 'Pontos: Assiduidade', 'Assiduidade >= 100%', 30, 'pontos'),
                ('pts_assiduidade_98', 'Pontos: Assiduidade', 'Assiduidade 98-99%', 20, 'pontos'),
                ('pts_assiduidade_95', 'Pontos: Assiduidade', 'Assiduidade 95-97%', 15, 'pontos'),
                ('pts_tma_30', 'Pontos: TMA', 'TMA <= 30 dias', 45, 'pontos'),
                ('pts_tma_35', 'Pontos: TMA', 'TMA 31-35 dias', 32, 'pontos'),
                ('pts_tma_40', 'Pontos: TMA', 'TMA 36-40 dias', 24, 'pontos'),
                ('pts_tma_45', 'Pontos: TMA', 'TMA 41-45 dias', 16, 'pontos'),
                ('pts_tma_46_mais', 'Pontos: TMA', 'TMA >= 46 dias', 8, 'pontos'),
                ('pts_reunioes_5', 'Pontos: Reuniões/Dia', 'Média Reuniões >= 5', 35, 'pontos'),
                ('pts_reunioes_4', 'Pontos: Reuniões/Dia', 'Média Reuniões >= 4', 30, 'pontos'),
                ('pts_reunioes_3', 'Pontos: Reuniões/Dia', 'Média Reuniões >= 3', 25, 'pontos'),
                ('pts_reunioes_2', 'Pontos: Reuniões/Dia', 'Média Reuniões >= 2', 15, 'pontos'),
                ('pts_acoes_5', 'Pontos: Ações/Dia', 'Média Ações >= 5', 15, 'pontos'),
                ('pts_acoes_4', 'Pontos: Ações/Dia', 'Média Ações >= 4', 10, 'pontos'),
                ('pts_acoes_3', 'Pontos: Ações/Dia', 'Média Ações >= 3', 7, 'pontos'),
                ('pts_acoes_2', 'Pontos: Ações/Dia', 'Média Ações >= 2', 5, 'pontos'),
                ('pts_planos_100', 'Pontos: Planos Sucesso', 'Planos Sucesso >= 100%', 45, 'pontos'),
                ('pts_planos_95', 'Pontos: Planos Sucesso', 'Planos Sucesso 95-99%', 35, 'pontos'),
                ('pts_planos_90', 'Pontos: Planos Sucesso', 'Planos Sucesso 90-94%', 30, 'pontos'),
                ('pts_planos_85', 'Pontos: Planos Sucesso', 'Planos Sucesso 85-89%', 20, 'pontos'),
                ('pts_planos_80', 'Pontos: Planos Sucesso', 'Planos Sucesso 80-84%', 10, 'pontos'),
                ('pts_iniciadas_10', 'Pontos: Impl. Iniciadas', 'Impl. Iniciadas >= 10', 25, 'pontos'),
                ('pts_iniciadas_9', 'Pontos: Impl. Iniciadas', 'Impl. Iniciadas >= 9', 20, 'pontos'),
                ('pts_iniciadas_8', 'Pontos: Impl. Iniciadas', 'Impl. Iniciadas >= 8', 18, 'pontos'),
                ('pts_iniciadas_7', 'Pontos: Impl. Iniciadas', 'Impl. Iniciadas >= 7', 14, 'pontos'),
                ('pts_iniciadas_6', 'Pontos: Impl. Iniciadas', 'Impl. Iniciadas >= 6', 10, 'pontos'),
                ('pts_qualidade_100', 'Pontos: Qualidade', 'Nota Qualidade >= 100%', 55, 'pontos'),
                ('pts_qualidade_95', 'Pontos: Qualidade', 'Nota Qualidade 95-99%', 40, 'pontos'),
                ('pts_qualidade_90', 'Pontos: Qualidade', 'Nota Qualidade 90-94%', 30, 'pontos'),
                ('pts_qualidade_85', 'Pontos: Qualidade', 'Nota Qualidade 85-89%', 15, 'pontos'),
                ('pts_qualidade_80', 'Pontos: Qualidade', 'Nota Qualidade 80-84%', 0, 'pontos'),
                ('bonus_elogios', 'Bônus', 'Elogio (Máx 1)', 15, 'pontos'),
                ('bonus_recomendacoes', 'Bônus', 'Recomendação (por ocorrência)', 1, 'pontos'),
                ('bonus_certificacoes', 'Bônus', 'Certificação (Máx 1)', 15, 'pontos'),
                ('bonus_trein_pacto_part', 'Bônus', 'Treinamento Pacto (Participou)', 15, 'pontos'),
                ('bonus_trein_pacto_aplic', 'Bônus', 'Treinamento Pacto (Aplicou)', 30, 'pontos'),
                ('bonus_reun_pres_10', 'Bônus: Reuniões Pres.', 'Reuniões Presenciais >= 10', 35, 'pontos'),
                ('bonus_reun_pres_7', 'Bônus: Reuniões Pres.', 'Reuniões Presenciais >= 7', 30, 'pontos'),
                ('bonus_reun_pres_5', 'Bônus: Reuniões Pres.', 'Reuniões Presenciais >= 5', 25, 'pontos'),
                ('bonus_reun_pres_3', 'Bônus: Reuniões Pres.', 'Reuniões Presenciais >= 3', 20, 'pontos'),
                ('bonus_reun_pres_1', 'Bônus: Reuniões Pres.', 'Reuniões Presenciais >= 1', 15, 'pontos'),
                ('penal_reclamacao', 'Penalidades', 'Reclamação (por ocorrência)', -50, 'penalidade'),
                ('penal_perda_prazo', 'Penalidades', 'Perda de Prazo (por ocorrência)', -10, 'penalidade'),
                ('penal_desc_incomp', 'Penalidades', 'Descrição Incompreensível (por ocorrência)', -10, 'penalidade'),
                ('penal_cancel_resp', 'Penalidades', 'Cancelamento por Resp. (por ocorrência)', -100, 'penalidade'),
                ('penal_nao_envolv', 'Penalidades', 'Não Envolvimento (por ocorrência)', -10, 'penalidade'),
                ('penal_nao_preench', 'Penalidades', 'Não Preenchimento (por ocorrência)', -10, 'penalidade'),
                ('penal_sla_grupo', 'Penalidades', 'Perda SLA Grupo (por ocorrência)', -5, 'penalidade'),
                ('penal_final_incomp', 'Penalidades', 'Finalização Incompleta (por ocorrência)', -10, 'penalidade'),
                ('penal_hora_extra', 'Penalidades', 'Hora Extra (por ocorrência)', -10, 'penalidade'),
             ]
             sql_insert = "INSERT INTO gamificacao_regras (regra_id, categoria, descricao, valor_pontos, tipo_valor) VALUES (%s, %s, %s, %s, %s)"
             if db_type == 'sqlite':
                 sql_insert = sql_insert.replace('%s', '?')
             for regra in regras:
                 cursor.execute(sql_insert, regra)

        conn.commit()
        print(f"Banco de dados ({db_type}) inicializado/verificado com sucesso.")
        
    except Exception as e:
        print(f"ERRO ao inicializar DB: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

@click.command('init-db')
@with_appcontext
def init_db_command():
    """Cria as tabelas do banco de dados via linha de comando."""
    init_db()
    click.echo('Inicialização do banco de dados concluída.')

def init_app(app):
    """Registra o comando init-db na aplicação."""
    app.cli.add_command(init_db_command)

def ensure_implantacoes_status_constraint():
    conn, db_type = None, None
    try:
        conn, db_type = get_db_connection()
        if db_type != 'postgres':
            return
        cursor = conn.cursor()
        try:
            cursor.execute("ALTER TABLE implantacoes DROP CONSTRAINT IF EXISTS implantacoes_status_check;")
        except Exception:
            pass
        try:
            cursor.execute(
                """
                ALTER TABLE implantacoes
                ADD CONSTRAINT implantacoes_status_check
                CHECK (status IN ('nova', 'andamento', 'futura', 'finalizada', 'parada', 'cancelada', 'sem_previsao', 'atrasada'))
                """
            )
            conn.commit()
        except Exception:
            if conn:
                conn.rollback()
    except Exception:
        if conn:
            conn.rollback()
    finally:
        use_sqlite = current_app.config.get('USE_SQLITE_LOCALLY', False)
        if use_sqlite and conn:
            conn.close()
