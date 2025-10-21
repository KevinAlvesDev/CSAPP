<<<<<<< HEAD
# -*- coding: utf-8 -*-
=======
>>>>>>> 6d78c716439a5aa5a8166507cdeea87fc9f15668
import sqlite3
import psycopg2
import psycopg2.extras
import os
<<<<<<< HEAD
from flask import Flask, render_template, request, redirect, url_for, session, g, jsonify, send_from_directory, flash
from werkzeug.security import generate_password_hash, check_password_hash
from collections import OrderedDict
from datetime import datetime, date # [CORREÇÃO] Importa 'date' explicitamente
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

load_dotenv()
=======
import urllib.parse as urlparse
from flask import Flask, render_template, request, redirect, url_for, session, g, jsonify, send_from_directory, flash
from werkzeug.security import generate_password_hash, check_password_hash
from collections import OrderedDict
from datetime import datetime
from werkzeug.utils import secure_filename
>>>>>>> 6d78c716439a5aa5a8166507cdeea87fc9f15668

# ===============================================
# CONFIGURAÇÃO INICIAL
# ===============================================

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app = Flask(__name__)
<<<<<<< HEAD
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
=======

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# Garanta que FLASK_SECRET_KEY esteja definida no Render!
>>>>>>> 6d78c716439a5aa5a8166507cdeea87fc9f15668
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'dev_secret_key_change_me')

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

DATABASE_URL = os.environ.get('DATABASE_URL')
<<<<<<< HEAD
=======
# Use SQLite localmente APENAS se DATABASE_URL não estiver definida
>>>>>>> 6d78c716439a5aa5a8166507cdeea87fc9f15668
USE_SQLITE_LOCALLY = not DATABASE_URL
LOCAL_SQLITE_DB = 'dashboard_simples.db'

# ===============================================
<<<<<<< HEAD
# DEFINIÇÕES GLOBAIS
=======
# FUNÇÕES DE HELPER (Upload, etc.)
# ===============================================

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    # ATENÇÃO: Ainda serve arquivos locais. Precisa mudar para S3 em produção real.
    try:
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    except FileNotFoundError:
        return "Arquivo não encontrado", 404

# ===============================================
# DEFINIÇÕES GLOBAIS (Tarefas Padrão, Justificativas, Cargos)
>>>>>>> 6d78c716439a5aa5a8166507cdeea87fc9f15668
# ===============================================
TAREFAS_PADRAO = {
    "Welcome": [{'nome': "Contato Inicial Whatsapp/Grupo", 'tag': "Ação interna"}, {'nome': "Criar Banco de Dados", 'tag': "Ação interna"}, {'nome': "Criar Usuário do Proprietário", 'tag': "Ação interna"}, {'nome': "Reunião de Kick-Off", 'tag': "Reunião"}],
    "Estruturação de BD": [{'nome': "Configurar planos", 'tag': "Ação interna"}, {'nome': "Configurar modelo de contrato", 'tag': "Ação interna"}, {'nome': "Configurar logo da empresa", 'tag': "Ação interna"}, {'nome': "Convênio de cobrança", 'tag': "Ação interna"}, {'nome': "Nota Fiscal", 'tag': "Ação interna"}],
    "Importação de dados": [{'nome': "Jira de implantação de dados", 'tag': "Ação interna"}, {'nome': "Importação de cartões de crédito", 'tag': "Ação interna"}],
    "Módulo ADM": [{'nome': "Treinamento Operacional 1", 'tag': "Reunião"}, {'nome': "Treinamento Operacional 2", 'tag': "Reunião"}, {'nome': "Treinamento Gerencial", 'tag': "Reunião"}, {'nome': "WellHub", 'tag': "Ação interna"}, {'nome': "TotalPass", 'tag': "Ação interna"}, {'nome': "Pacto Flow", 'tag': "Reunião"}, {'nome': "Vendas Online", 'tag': "Reunião"}, {'nome': "Verificação de Importação", 'tag': "Reunião"}, {'nome': "Controle de acesso", 'tag': "Reunião"}, {'nome': "App Pacto", 'tag': "Reunião"}],
    "Módulo Treino": [{'nome': "Estrutural", 'tag': "Reunião"}, {'nome': "Operacional", 'tag': "Reunião"}, {'nome': "Agenda", 'tag': "Reunião"}, {'nome': "Treino Gerencial", 'tag': "Reunião"}, {'nome': "App Treino", 'tag': "Reunião"}, {'nome': "Avaliação Física", 'tag': "Reunião"}, {'nome': "Retira Fichas", 'tag': "Reunião"}],
    "Módulo CRM": [{'nome': "Estrutural", 'tag': "Reunião"}, {'nome': "Operacional", 'tag': "Reunião"}, {'nome': "Gerencial", 'tag': "Reunião"}, {'nome': "GymBot", 'tag': "Reunião"}, {'nome': "Conversas IA", 'tag': "Reunião"}],
    "Módulo Financeiro": [{'nome': "Financeiro Simplificado", 'tag': "Reunião"}, {'nome': "Financeiro Avançado", 'tag': "Reunião"}, {'nome': "FyPay", 'tag': "Reunião"}],
    "Conclusão": [{'nome': "Tira dúvidas", 'tag': "Reunião"}, {'nome': "Concluir processos internos", 'tag': "Ação interna"}]
}
JUSTIFICATIVAS_PARADA = ["Pausa solicitada pelo cliente", "Aguardando dados / material do cliente", "Cliente em viagem / Férias", "Aguardando pagamento / Questões financeiras", "Revisão interna de processos", "Outro (detalhar nos comentários da implantação)"]
CARGOS_RESPONSAVEL = ["Proprietário(a)", "Sócio(a)", "Gerente", "Coordenador(a)", "Analista de TI", "Financeiro", "Outro"]

# ===============================================
<<<<<<< HEAD
# FUNÇÕES DE BANCO DE DADOS (BILÍNGUES)
=======
# FUNÇÕES DE BANCO DE DADOS (ADAPTADAS PARA POSTGRESQL)
>>>>>>> 6d78c716439a5aa5a8166507cdeea87fc9f15668
# ===============================================

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        if not USE_SQLITE_LOCALLY and DATABASE_URL:
<<<<<<< HEAD
            try: db = g._database = psycopg2.connect(DATABASE_URL)
            except psycopg2.OperationalError as e: print(f"Erro ao conectar ao PostgreSQL: {e}"); raise e
        elif USE_SQLITE_LOCALLY:
            db = g._database = sqlite3.connect(LOCAL_SQLITE_DB)
            db.row_factory = sqlite3.Row
        else: raise Exception("DATABASE_URL não definida e fallback SQLite desativado.")
=======
            try:
                db = g._database = psycopg2.connect(DATABASE_URL)
            except psycopg2.OperationalError as e:
                print(f"Erro ao conectar ao PostgreSQL: {e}")
                raise e
        elif USE_SQLITE_LOCALLY:
            db = g._database = sqlite3.connect(LOCAL_SQLITE_DB)
            db.row_factory = sqlite3.Row
        else:
             raise Exception("DATABASE_URL não definida e fallback SQLite desativado.")
>>>>>>> 6d78c716439a5aa5a8166507cdeea87fc9f15668
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None: db.close()

def query_db(query, args=(), one=False):
    db = get_db()
    cur = None
    try:
<<<<<<< HEAD
        # Adapta placeholder para SQLite
        if isinstance(db, sqlite3.Connection): query = query.replace('%s', '?')
        
        if isinstance(db, psycopg2.extensions.connection): cur = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        elif isinstance(db, sqlite3.Connection): cur = db.cursor()
        else: raise Exception("Tipo de conexão de banco de dados desconhecido.")
        
        cur.execute(query, args)
        rv = cur.fetchall()
        cur.close()
        results = [dict(row) for row in rv]
        return (results[0] if results else None) if one else results
    except Exception as e:
        print(f"Erro query: {e}\nQuery: {query}\nArgs: {args}")
=======
        if isinstance(db, psycopg2.extensions.connection):
            cur = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
            cur.execute(query, args)
            rv = cur.fetchall()
            cur.close()
        elif isinstance(db, sqlite3.Connection):
            cur = db.cursor()
            if USE_SQLITE_LOCALLY: query = query.replace('%s', '?')
            cur.execute(query, args)
            rv = cur.fetchall()
            cur.close()
        else: raise Exception("Tipo de conexão de banco de dados desconhecido.")
        results = [dict(row) for row in rv]
        return (results[0] if results else None) if one else results
    except Exception as e:
        print(f"Erro ao executar query: {e}\nQuery: {query}\nArgs: {args}")
>>>>>>> 6d78c716439a5aa5a8166507cdeea87fc9f15668
        if cur: cur.close()
        raise e

def execute_db(command, args=()):
    db = get_db()
    cur = None
    returned_id = None
    try:
<<<<<<< HEAD
        if isinstance(db, sqlite3.Connection): command = command.replace('%s', '?')

        if isinstance(db, psycopg2.extensions.connection):
            cur = db.cursor()
            command_upper = command.strip().upper()
            needs_returning_id = command_upper.startswith("INSERT") and any(tbl in command_upper for tbl in ["INTO IMPLANTACOES", "INTO TAREFAS", "INTO COMENTARIOS", "INTO TIMELINE_LOG"])
=======
        if isinstance(db, psycopg2.extensions.connection):
            cur = db.cursor()
            command_upper = command.strip().upper()
            needs_returning_id = command_upper.startswith("INSERT") and \
                                 any(table in command_upper for table in ["INTO IMPLANTACOES", "INTO TAREFAS", "INTO COMENTARIOS", "INTO TIMELINE_LOG"])
>>>>>>> 6d78c716439a5aa5a8166507cdeea87fc9f15668
            if needs_returning_id and "RETURNING" not in command_upper:
                 command += " RETURNING id"
                 cur.execute(command, args)
                 returned_id = cur.fetchone()[0] if cur.rowcount > 0 else None
<<<<<<< HEAD
            else: cur.execute(command, args)
            db.commit(); cur.close()
        elif isinstance(db, sqlite3.Connection):
            cur = db.cursor(); cur.execute(command, args); returned_id = cur.lastrowid; db.commit(); cur.close()
        else: raise Exception("Tipo de conexão de banco de dados desconhecido.")
        return returned_id
    except Exception as e:
        print(f"Erro execute: {e}\nCmd: {command}\nArgs: {args}")
        if cur: cur.close()
        db.rollback(); raise e

def init_db():
    with app.app_context():
        db = get_db()
        cur = db.cursor()
        is_postgres = isinstance(db, psycopg2.extensions.connection)

        pk_type = "SERIAL PRIMARY KEY" if is_postgres else "INTEGER PRIMARY KEY AUTOINCREMENT"
        boolean_type = "BOOLEAN" if is_postgres else "INTEGER"
        timestamp_type = "TIMESTAMP" if is_postgres else "DATETIME"
        date_type = "DATE" if is_postgres else "TEXT"

        cur.execute(f"CREATE TABLE IF NOT EXISTS usuarios (usuario VARCHAR(255) PRIMARY KEY, senha TEXT NOT NULL)")
        cur.execute(f"CREATE TABLE IF NOT EXISTS perfil_usuario (usuario VARCHAR(255) PRIMARY KEY REFERENCES usuarios(usuario) ON DELETE CASCADE, nome TEXT, impl_andamento INTEGER DEFAULT 0, impl_finalizadas INTEGER DEFAULT 0, impl_paradas INTEGER DEFAULT 0, progresso_medio_carteira INTEGER DEFAULT 0, impl_andamento_total INTEGER DEFAULT 0, implantacoes_atrasadas INTEGER DEFAULT 0)")
        cur.execute(f"CREATE TABLE IF NOT EXISTS implantacoes (id {pk_type}, usuario_cs VARCHAR(255) NOT NULL REFERENCES usuarios(usuario) ON DELETE NO ACTION, nome_empresa TEXT NOT NULL, status VARCHAR(50) DEFAULT 'andamento', tipo VARCHAR(50) DEFAULT 'agora', data_criacao {timestamp_type} DEFAULT CURRENT_TIMESTAMP, data_finalizacao {timestamp_type}, motivo_parada TEXT DEFAULT '', responsavel_cliente TEXT DEFAULT '', cargo_responsavel TEXT DEFAULT '', telefone_responsavel VARCHAR(50) DEFAULT '', email_responsavel VARCHAR(255) DEFAULT '', data_inicio_producao {date_type} DEFAULT NULL, data_final_implantacao {date_type} DEFAULT NULL, chave_oamd TEXT DEFAULT '', catraca TEXT DEFAULT '', facial TEXT DEFAULT '')")
        cur.execute(f"CREATE TABLE IF NOT EXISTS tarefas (id {pk_type}, implantacao_id INTEGER NOT NULL REFERENCES implantacoes(id) ON DELETE CASCADE, tarefa_pai TEXT NOT NULL, tarefa_filho TEXT NOT NULL, concluida {boolean_type} DEFAULT FALSE, ordem INTEGER DEFAULT 0, tag VARCHAR(100) DEFAULT '')")
        cur.execute(f"CREATE TABLE IF NOT EXISTS comentarios (id {pk_type}, tarefa_id INTEGER NOT NULL REFERENCES tarefas(id) ON DELETE CASCADE, usuario_cs VARCHAR(255) NOT NULL REFERENCES usuarios(usuario) ON DELETE NO ACTION, texto TEXT NOT NULL, data_criacao {timestamp_type} DEFAULT CURRENT_TIMESTAMP, imagem_url TEXT DEFAULT NULL)")
        cur.execute(f"CREATE TABLE IF NOT EXISTS timeline_log (id {pk_type}, implantacao_id INTEGER NOT NULL REFERENCES implantacoes(id) ON DELETE CASCADE, usuario_cs VARCHAR(255) NOT NULL REFERENCES usuarios(usuario) ON DELETE NO ACTION, tipo_evento VARCHAR(100) NOT NULL, detalhes TEXT NOT NULL, data_criacao {timestamp_type} DEFAULT CURRENT_TIMESTAMP)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_tarefas_implantacao_id ON tarefas (implantacao_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_comentarios_tarefa_id ON comentarios (tarefa_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_timeline_log_implantacao_id ON timeline_log (implantacao_id)")
        db.commit(); cur.close()
        print("Schema DB verificado/inicializado.")

# ===============================================
# FUNÇÕES DE LÓGICA
# ===============================================
def format_date_br(dt_obj, include_time=False):
    # [CORREÇÃO] A checagem isinstance agora tem `datetime` e `date`
    if not dt_obj or not isinstance(dt_obj, (datetime, date)):
        if isinstance(dt_obj, str) and '-' in dt_obj:
             try: dt_obj = datetime.strptime(dt_obj.split(' ')[0], '%Y-%m-%d').date()
             except ValueError: return 'N/A'
        else: return 'N/A'
    fmt = '%d/%m/%Y %H:%M:%S' if include_time and isinstance(dt_obj, datetime) else '%d/%m/%Y'
    return dt_obj.strftime(fmt)

def format_date_iso_for_json(dt_obj):
    if not dt_obj or not isinstance(dt_obj, (datetime, date)): return None
    if isinstance(dt_obj, date) and not isinstance(dt_obj, datetime):
        dt_obj = datetime.combine(dt_obj, datetime.min.time())
    return dt_obj.strftime('%Y-%m-%d %H:%M:%S')
=======
            else:
                 cur.execute(command, args)
            db.commit()
            cur.close()
        elif isinstance(db, sqlite3.Connection):
            cur = db.cursor()
            if USE_SQLITE_LOCALLY: command = command.replace('%s', '?')
            cur.execute(command, args)
            returned_id = cur.lastrowid
            db.commit()
            cur.close()
        else: raise Exception("Tipo de conexão de banco de dados desconhecido.")
        return returned_id
    except Exception as e:
        print(f"Erro ao executar comando: {e}\nComando: {command}\nArgs: {args}")
        if cur: cur.close()
        db.rollback()
        raise e

def init_db():
    db = get_db()
    cur = db.cursor()
    # Criação das tabelas (com sintaxe PostgreSQL)
    cur.execute("CREATE TABLE IF NOT EXISTS usuarios (usuario VARCHAR(255) PRIMARY KEY, senha TEXT NOT NULL)")
    cur.execute("""CREATE TABLE IF NOT EXISTS perfil_usuario (usuario VARCHAR(255) PRIMARY KEY REFERENCES usuarios(usuario) ON DELETE CASCADE, nome TEXT, impl_andamento INTEGER DEFAULT 0, impl_finalizadas INTEGER DEFAULT 0, impl_paradas INTEGER DEFAULT 0, progresso_medio_carteira INTEGER DEFAULT 0, impl_andamento_total INTEGER DEFAULT 0, implantacoes_atrasadas INTEGER DEFAULT 0)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS implantacoes (id SERIAL PRIMARY KEY, usuario_cs VARCHAR(255) NOT NULL REFERENCES usuarios(usuario) ON DELETE NO ACTION, nome_empresa TEXT NOT NULL, status VARCHAR(50) DEFAULT 'andamento', tipo VARCHAR(50) DEFAULT 'agora', data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP, data_finalizacao TIMESTAMP, motivo_parada TEXT DEFAULT '', responsavel_cliente TEXT DEFAULT '', cargo_responsavel TEXT DEFAULT '', telefone_responsavel VARCHAR(50) DEFAULT '', email_responsavel VARCHAR(255) DEFAULT '', data_inicio_producao DATE DEFAULT NULL, data_final_implantacao DATE DEFAULT NULL, chave_oamd TEXT DEFAULT '', catraca TEXT DEFAULT '', facial TEXT DEFAULT '')""")
    cur.execute("""CREATE TABLE IF NOT EXISTS tarefas (id SERIAL PRIMARY KEY, implantacao_id INTEGER NOT NULL REFERENCES implantacoes(id) ON DELETE CASCADE, tarefa_pai TEXT NOT NULL, tarefa_filho TEXT NOT NULL, concluida BOOLEAN DEFAULT FALSE, ordem INTEGER DEFAULT 0, tag VARCHAR(100) DEFAULT '')""")
    cur.execute("""CREATE TABLE IF NOT EXISTS comentarios (id SERIAL PRIMARY KEY, tarefa_id INTEGER NOT NULL REFERENCES tarefas(id) ON DELETE CASCADE, usuario_cs VARCHAR(255) NOT NULL REFERENCES usuarios(usuario) ON DELETE NO ACTION, texto TEXT NOT NULL, data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP, imagem_url TEXT DEFAULT NULL)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS timeline_log (id SERIAL PRIMARY KEY, implantacao_id INTEGER NOT NULL REFERENCES implantacoes(id) ON DELETE CASCADE, usuario_cs VARCHAR(255) NOT NULL REFERENCES usuarios(usuario) ON DELETE NO ACTION, tipo_evento VARCHAR(100) NOT NULL, detalhes TEXT NOT NULL, data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    # Criação de índices
    cur.execute("CREATE INDEX IF NOT EXISTS idx_tarefas_implantacao_id ON tarefas (implantacao_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_comentarios_tarefa_id ON comentarios (tarefa_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_timeline_log_implantacao_id ON timeline_log (implantacao_id)")
    db.commit()
    cur.close()
    print("Schema do banco de dados verificado/inicializado.")

# ===============================================
# FUNÇÕES DE LÓGICA (ADAPTADAS)
# ===============================================
>>>>>>> 6d78c716439a5aa5a8166507cdeea87fc9f15668

def logar_timeline(implantacao_id, usuario_cs, tipo_evento, detalhes):
    try:
        query = "INSERT INTO timeline_log (implantacao_id, usuario_cs, tipo_evento, detalhes, data_criacao) VALUES (%s, %s, %s, %s, %s)"
        execute_db(query, (implantacao_id, usuario_cs, tipo_evento, detalhes, datetime.now()))
<<<<<<< HEAD
    except Exception as e:
        print(f"Erro ao logar timeline (id: {implantacao_id}): {e}")

def get_dashboard_data(usuario):
    db = get_db()
    is_postgres = isinstance(db, psycopg2.extensions.connection)

    if is_postgres:
        query = """WITH TaskProgress AS (SELECT implantacao_id, COUNT(*) AS total_tarefas, SUM(CASE WHEN concluida = TRUE THEN 1 ELSE 0 END) AS tarefas_concluidas FROM tarefas GROUP BY implantacao_id) SELECT i.*, EXTRACT(DAY FROM (NOW() - i.data_criacao)) AS dias_passados, COALESCE(tp.total_tarefas, 0) AS total, COALESCE(tp.tarefas_concluidas, 0) AS done FROM implantacoes i LEFT JOIN TaskProgress tp ON i.id = tp.implantacao_id WHERE i.usuario_cs = %s ORDER BY i.data_criacao DESC"""
        args = (usuario,)
    else: # SQLite
        query = """WITH TaskProgress AS (SELECT implantacao_id, COUNT(*) AS total_tarefas, SUM(CASE WHEN concluida = 1 THEN 1 ELSE 0 END) AS tarefas_concluidas FROM tarefas GROUP BY implantacao_id) SELECT i.*, julianday('now') - julianday(i.data_criacao) AS dias_passados, COALESCE(tp.total_tarefas, 0) AS total, COALESCE(tp.tarefas_concluidas, 0) AS done FROM implantacoes i LEFT JOIN TaskProgress tp ON i.id = tp.implantacao_id WHERE i.usuario_cs = ? ORDER BY i.data_criacao DESC"""
        args = (usuario,)
    
    implantacoes = query_db(query, args)
    
=======
    except Exception as e: print(f"Erro ao logar timeline (id: {implantacao_id}): {e}")

def get_dashboard_data(usuario):
    query = """
        WITH TaskProgress AS (SELECT implantacao_id, COUNT(*) AS total_tarefas, SUM(CASE WHEN concluida = TRUE THEN 1 ELSE 0 END) AS tarefas_concluidas FROM tarefas GROUP BY implantacao_id)
        SELECT i.*, EXTRACT(DAY FROM (NOW() - i.data_criacao)) AS dias_passados, COALESCE(tp.total_tarefas, 0) AS total, COALESCE(tp.tarefas_concluidas, 0) AS done
        FROM implantacoes i LEFT JOIN TaskProgress tp ON i.id = tp.implantacao_id
        WHERE i.usuario_cs = %s ORDER BY i.data_criacao DESC"""
    implantacoes = query_db(query, (usuario,))
>>>>>>> 6d78c716439a5aa5a8166507cdeea87fc9f15668
    data = {'andamento': [], 'futuras': [], 'finalizadas': [], 'paradas': [], 'atrasadas': []}
    metrics = {'impl_andamento_total': 0, 'implantacoes_futuras': 0, 'impl_finalizadas': 0, 'impl_paradas': 0, 'implantacoes_atrasadas': 0, 'progresso_total': 0, 'total_impl': 0}
    ids_atrasadas_contadas = set()
    for impl in implantacoes:
<<<<<<< HEAD
        impl['progresso'] = int(round((impl['done'] / impl['total']) * 100)) if impl['total'] > 0 else 0
        metrics['total_impl'] += 1; metrics['progresso_total'] += impl['progresso']
        dias_passados_num = float(impl.get('dias_passados', 0) or 0)
        
        # O SQLite retorna strings, o psycopg2 retorna objetos datetime. A função format_date_br lida com ambos
        impl['data_criacao_fmt'] = format_date_br(impl.get('data_criacao'))
        impl['data_finalizacao_fmt'] = format_date_br(impl.get('data_finalizacao'))
        impl['data_inicio_producao_fmt'] = format_date_br(impl.get('data_inicio_producao'))
        impl['data_final_implantacao_fmt'] = format_date_br(impl.get('data_final_implantacao'))

=======
        total, done = impl['total'], impl['done']
        impl['progresso'] = int(round((done / total) * 100)) if total > 0 else 0
        metrics['total_impl'] += 1
        metrics['progresso_total'] += impl['progresso']
        dias_passados_num = float(impl.get('dias_passados', 0) or 0)
        # Formata datas para exibição no template (DD/MM/AAAA)
        impl['data_criacao_fmt'] = impl['data_criacao'].strftime('%d/%m/%Y') if impl['data_criacao'] else 'N/A'
        impl['data_finalizacao_fmt'] = impl['data_finalizacao'].strftime('%d/%m/%Y') if impl['data_finalizacao'] else 'N/A'
        impl['data_inicio_producao_fmt'] = impl['data_inicio_producao'].strftime('%d/%m/%Y') if impl['data_inicio_producao'] else 'N/A'
        impl['data_final_implantacao_fmt'] = impl['data_final_implantacao'].strftime('%d/%m/%Y') if impl['data_final_implantacao'] else 'N/A'
        # Adiciona às listas apropriadas
>>>>>>> 6d78c716439a5aa5a8166507cdeea87fc9f15668
        if impl['tipo'] == 'futura': data['futuras'].append(impl); metrics['implantacoes_futuras'] += 1
        elif impl['status'] == 'andamento': data['andamento'].append(impl); metrics['impl_andamento_total'] += 1
        elif impl['status'] == 'finalizada': data['finalizadas'].append(impl); metrics['impl_finalizadas'] += 1
        elif impl['status'] == 'parada': data['paradas'].append(impl); metrics['impl_paradas'] += 1
<<<<<<< HEAD
=======
        # Lógica de atrasadas
>>>>>>> 6d78c716439a5aa5a8166507cdeea87fc9f15668
        if impl['status'] in ('andamento', 'parada') and dias_passados_num > 25:
            if not any(d['id'] == impl['id'] for d in data['atrasadas']): data['atrasadas'].append(impl)
            if impl['id'] not in ids_atrasadas_contadas: metrics['implantacoes_atrasadas'] += 1; ids_atrasadas_contadas.add(impl['id'])
    metrics['progresso_medio_carteira'] = int(round(metrics['progresso_total'] / metrics['total_impl'])) if metrics['total_impl'] > 0 else 0
    return data, metrics

<<<<<<< HEAD
# ... (Restante do código, incluindo todas as rotas, está completo e correto abaixo)
# ...
def auto_finalizar_implantacao(impl_id, usuario_cs):
    implantacao = query_db("SELECT status, tipo FROM implantacoes WHERE id = %s", (impl_id,), one=True)
    if not implantacao or implantacao['tipo'] == 'futura' or implantacao['status'] == 'finalizada': return False, None
    counts = query_db("SELECT COUNT(*) as total, SUM(CASE WHEN concluida THEN 1 ELSE 0 END) as done FROM tarefas WHERE implantacao_id = %s", (impl_id,), one=True)
    total_tarefas, tarefas_concluidas = counts['total'] or 0, counts['done'] or 0
=======
def auto_finalizar_implantacao(impl_id, usuario_cs):
    implantacao = query_db("SELECT status, tipo FROM implantacoes WHERE id = %s", (impl_id,), one=True)
    if not implantacao or implantacao['tipo'] == 'futura' or implantacao['status'] == 'finalizada': return False, None
    counts = query_db("SELECT COUNT(*) as total, SUM(CASE WHEN concluida = TRUE THEN 1 ELSE 0 END) as done FROM tarefas WHERE implantacao_id = %s", (impl_id,), one=True)
    total_tarefas, tarefas_concluidas = counts['total'] or 0, counts['done'] or 0
    log_finalizacao_dict = None
>>>>>>> 6d78c716439a5aa5a8166507cdeea87fc9f15668
    if total_tarefas > 0 and total_tarefas == tarefas_concluidas:
        try:
            execute_db("UPDATE implantacoes SET status = 'finalizada', data_finalizacao = CURRENT_TIMESTAMP WHERE id = %s", (impl_id,))
            execute_db("UPDATE perfil_usuario SET impl_finalizadas = impl_finalizadas + 1, impl_andamento_total = GREATEST(0, impl_andamento_total - 1) WHERE usuario = %s", (usuario_cs,))
<<<<<<< HEAD
            logar_timeline(impl_id, usuario_cs, 'status_alterado', 'Implantação finalizada automaticamente.')
            perfil = query_db("SELECT nome FROM perfil_usuario WHERE usuario = %s", (usuario_cs,), one=True)
            nome = perfil['nome'] if perfil else usuario_cs
            log_finalizacao = query_db("SELECT *, %s as usuario_nome FROM timeline_log WHERE implantacao_id = %s AND tipo_evento = 'status_alterado' ORDER BY id DESC LIMIT 1", (nome, impl_id), one=True)
            if log_finalizacao: log_finalizacao['data_criacao'] = format_date_iso_for_json(log_finalizacao.get('data_criacao'))
            return True, log_finalizacao
        except Exception as e: print(f"Erro auto-finalizar: {e}"); return False, None
    return False, None

# ===============================================
# ROTAS
=======
            log_detalhes = 'Implantação finalizada automaticamente (100% das tarefas concluídas).'
            logar_timeline(impl_id, usuario_cs, 'status_alterado', log_detalhes)
            perfil_usuario = query_db("SELECT nome FROM perfil_usuario WHERE usuario = %s", (usuario_cs,), one=True)
            nome_usuario = perfil_usuario['nome'] if perfil_usuario else usuario_cs
            log_finalizacao = query_db("SELECT *, %s as usuario_nome FROM timeline_log WHERE implantacao_id = %s AND tipo_evento = 'status_alterado' AND detalhes = %s ORDER BY id DESC LIMIT 1", (nome_usuario, impl_id, log_detalhes), one=True)
            if log_finalizacao and log_finalizacao.get('data_criacao'):
                log_finalizacao['data_criacao_str'] = log_finalizacao['data_criacao'].strftime('%Y-%m-%d %H:%M:%S') # Formato para JSON
            log_finalizacao_dict = log_finalizacao
            return True, log_finalizacao_dict
        except Exception as e:
            print(f"Erro ao auto-finalizar implantação: {e}")
            return False, None
    return False, None

# ===============================================
# ROTAS (ADAPTADAS E COM FORMATAÇÃO DE DATA PARA TEMPLATE)
>>>>>>> 6d78c716439a5aa5a8166507cdeea87fc9f15668
# ===============================================
@app.route('/')
def home():
    if 'usuario' in session: return redirect(url_for('dashboard'))
    return redirect(url_for('login_cadastro'))

@app.route('/dashboard')
def dashboard():
    if 'usuario' not in session: return redirect(url_for('login_cadastro'))
    usuario = session['usuario']
<<<<<<< HEAD
    dashboard_data, metrics = get_dashboard_data(usuario)
=======
    dashboard_data, metrics = get_dashboard_data(usuario) # get_dashboard_data já formata as datas necessárias
>>>>>>> 6d78c716439a5aa5a8166507cdeea87fc9f15668
    perfil = query_db("SELECT * FROM perfil_usuario WHERE usuario = %s", (usuario,), one=True)
    perfil_data = perfil if perfil else {}
    default_metrics = {'nome': usuario, 'impl_andamento': 0, 'impl_finalizadas': 0, 'impl_paradas': 0, 'progresso_medio_carteira': 0, 'impl_andamento_total': 0, 'implantacoes_atrasadas': 0, 'implantacoes_futuras': 0}
    final_metrics = {**default_metrics, **perfil_data, **metrics}
<<<<<<< HEAD
    return render_template('dashboard.html', usuario=usuario, metrics=final_metrics, **dashboard_data, cargos_responsavel=CARGOS_RESPONSAVEL)

@app.route('/login', methods=['GET', 'POST'])
def login_cadastro():
    if request.method == 'POST':
        usuario = request.form['usuario'].strip(); senha = request.form['senha']; action = request.form.get('action', 'login')
        if action == 'login':
            user_data = query_db("SELECT senha FROM usuarios WHERE usuario = %s", (usuario,), one=True)
            if not user_data or not check_password_hash(user_data['senha'], senha):
                return render_template('login.html', aba_ativa='login', error="Usuário ou senha inválidos.")
=======
    return render_template('dashboard.html', usuario=usuario, metrics=final_metrics,
                           implantacoes_andamento=dashboard_data['andamento'], implantacoes_futuras=dashboard_data['futuras'],
                           implantacoes_finalizadas=dashboard_data['finalizadas'], implantacoes_paradas=dashboard_data['paradas'],
                           implantacoes_atrasadas=dashboard_data['atrasadas'], cargos_responsavel=CARGOS_RESPONSAVEL)

@app.route('/login', methods=['GET', 'POST'])
def login_cadastro():
    # ... (lógica de login/cadastro adaptada - sem mudanças de data aqui) ...
    if request.method == 'POST':
        usuario = request.form['usuario'].strip()
        senha = request.form['senha']
        action = request.form.get('action', 'login')
        if action == 'login':
            user_data = query_db("SELECT senha FROM usuarios WHERE usuario = %s", (usuario,), one=True)
            if not user_data or not check_password_hash(user_data['senha'], senha):
                error_msg = "Senha incorreta." if user_data else "Usuário não encontrado."
                return render_template('login.html', aba_ativa='login', error=error_msg)
>>>>>>> 6d78c716439a5aa5a8166507cdeea87fc9f15668
            session['usuario'] = usuario
            return redirect(url_for('dashboard'))
        elif action == 'cadastro':
            nome_completo = request.form.get('nome_completo', usuario).strip()
            if query_db("SELECT usuario FROM usuarios WHERE usuario = %s", (usuario,), one=True):
                return render_template('login.html', aba_ativa='cadastro', error="Usuário já existe.")
            if len(senha) < 6:
<<<<<<< HEAD
                return render_template('login.html', aba_ativa='cadastro', error="Senha deve ter no mínimo 6 caracteres.")
            try:
                execute_db("INSERT INTO usuarios (usuario, senha) VALUES (%s, %s)", (usuario, generate_password_hash(senha)))
=======
                 return render_template('login.html', aba_ativa='cadastro', error="Senha deve ter no mínimo 6 caracteres.")
            try:
                senha_hash = generate_password_hash(senha)
                execute_db("INSERT INTO usuarios (usuario, senha) VALUES (%s, %s)", (usuario, senha_hash))
>>>>>>> 6d78c716439a5aa5a8166507cdeea87fc9f15668
                execute_db("INSERT INTO perfil_usuario (usuario, nome) VALUES (%s, %s)", (usuario, nome_completo))
                session['usuario'] = usuario
                return redirect(url_for('dashboard'))
            except Exception as e:
<<<<<<< HEAD
                print(f"Erro cadastro: {e}")
                return render_template('login.html', aba_ativa='cadastro', error="Erro ao criar usuário.")
    return render_template('login.html', aba_ativa='login')

=======
                print(f"Erro ao cadastrar usuário: {e}")
                return render_template('login.html', aba_ativa='cadastro', error="Erro ao criar usuário. Tente novamente.")
    return render_template('login.html', aba_ativa='login')


>>>>>>> 6d78c716439a5aa5a8166507cdeea87fc9f15668
@app.route('/logout')
def logout():
    session.pop('usuario', None)
    return redirect(url_for('login_cadastro'))

@app.route('/criar_implantacao', methods=['POST'])
def criar_implantacao():
<<<<<<< HEAD
    if 'usuario' not in session: return redirect(url_for('login_cadastro'))
    usuario, nome_empresa, tipo = session['usuario'], request.form.get('nome_empresa', '').strip(), request.form.get('tipo', 'agora')
    if not nome_empresa:
        flash('Nome da empresa não pode estar vazio.', 'error')
        return redirect(url_for('dashboard'))
    try:
        implantacao_id = execute_db("INSERT INTO implantacoes (usuario_cs, nome_empresa, tipo, data_criacao) VALUES (%s, %s, %s, %s)", (usuario, nome_empresa, tipo, datetime.now()))
        if not implantacao_id:
            raise Exception("Falha ID implantação.")
        logar_timeline(implantacao_id, usuario, 'implantacao_criada', f'Implantação "{nome_empresa}" (Tipo: {tipo}) criada.')
        tasks_added = 0
        for pai, filhos in TAREFAS_PADRAO.items():
            for i, filho in enumerate(filhos, 1):
                execute_db("INSERT INTO tarefas (implantacao_id, tarefa_pai, tarefa_filho, ordem, tag) VALUES (%s, %s, %s, %s, %s)", (implantacao_id, pai, filho['nome'], i, filho.get('tag', '')))
                tasks_added += 1
        print(f"{tasks_added} tarefas padrão add p/ ID {implantacao_id}.")
        flash(f'Implantação "{nome_empresa}" criada!', 'success')
    except Exception as e:
        print(f"Erro criar impl: {e}")
        flash(f'Erro: {e}', 'error')
    return redirect(url_for('dashboard'))

# ... (outras rotas)
=======
    # ... (lógica adaptada - sem mudanças de data aqui) ...
    if 'usuario' not in session: return redirect(url_for('login_cadastro'))
    usuario, nome_empresa, tipo = session['usuario'], request.form.get('nome_empresa', '').strip(), request.form.get('tipo', 'agora')
    if not nome_empresa:
        flash('O nome da empresa não pode estar vazio.', 'error')
        return redirect(url_for('dashboard'))
    try:
        implantacao_id = execute_db("INSERT INTO implantacoes (usuario_cs, nome_empresa, tipo, data_criacao) VALUES (%s, %s, %s, %s)", (usuario, nome_empresa, tipo, datetime.now()))
        if not implantacao_id: raise Exception("Falha ao obter ID da implantação criada.")
        logar_timeline(implantacao_id, usuario, 'implantacao_criada', f'Implantação "{nome_empresa}" (Tipo: {tipo}) foi criada.')
        tasks_added_count = 0
        for tarefa_pai, tarefas_info in TAREFAS_PADRAO.items():
            for i, tarefa_info in enumerate(tarefas_info, 1):
                execute_db("INSERT INTO tarefas (implantacao_id, tarefa_pai, tarefa_filho, ordem, tag) VALUES (%s, %s, %s, %s, %s)",
                           (implantacao_id, tarefa_pai, tarefa_info['nome'], i, tarefa_info.get('tag', '')))
                tasks_added_count += 1
        print(f"{tasks_added_count} tarefas padrão adicionadas para implantação ID {implantacao_id}.")
        flash(f'Implantação "{nome_empresa}" criada com sucesso!', 'success')
    except Exception as e:
        print(f"Erro CRÍTICO ao criar implantação ou suas tarefas: {e}")
        flash(f'Erro ao criar implantação: {e}', 'error')
    return redirect(url_for('dashboard'))


@app.route('/iniciar_implantacao', methods=['POST'])
def iniciar_implantacao():
    # ... (lógica adaptada - sem mudanças de data aqui) ...
    if 'usuario' not in session: return redirect(url_for('login_cadastro'))
    implantacao_id = request.form.get('implantacao_id')
    if not implantacao_id: return redirect(url_for('dashboard'))
    row = query_db("SELECT usuario_cs, nome_empresa FROM implantacoes WHERE id = %s", (implantacao_id,), one=True)
    if not row or row['usuario_cs'] != session['usuario']:
        flash('Permissão negada ou implantação não encontrada.', 'error')
        return redirect(url_for('dashboard'))
    try:
        execute_db("UPDATE implantacoes SET tipo = 'agora', status = 'andamento', data_criacao = %s WHERE id = %s", (datetime.now(), implantacao_id))
        logar_timeline(implantacao_id, session['usuario'], 'status_alterado', f'Implantação "{row["nome_empresa"]}" iniciada (movida de "Futura" para "Em Andamento").')
        flash('Implantação iniciada!', 'success')
    except Exception as e:
        print(f"Erro ao iniciar implantação: {e}")
        flash('Erro ao iniciar implantação.', 'error')
    return redirect(url_for('ver_implantacao', impl_id=implantacao_id))

@app.route('/finalizar_implantacao', methods=['POST'])
def finalizar_implantacao():
    # ... (lógica adaptada - sem mudanças de data aqui) ...
    if 'usuario' not in session: return redirect(url_for('login_cadastro'))
    id_implantacao = request.form.get('implantacao_id')
    if not id_implantacao: return redirect(url_for('dashboard'))
    impl = query_db("SELECT status FROM implantacoes WHERE id = %s AND usuario_cs = %s", (id_implantacao, session['usuario']), one=True)
    if not impl:
         flash('Permissão negada ou implantação não encontrada.', 'error')
         return redirect(url_for('dashboard'))
    if impl['status'] != 'andamento':
         flash('Apenas implantações em andamento podem ser finalizadas.', 'warning')
         return redirect(url_for('dashboard'))
    try:
        execute_db("UPDATE implantacoes SET status = 'finalizada', data_finalizacao = CURRENT_TIMESTAMP WHERE id = %s AND usuario_cs = %s", (id_implantacao, session['usuario']))
        execute_db("UPDATE perfil_usuario SET impl_finalizadas = impl_finalizadas + 1, impl_andamento_total = GREATEST(0, impl_andamento_total - 1) WHERE usuario = %s", (session['usuario'],))
        logar_timeline(id_implantacao, session['usuario'], 'status_alterado', 'Implantação marcada como "Finalizada" manualmente.')
        flash('Implantação finalizada com sucesso!', 'success')
    except Exception as e:
        print(f"Erro ao finalizar implantação: {e}")
        flash('Erro ao finalizar implantação.', 'error')
    return redirect(url_for('dashboard'))

@app.route('/parar_implantacao', methods=['POST'])
def parar_implantacao():
    # ... (lógica adaptada - sem mudanças de data aqui) ...
    if 'usuario' not in session: return redirect(url_for('login_cadastro'))
    id_implantacao = request.form.get('implantacao_id')
    motivo = request.form.get('motivo_parada', '').strip()
    if not id_implantacao or not motivo:
         flash('ID da implantação ou motivo da parada faltando.', 'error')
         return redirect(url_for(request.referrer or 'dashboard'))
    impl = query_db("SELECT status FROM implantacoes WHERE id = %s AND usuario_cs = %s", (id_implantacao, session['usuario']), one=True)
    if not impl:
        flash('Permissão negada ou implantação não encontrada.', 'error')
        return redirect(url_for('dashboard'))
    if impl['status'] != 'andamento':
        flash('Apenas implantações em andamento podem ser paradas.', 'warning')
        return redirect(url_for('ver_implantacao', impl_id=id_implantacao))
    try:
        execute_db("UPDATE implantacoes SET status = 'parada', data_finalizacao = CURRENT_TIMESTAMP, motivo_parada = %s WHERE id = %s AND usuario_cs = %s", (motivo, id_implantacao, session['usuario']))
        execute_db("UPDATE perfil_usuario SET impl_paradas = impl_paradas + 1, impl_andamento_total = GREATEST(0, impl_andamento_total - 1) WHERE usuario = %s", (session['usuario'],))
        logar_timeline(id_implantacao, session['usuario'], 'status_alterado', f'Implantação marcada como "Parada". Motivo: {motivo}')
        flash('Implantação parada com sucesso.', 'success')
    except Exception as e:
        print(f"Erro ao parar implantação: {e}")
        flash('Erro ao parar implantação.', 'error')
    return redirect(url_for('ver_implantacao', impl_id=id_implantacao))

@app.route('/retomar_implantacao', methods=['POST'])
def retomar_implantacao():
    # ... (lógica adaptada - sem mudanças de data aqui) ...
    if 'usuario' not in session: return redirect(url_for('login_cadastro'))
    id_implantacao, redirect_to = request.form.get('implantacao_id'), request.form.get('redirect_to', 'dashboard')
    if not id_implantacao: return redirect(url_for('dashboard'))
    impl = query_db("SELECT status FROM implantacoes WHERE id = %s AND usuario_cs = %s", (id_implantacao, session['usuario']), one=True)
    if not impl:
        flash('Permissão negada ou implantação não encontrada.', 'error')
        return redirect(url_for('dashboard'))
    if impl['status'] != 'parada':
        flash('Apenas implantações paradas podem ser retomadas.', 'warning')
        redir_target = 'ver_implantacao' if redirect_to == 'detalhes' else 'dashboard'
        return redirect(url_for(redir_target, impl_id=id_implantacao if redir_target == 'ver_implantacao' else None))
    try:
        execute_db("UPDATE implantacoes SET status = 'andamento', data_finalizacao = NULL, motivo_parada = '' WHERE id = %s AND usuario_cs = %s", (id_implantacao, session['usuario']))
        execute_db("UPDATE perfil_usuario SET impl_paradas = GREATEST(0, impl_paradas - 1), impl_andamento_total = impl_andamento_total + 1 WHERE usuario = %s", (session['usuario'],))
        logar_timeline(id_implantacao, session['usuario'], 'status_alterado', 'Implantação retomada (status alterado de "Parada" para "Em Andamento").')
        flash('Implantação retomada com sucesso.', 'success')
    except Exception as e:
        print(f"Erro ao retomar implantação: {e}")
        flash('Erro ao retomar implantação.', 'error')
    redir_target = 'ver_implantacao' if redirect_to == 'detalhes' else 'dashboard'
    return redirect(url_for(redir_target, impl_id=id_implantacao if redir_target == 'ver_implantacao' else None))

@app.route('/atualizar_detalhes_empresa', methods=['POST'])
def atualizar_detalhes_empresa():
    # ... (lógica adaptada - sem mudanças de data aqui) ...
    if 'usuario' not in session: return redirect(url_for('login_cadastro'))
    implantacao_id, redirect_to = request.form.get('implantacao_id'), request.form.get('redirect_to', 'dashboard')
    if not query_db("SELECT id FROM implantacoes WHERE id = %s AND usuario_cs = %s", (implantacao_id, session['usuario']), one=True):
        flash('Você não tem permissão para editar esta implantação.', 'error')
        return redirect(url_for('dashboard'))
    try:
        data_inicio_prod = request.form.get('data_inicio_producao') or None
        data_final_impl = request.form.get('data_final_implantacao') or None
        query = """ UPDATE implantacoes SET responsavel_cliente = %s, cargo_responsavel = %s, telefone_responsavel = %s, email_responsavel = %s, data_inicio_producao = %s, data_final_implantacao = %s, chave_oamd = %s, catraca = %s, facial = %s WHERE id = %s AND usuario_cs = %s """
        args = (request.form.get('responsavel_cliente', '').strip(), request.form.get('cargo_responsavel', '').strip(), request.form.get('telefone_responsavel', '').strip(), request.form.get('email_responsavel', '').strip(), data_inicio_prod, data_final_impl, request.form.get('chave_oamd', '').strip(), request.form.get('catraca', '').strip(), request.form.get('facial', '').strip(), implantacao_id, session['usuario'])
        execute_db(query, args)
        logar_timeline(implantacao_id, session['usuario'], 'detalhes_alterados', 'Os detalhes da empresa foram atualizados.')
        flash('Detalhes da empresa atualizados com sucesso!', 'success')
    except Exception as e:
        print(f"Erro ao atualizar detalhes da empresa: {e}")
        flash('Erro ao atualizar detalhes.', 'error')
    redir_target = 'ver_implantacao' if redirect_to == 'detalhes' else 'dashboard'
    return redirect(url_for(redir_target, impl_id=implantacao_id if redir_target == 'ver_implantacao' else None))
>>>>>>> 6d78c716439a5aa5a8166507cdeea87fc9f15668

@app.route('/implantacao/<int:impl_id>')
def ver_implantacao(impl_id):
    if 'usuario' not in session: return redirect(url_for('login_cadastro'))
    usuario = session['usuario']
<<<<<<< HEAD

    implantacao = query_db("SELECT * FROM implantacoes WHERE id = %s AND usuario_cs = %s", (impl_id, usuario), one=True)
    if not implantacao:
        flash('Não encontrado/Acesso negado.', 'error')
        return redirect(url_for('dashboard'))

    # Formata datas BR para template
    implantacao['data_criacao_fmt_dt_hr'] = format_date_br(implantacao.get('data_criacao'), True)
    implantacao['data_criacao_fmt_d'] = format_date_br(implantacao.get('data_criacao'))
    implantacao['data_finalizacao_fmt_d'] = format_date_br(implantacao.get('data_finalizacao'))
    implantacao['data_inicio_producao_fmt_d'] = format_date_br(implantacao.get('data_inicio_producao'))
    implantacao['data_final_implantacao_fmt_d'] = format_date_br(implantacao.get('data_final_implantacao'))

    counts = query_db("SELECT COUNT(*) as total, SUM(CASE WHEN concluida THEN 1 ELSE 0 END) as done FROM tarefas WHERE implantacao_id = %s", (impl_id,), one=True)
    total_t, concl_t = counts['total'] or 0, counts['done'] or 0
    progresso = int(round((concl_t / total_t) * 100)) if total_t > 0 else 0
    tarefas_raw = query_db("SELECT * FROM tarefas WHERE implantacao_id = %s ORDER BY tarefa_pai, ordem", (impl_id,))
    comentarios_raw = query_db("SELECT c.*, p.nome as usuario_nome FROM comentarios c JOIN perfil_usuario p ON c.usuario_cs = p.usuario WHERE c.tarefa_id IN (SELECT id FROM tarefas WHERE implantacao_id = %s) ORDER BY c.data_criacao DESC", (impl_id,))
    for c in comentarios_raw:
        c['data_criacao_fmt_d'] = format_date_br(c.get('data_criacao'))
    comentarios_por_tarefa = {}
    for c in comentarios_raw:
        comentarios_por_tarefa.setdefault(c['tarefa_id'], []).append(c)
    temp = {}
    for t in tarefas_raw:
        t['comentarios'] = comentarios_por_tarefa.get(t['id'], [])
        temp.setdefault(t['tarefa_pai'], []).append(t)
    tarefas_agrupadas = OrderedDict((k, sorted(temp.pop(k), key=lambda x: x['ordem'])) for k in TAREFAS_PADRAO if k in temp)
    tarefas_agrupadas.update(OrderedDict(sorted(temp.items())))
    perfil = query_db("SELECT nome FROM perfil_usuario WHERE usuario = %s", (usuario,), one=True)
    nome_logado = perfil['nome'] if perfil else usuario
    logs_timeline = query_db("SELECT j.*, p.nome as usuario_nome FROM timeline_log j LEFT JOIN perfil_usuario p ON j.usuario_cs = p.usuario WHERE j.implantacao_id = %s ORDER BY j.data_criacao DESC", (impl_id,))
    for log in logs_timeline:
        log['data_criacao_fmt_dt_hr'] = format_date_br(log.get('data_criacao'), True)

    return render_template('implantacao_detalhes.html', implantacao=implantacao, tarefas_agrupadas=tarefas_agrupadas,
                           progresso_porcentagem=progresso, nome_usuario_logado=nome_logado, email_usuario_logado=usuario,
                           justificativas_parada=JUSTIFICATIVAS_PARADA, logs_timeline=logs_timeline,
                           cargos_responsavel=CARGOS_RESPONSAVEL)

# ... (Restante das rotas de ação, como toggle_tarefa, excluir_tarefa, etc., estão completas e corretas como na resposta anterior)
@app.route('/toggle_tarefa/<int:tarefa_id>', methods=['POST'])
def toggle_tarefa(tarefa_id):
    if 'usuario' not in session: return jsonify({'ok': False, 'error': 'login_required'}), 403
    tarefa = query_db("SELECT t.*, i.usuario_cs, i.id as implantacao_id FROM tarefas t JOIN implantacoes i ON t.implantacao_id = i.id WHERE t.id = %s", (tarefa_id,), one=True)
    if not tarefa or tarefa['usuario_cs'] != session['usuario']: return jsonify({'ok': False, 'error': 'forbidden'}), 403
    novo_status_bool, impl_id = not tarefa['concluida'], tarefa['implantacao_id']
    try:
        execute_db("UPDATE tarefas SET concluida = %s WHERE id = %s", (novo_status_bool, tarefa_id))
        agora_str_br = datetime.now().strftime('%d/%m/%Y %H:%M')
        detalhe = f"Atualização tarefa: {tarefa['tarefa_filho']}.\n{'Concluída: ' + agora_str_br if novo_status_bool else 'Status: Não Concluída.'}"
        logar_timeline(impl_id, session['usuario'], 'tarefa_alterada', detalhe)
        finalizada, log_finalizacao = auto_finalizar_implantacao(impl_id, session['usuario'])
        counts = query_db("SELECT COUNT(*) as total, SUM(CASE WHEN concluida THEN 1 ELSE 0 END) as done FROM tarefas WHERE implantacao_id = %s", (impl_id,), one=True)
        novo_prog = int(round((counts['done'] / counts['total']) * 100)) if counts['total'] > 0 else 0
        perfil = query_db("SELECT nome FROM perfil_usuario WHERE usuario = %s", (session['usuario'],), one=True)
        nome = perfil['nome'] if perfil else session['usuario']
        log_tarefa = query_db("SELECT *, %s as usuario_nome FROM timeline_log WHERE implantacao_id = %s AND tipo_evento = 'tarefa_alterada' ORDER BY id DESC LIMIT 1", (nome, impl_id), one=True)
        if log_tarefa: log_tarefa['data_criacao'] = format_date_iso_for_json(log_tarefa.get('data_criacao'))
        return jsonify({'ok': True, 'novo_status': 1 if novo_status_bool else 0, 'implantacao_finalizada': finalizada, 'novo_progresso': novo_prog, 'log_tarefa': log_tarefa, 'log_finalizacao': log_finalizacao})
    except Exception as e: print(f"Erro toggle tarefa: {e}"); return jsonify({'ok': False, 'error': str(e)}), 500
=======
    implantacao = query_db("SELECT * FROM implantacoes WHERE id = %s AND usuario_cs = %s", (impl_id, usuario), one=True)
    if not implantacao:
        flash('Implantação não encontrada ou acesso negado.', 'error')
        return redirect(url_for('dashboard'))

    # Formata datas para exibição no template (DD/MM/AAAA ou DD/MM/AAAA HH:MM:SS)
    implantacao['data_criacao_fmt_dt_hr'] = implantacao['data_criacao'].strftime('%d/%m/%Y %H:%M:%S') if implantacao.get('data_criacao') else 'N/A'
    implantacao['data_criacao_fmt_d'] = implantacao['data_criacao'].strftime('%d/%m/%Y') if implantacao.get('data_criacao') else 'N/A'
    implantacao['data_finalizacao_fmt_d'] = implantacao['data_finalizacao'].strftime('%d/%m/%Y') if implantacao.get('data_finalizacao') else 'N/A'
    # Campos data_inicio_producao e data_final_implantacao são DATE no DB, strftime funciona
    implantacao['data_inicio_producao_fmt_d'] = implantacao['data_inicio_producao'].strftime('%d/%m/%Y') if implantacao.get('data_inicio_producao') else 'N/A'
    implantacao['data_final_implantacao_fmt_d'] = implantacao['data_final_implantacao'].strftime('%d/%m/%Y') if implantacao.get('data_final_implantacao') else 'N/A'

    counts = query_db("SELECT COUNT(*) as total, SUM(CASE WHEN concluida = TRUE THEN 1 ELSE 0 END) as done FROM tarefas WHERE implantacao_id = %s", (impl_id,), one=True)
    total_tarefas, tarefas_concluidas = counts['total'] or 0, counts['done'] or 0
    progresso_porcentagem = int(round((tarefas_concluidas / total_tarefas) * 100)) if total_tarefas > 0 else 0
    tarefas_raw = query_db("SELECT * FROM tarefas WHERE implantacao_id = %s ORDER BY tarefa_pai, ordem", (impl_id,))
    comentarios_raw = query_db("SELECT c.*, p.nome as usuario_nome FROM comentarios c JOIN perfil_usuario p ON c.usuario_cs = p.usuario WHERE c.tarefa_id IN (SELECT id FROM tarefas WHERE implantacao_id = %s) ORDER BY c.data_criacao DESC", (impl_id,))
    # Formata data dos comentários para o template
    for c in comentarios_raw:
        c['data_criacao_fmt_d'] = c['data_criacao'].strftime('%d/%m/%Y') if c.get('data_criacao') else ''
    comentarios_por_tarefa = {}
    for c in comentarios_raw: comentarios_por_tarefa.setdefault(c['tarefa_id'], []).append(c)
    temp = {}
    for tarefa in tarefas_raw:
        tarefa['comentarios'] = comentarios_por_tarefa.get(tarefa['id'], [])
        temp.setdefault(tarefa['tarefa_pai'], []).append(tarefa)
    tarefas_agrupadas = OrderedDict((key, sorted(temp.pop(key), key=lambda x: x['ordem'])) for key in TAREFAS_PADRAO if key in temp)
    tarefas_agrupadas.update(OrderedDict(sorted(temp.items(), key=lambda item: item[0])))
    perfil_usuario = query_db("SELECT nome FROM perfil_usuario WHERE usuario = %s", (usuario,), one=True)
    nome_usuario_logado = perfil_usuario['nome'] if perfil_usuario else usuario
    logs_timeline = query_db("SELECT j.*, p.nome as usuario_nome FROM timeline_log j LEFT JOIN perfil_usuario p ON j.usuario_cs = p.usuario WHERE j.implantacao_id = %s ORDER BY j.data_criacao DESC", (impl_id,))
    # Formata data dos logs para o template
    for log in logs_timeline:
        log['data_criacao_fmt_dt_hr'] = log['data_criacao'].strftime('%d/%m/%Y %H:%M:%S') if log.get('data_criacao') else ''

    return render_template('implantacao_detalhes.html', implantacao=implantacao, tarefas_agrupadas=tarefas_agrupadas,
                           progresso_porcentagem=progresso_porcentagem, nome_usuario_logado=nome_usuario_logado,
                           email_usuario_logado=usuario, justificativas_parada=JUSTIFICATIVAS_PARADA, logs_timeline=logs_timeline)


@app.route('/toggle_tarefa/<int:tarefa_id>', methods=['POST'])
def toggle_tarefa(tarefa_id):
    if 'usuario' not in session: return jsonify({'ok': False, 'error': 'login_required'}), 403
    tarefa_info = query_db("SELECT t.*, i.usuario_cs, i.id as implantacao_id FROM tarefas t JOIN implantacoes i ON t.implantacao_id = i.id WHERE t.id = %s", (tarefa_id,), one=True)
    if not tarefa_info or tarefa_info['usuario_cs'] != session['usuario']: return jsonify({'ok': False, 'error': 'forbidden'}), 403
    novo_status_bool, impl_id = not tarefa_info['concluida'], tarefa_info['implantacao_id']
    try:
        execute_db("UPDATE tarefas SET concluida = %s WHERE id = %s", (novo_status_bool, tarefa_id))
        agora_str_br = datetime.now().strftime('%d/%m/%Y %H:%M') # Formato BR para o log
        detalhe_log = f"Atualização da tarefa: {tarefa_info['tarefa_filho']}.\n{'Concluída alterado(a) de: Sem valor para: ' + agora_str_br if novo_status_bool else 'Status alterado(a) de: Concluída para: Sem valor.'}"
        logar_timeline(impl_id, session['usuario'], 'tarefa_alterada', detalhe_log)
        finalizada, log_finalizacao_dict = auto_finalizar_implantacao(impl_id, session['usuario'])
        counts_after = query_db("SELECT COUNT(*) as total, SUM(CASE WHEN concluida = TRUE THEN 1 ELSE 0 END) as done FROM tarefas WHERE implantacao_id = %s", (impl_id,), one=True)
        total_after, concl_after = counts_after['total'] or 0, counts_after['done'] or 0
        novo_progresso = int(round((concl_after / total_after) * 100)) if total_after > 0 else 0
        perfil = query_db("SELECT nome FROM perfil_usuario WHERE usuario = %s", (session['usuario'],), one=True)
        nome_logado = perfil['nome'] if perfil else session['usuario']
        log_tarefa = query_db("SELECT *, %s as usuario_nome FROM timeline_log WHERE implantacao_id = %s AND tipo_evento = 'tarefa_alterada' ORDER BY id DESC LIMIT 1", (nome_logado, impl_id), one=True)
        # Formata datas para JSON (YYYY-MM-DD HH:MM:SS)
        if log_tarefa and log_tarefa.get('data_criacao'):
            log_tarefa['data_criacao'] = log_tarefa['data_criacao'].strftime('%Y-%m-%d %H:%M:%S')
        if log_finalizacao_dict and log_finalizacao_dict.get('data_criacao'):
             log_finalizacao_dict['data_criacao'] = log_finalizacao_dict['data_criacao'].strftime('%Y-%m-%d %H:%M:%S')

        return jsonify({'ok': True, 'novo_status': 1 if novo_status_bool else 0, 'implantacao_finalizada': finalizada,
                        'novo_progresso': novo_progresso, 'log_tarefa': log_tarefa, 'log_finalizacao': log_finalizacao_dict})
    except Exception as e:
        print(f"Erro ao alternar tarefa: {e}")
        return jsonify({'ok': False, 'error': str(e)}), 500
>>>>>>> 6d78c716439a5aa5a8166507cdeea87fc9f15668

@app.route('/excluir_tarefa/<int:tarefa_id>', methods=['POST'])
def excluir_tarefa(tarefa_id):
    if 'usuario' not in session: return jsonify({'ok': False, 'error': 'login_required'}), 403
    tarefa = query_db("SELECT t.implantacao_id, t.tarefa_filho, t.tarefa_pai, i.usuario_cs FROM tarefas t JOIN implantacoes i ON t.implantacao_id = i.id WHERE t.id = %s", (tarefa_id,), one=True)
    if not tarefa or tarefa['usuario_cs'] != session['usuario']: return jsonify({'ok': False, 'error': 'forbidden'}), 403
    implantacao_id = tarefa['implantacao_id']
    try:
<<<<<<< HEAD
        comentarios = query_db("SELECT id, imagem_url FROM comentarios WHERE tarefa_id = %s", (tarefa_id,))
        for c in comentarios:
            if c['imagem_url'] and not c['imagem_url'].startswith(('http:','https:')):
                try: fname=os.path.basename(c['imagem_url'].split('/')[-1]); fp=os.path.join(app.config['UPLOAD_FOLDER'],fname); os.remove(fp)
                except Exception as e: print(f"Erro excluir img local com {c['id']}: {e}")
        execute_db("DELETE FROM tarefas WHERE id = %s", (tarefa_id,))
        logar_timeline(implantacao_id, session['usuario'], 'tarefa_excluida', f"Tarefa '{tarefa['tarefa_filho']}' ({tarefa['tarefa_pai']}) excluída.")
        finalizada, log_finalizacao = auto_finalizar_implantacao(implantacao_id, session['usuario'])
        perfil = query_db("SELECT nome FROM perfil_usuario WHERE usuario = %s", (session['usuario'],), one=True)
        nome = perfil['nome'] if perfil else session['usuario']
        log_exclusao = query_db("SELECT *, %s as usuario_nome FROM timeline_log WHERE implantacao_id = %s AND tipo_evento = 'tarefa_excluida' ORDER BY id DESC LIMIT 1", (nome, implantacao_id), one=True)
        if log_exclusao: log_exclusao['data_criacao'] = format_date_iso_for_json(log_exclusao.get('data_criacao'))
        counts = query_db("SELECT COUNT(*) as total, SUM(CASE WHEN concluida THEN 1 ELSE 0 END) as done FROM tarefas WHERE implantacao_id = %s", (implantacao_id,), one=True)
        novo_prog = int(round((counts['done'] / counts['total']) * 100)) if counts['total'] > 0 else 0
        return jsonify({'ok': True, 'tarefa_id': tarefa_id, 'log_exclusao': log_exclusao, 'implantacao_finalizada': finalizada, 'log_finalizacao': log_finalizacao, 'novo_progresso': novo_prog})
    except Exception as e: print(f"Erro excluir tarefa: {e}"); return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/excluir_implantacao', methods=['POST'])
def excluir_implantacao():
    if 'usuario' not in session: flash('Login necessário.', 'error'); return redirect(url_for('login_cadastro'))
    impl_id = request.form.get('implantacao_id')
    if not impl_id: flash('ID inválido.', 'error'); return redirect(url_for('dashboard'))
    row = query_db("SELECT usuario_cs FROM implantacoes WHERE id = %s", (impl_id,), one=True)
    if not row or row['usuario_cs'] != session['usuario']: flash('Permissão negada.', 'error'); return redirect(url_for('dashboard'))
    try:
        comentarios_img = query_db("SELECT c.imagem_url FROM comentarios c JOIN tarefas t ON c.tarefa_id=t.id WHERE t.implantacao_id=%s AND c.imagem_url IS NOT NULL", (impl_id,))
        for c in comentarios_img:
            if c['imagem_url'] and not c['imagem_url'].startswith(('http:','https:')):
                try: fname=os.path.basename(c['imagem_url'].split('/')[-1]); fp=os.path.join(app.config['UPLOAD_FOLDER'],fname); os.remove(fp)
                except Exception as e: print(f"Erro excluir img local {c['imagem_url']}: {e}")
        execute_db("DELETE FROM implantacoes WHERE id = %s AND usuario_cs = %s", (impl_id, session['usuario']))
        flash('Implantação excluída.', 'success')
    except Exception as e: print(f"Erro excluir impl: {e}"); flash('Erro.', 'error')
=======
        comentarios_para_excluir = query_db("SELECT id, imagem_url FROM comentarios WHERE tarefa_id = %s", (tarefa_id,))
        for comm in comentarios_para_excluir:
             if comm['imagem_url'] and not comm['imagem_url'].startswith(('http://', 'https://')):
                try:
                    filename = os.path.basename(comm['imagem_url'].split('/')[-1])
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    if os.path.exists(filepath): os.remove(filepath)
                except Exception as e: print(f"Erro ao excluir imagem local do comentário {comm['id']}: {e}")
        execute_db("DELETE FROM tarefas WHERE id = %s", (tarefa_id,))
        detalhe_log = f"Tarefa '{tarefa['tarefa_filho']}' (do módulo '{tarefa['tarefa_pai']}') foi excluída."
        logar_timeline(implantacao_id, session['usuario'], 'tarefa_excluida', detalhe_log)
        finalizada, log_finalizacao_dict = auto_finalizar_implantacao(implantacao_id, session['usuario'])
        perfil = query_db("SELECT nome FROM perfil_usuario WHERE usuario = %s", (session['usuario'],), one=True)
        nome_usuario = perfil['nome'] if perfil else session['usuario']
        log_exclusao = query_db("SELECT *, %s as usuario_nome FROM timeline_log WHERE implantacao_id = %s AND tipo_evento = 'tarefa_excluida' ORDER BY id DESC LIMIT 1", (nome_usuario, implantacao_id), one=True)
        # Formata datas para JSON
        if log_exclusao and log_exclusao.get('data_criacao'):
             log_exclusao['data_criacao'] = log_exclusao['data_criacao'].strftime('%Y-%m-%d %H:%M:%S')
        if log_finalizacao_dict and log_finalizacao_dict.get('data_criacao'):
             log_finalizacao_dict['data_criacao'] = log_finalizacao_dict['data_criacao'].strftime('%Y-%m-%d %H:%M:%S')

        counts_after = query_db("SELECT COUNT(*) as total, SUM(CASE WHEN concluida = TRUE THEN 1 ELSE 0 END) as done FROM tarefas WHERE implantacao_id = %s", (implantacao_id,), one=True)
        total_after, concl_after = counts_after['total'] or 0, counts_after['done'] or 0
        novo_progresso = int(round((concl_after / total_after) * 100)) if total_after > 0 else 0
        return jsonify({'ok': True, 'tarefa_id': tarefa_id, 'log_exclusao': log_exclusao, 'implantacao_finalizada': finalizada, 'log_finalizacao': log_finalizacao_dict, 'novo_progresso': novo_progresso})
    except Exception as e:
        print(f"Erro ao excluir tarefa: {e}")
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/excluir_implantacao', methods=['POST'])
def excluir_implantacao():
    # ... (lógica adaptada, sem datas para formatar aqui) ...
    if 'usuario' not in session:
        flash('Faça login para continuar.', 'error')
        return redirect(url_for('login_cadastro'))
    implantacao_id = request.form.get('implantacao_id')
    if not implantacao_id:
        flash('ID da implantação inválido.', 'error')
        return redirect(url_for('dashboard'))
    row = query_db("SELECT usuario_cs FROM implantacoes WHERE id = %s", (implantacao_id,), one=True)
    if not row or row['usuario_cs'] != session['usuario']:
        flash('Permissão negada ou implantação não encontrada.', 'error')
        return redirect(url_for('dashboard'))
    try:
        comentarios_com_imagem = query_db("SELECT c.imagem_url FROM comentarios c JOIN tarefas t ON c.tarefa_id = t.id WHERE t.implantacao_id = %s AND c.imagem_url IS NOT NULL", (implantacao_id,))
        for comm in comentarios_com_imagem:
            if comm['imagem_url'] and not comm['imagem_url'].startswith(('http://', 'https://')):
                try:
                    filename = os.path.basename(comm['imagem_url'].split('/')[-1])
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    if os.path.exists(filepath): os.remove(filepath)
                except Exception as e: print(f"Erro ao excluir imagem local {comm['imagem_url']}: {e}")
        execute_db("DELETE FROM implantacoes WHERE id = %s AND usuario_cs = %s", (implantacao_id, session['usuario']))
        flash('Implantação excluída com sucesso.', 'success')
    except Exception as e:
        print(f"Erro ao excluir implantação: {e}")
        flash('Erro ao excluir implantação.', 'error')
>>>>>>> 6d78c716439a5aa5a8166507cdeea87fc9f15668
    return redirect(url_for('dashboard'))

@app.route('/adicionar_comentario/<int:tarefa_id>', methods=['POST'])
def adicionar_comentario(tarefa_id):
    if 'usuario' not in session: return jsonify({'ok': False, 'error': 'login_required'}), 403
<<<<<<< HEAD
    texto, img_url = request.form.get('comentario', '')[:8000].strip(), None
    if 'imagem' in request.files:
        file = request.files['imagem']
        if file and file.filename != '' and allowed_file(file.filename):
            try: fname=secure_filename(file.filename); base,ext=os.path.splitext(fname); nome_unico=f"{base}_{int(datetime.now().timestamp())}{ext}"; fp=os.path.join(app.config['UPLOAD_FOLDER'],nome_unico); file.save(fp); img_url=url_for('uploaded_file',filename=nome_unico,_external=False)
            except Exception as e: print(f"Erro salvar img local: {e}")
    if not texto and not img_url: return jsonify({'ok': False, 'error': 'vazio'}), 400
=======
    texto_comentario, imagem_url = request.form.get('comentario', '')[:8000].strip(), None
    if 'imagem' in request.files:
        file = request.files['imagem']
        if file and file.filename != '' and allowed_file(file.filename):
            try:
                filename = secure_filename(file.filename)
                nome_base, extensao = os.path.splitext(filename)
                nome_unico = f"{nome_base}_{int(datetime.now().timestamp())}{extensao}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], nome_unico)
                file.save(filepath)
                imagem_url = url_for('uploaded_file', filename=nome_unico, _external=False)
            except Exception as e: print(f"Erro ao salvar imagem local: {e}")
    if not texto_comentario and not imagem_url: return jsonify({'ok': False, 'error': 'comentario_vazio_e_sem_imagem'}), 400
>>>>>>> 6d78c716439a5aa5a8166507cdeea87fc9f15668
    tarefa = query_db("SELECT i.usuario_cs, i.id as implantacao_id, t.tarefa_filho FROM tarefas t JOIN implantacoes i ON t.implantacao_id = i.id WHERE t.id = %s", (tarefa_id,), one=True)
    if not tarefa or tarefa['usuario_cs'] != session['usuario']: return jsonify({'ok': False, 'error': 'forbidden'}), 403
    try:
        agora = datetime.now()
<<<<<<< HEAD
        novo_id = execute_db("INSERT INTO comentarios (tarefa_id, usuario_cs, texto, data_criacao, imagem_url) VALUES (%s, %s, %s, %s, %s)", (tarefa_id, session['usuario'], texto, agora, img_url))
        if not novo_id: raise Exception("Falha ID comentário.")
        detalhe = f"Novo comentário em '{tarefa['tarefa_filho']}':\n{texto}" if texto else f"Nova imagem em '{tarefa['tarefa_filho']}'."
        if texto and img_url: detalhe = f"Novo comentário em '{tarefa['tarefa_filho']}':\n{texto}\n[Imagem]"
        logar_timeline(tarefa['implantacao_id'], session['usuario'], 'novo_comentario', detalhe)
        perfil = query_db("SELECT nome FROM perfil_usuario WHERE usuario = %s", (session['usuario'],), one=True)
        nome = perfil['nome'] if perfil else session['usuario']
        log_com = query_db("SELECT *, %s as usuario_nome FROM timeline_log WHERE implantacao_id = %s AND tipo_evento = 'novo_comentario' ORDER BY id DESC LIMIT 1", (nome, tarefa['implantacao_id']), one=True)
        data_criacao_str = format_date_iso_for_json(agora)
        if log_com: log_com['data_criacao'] = format_date_iso_for_json(log_com.get('data_criacao'))
        return jsonify({'ok': True, 'comentario': {'id': novo_id, 'tarefa_id': tarefa_id, 'usuario_cs': session['usuario'], 'usuario_nome': nome, 'texto': texto, 'imagem_url': img_url, 'data_criacao': data_criacao_str }, 'log_comentario': log_com})
    except Exception as e: print(f"Erro add comentário: {e}"); return jsonify({'ok': False, 'error': str(e)}), 500
=======
        novo_comentario_id = execute_db("INSERT INTO comentarios (tarefa_id, usuario_cs, texto, data_criacao, imagem_url) VALUES (%s, %s, %s, %s, %s)", (tarefa_id, session['usuario'], texto_comentario, agora, imagem_url))
        if not novo_comentario_id: raise Exception("Falha ao obter ID do comentário criado.")
        detalhe_log = f"Novo comentário na tarefa '{tarefa['tarefa_filho']}':\n{texto_comentario}" if texto_comentario else f"Nova imagem adicionada à tarefa '{tarefa['tarefa_filho']}'."
        if texto_comentario and imagem_url: detalhe_log = f"Novo comentário na tarefa '{tarefa['tarefa_filho']}':\n{texto_comentario}\n[Imagem adicionada]"
        logar_timeline(tarefa['implantacao_id'], session['usuario'], 'novo_comentario', detalhe_log)
        perfil = query_db("SELECT nome FROM perfil_usuario WHERE usuario = %s", (session['usuario'],), one=True)
        nome_usuario = perfil['nome'] if perfil else session['usuario']
        log_comentario = query_db("SELECT *, %s as usuario_nome FROM timeline_log WHERE implantacao_id = %s AND tipo_evento = 'novo_comentario' ORDER BY id DESC LIMIT 1", (nome_usuario, tarefa['implantacao_id']), one=True)
        # Formata datas para JSON
        data_criacao_str = agora.strftime('%Y-%m-%d %H:%M:%S')
        if log_comentario and log_comentario.get('data_criacao'):
             log_comentario['data_criacao'] = log_comentario['data_criacao'].strftime('%Y-%m-%d %H:%M:%S')

        return jsonify({'ok': True, 'comentario': {'id': novo_comentario_id, 'tarefa_id': tarefa_id, 'usuario_cs': session['usuario'], 'usuario_nome': nome_usuario, 'texto': texto_comentario, 'imagem_url': imagem_url, 'data_criacao': data_criacao_str }, 'log_comentario': log_comentario})
    except Exception as e:
        print(f"Erro ao adicionar comentário: {e}")
        return jsonify({'ok': False, 'error': str(e)}), 500
>>>>>>> 6d78c716439a5aa5a8166507cdeea87fc9f15668

@app.route('/excluir_comentario/<int:comentario_id>', methods=['POST'])
def excluir_comentario(comentario_id):
    if 'usuario' not in session: return jsonify({'ok': False, 'error': 'login_required'}), 403
<<<<<<< HEAD
    com = query_db("SELECT c.*, t.implantacao_id, t.tarefa_filho FROM comentarios c JOIN tarefas t ON c.tarefa_id=t.id WHERE c.id=%s", (comentario_id,), one=True)
    if not com: return jsonify({'ok': False, 'error': 'not_found'}), 404
    if com['usuario_cs'] != session['usuario']: return jsonify({'ok': False, 'error': 'forbidden'}), 403
    try:
        if com['imagem_url'] and not com['imagem_url'].startswith(('http:','https:')):
            try: fname=os.path.basename(com['imagem_url'].split('/')[-1]); fp=os.path.join(app.config['UPLOAD_FOLDER'],fname); os.remove(fp)
            except Exception as e: print(f"Erro excluir img local com {com['id']}: {e}")
        execute_db("DELETE FROM comentarios WHERE id = %s", (comentario_id,))
        logar_timeline(com['implantacao_id'], session['usuario'], 'comentario_excluido', f"Comentário excluído de '{com['tarefa_filho']}': \"{com['texto'][:50]}...\"")
        perfil = query_db("SELECT nome FROM perfil_usuario WHERE usuario = %s", (session['usuario'],), one=True)
        nome = perfil['nome'] if perfil else session['usuario']
        log_exc = query_db("SELECT *, %s as usuario_nome FROM timeline_log WHERE implantacao_id=%s AND tipo_evento='comentario_excluido' ORDER BY id DESC LIMIT 1", (nome, com['implantacao_id']), one=True)
        if log_exc: log_exc['data_criacao'] = format_date_iso_for_json(log_exc.get('data_criacao'))
        return jsonify({'ok': True, 'log_exclusao': log_exc})
    except Exception as e: print(f"Erro excluir comentário: {e}"); return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/adicionar_tarefa', methods=['POST'])
def adicionar_tarefa(tarefa_id):
    if 'usuario' not in session: flash('Login necessário.', 'error'); return redirect(url_for('login_cadastro'))
    pai, filho, tag, impl_id = request.form.get('tarefa_pai','').strip(), request.form.get('tarefa_filho','').strip(), request.form.get('tarefa_tag','').strip(), request.form.get('implantacao_id')
    if not all([pai, filho, impl_id]): flash('Dados inválidos.', 'error'); return redirect(url_for(request.referrer or 'dashboard'))
    if not query_db("SELECT 1 FROM implantacoes WHERE id=%s AND usuario_cs=%s",(impl_id, session['usuario']), one=True): flash('Permissão negada.', 'error'); return redirect(url_for('dashboard'))
    try:
        max_o = query_db("SELECT MAX(ordem) as m FROM tarefas WHERE implantacao_id=%s AND tarefa_pai=%s", (impl_id, pai), one=True)
        ordem = (max_o['m'] or 0) + 1
        execute_db("INSERT INTO tarefas (implantacao_id, tarefa_pai, tarefa_filho, ordem, tag) VALUES (%s, %s, %s, %s, %s)", (impl_id, pai, filho, ordem, tag))
        logar_timeline(impl_id, session['usuario'], 'tarefa_adicionada', f"Tarefa '{filho}' ({tag or 'Sem tag'}) add ao módulo '{pai}'.")
        flash('Tarefa adicionada.', 'success')
    except Exception as e: print(f"Erro add tarefa: {e}"); flash('Erro.', 'error')
    return redirect(url_for('ver_implantacao', impl_id=impl_id))

@app.route('/reordenar_tarefas', methods=['POST'])
def reordenar_tarefas(tarefa_id):
    if 'usuario' not in session: return jsonify({'ok': False, 'error': 'login_required'}), 403
    data = request.get_json() or {}; impl_id, pai, ordem = data.get('implantacao_id'), data.get('tarefa_pai'), data.get('ordem', [])
    if not all([impl_id, pai, isinstance(ordem, list)]): return jsonify({'ok': False, 'error': 'payload'}), 400
    if not query_db("SELECT 1 FROM implantacoes WHERE id=%s AND usuario_cs=%s",(impl_id, session['usuario']), one=True): return jsonify({'ok': False, 'error': 'forbidden'}), 403
    try:
        for idx, t_id in enumerate(ordem, 1): execute_db("UPDATE tarefas SET ordem = %s WHERE id = %s AND implantacao_id = %s AND tarefa_pai = %s", (idx, t_id, impl_id, pai))
        logar_timeline(impl_id, session['usuario'], 'tarefa_reordenada', f"Tarefas do módulo '{pai}' reordenadas.")
        perfil = query_db("SELECT nome FROM perfil_usuario WHERE usuario = %s", (session['usuario'],), one=True)
        nome = perfil['nome'] if perfil else session['usuario']
        log_reord = query_db("SELECT *, %s as usuario_nome FROM timeline_log WHERE implantacao_id=%s AND tipo_evento='tarefa_reordenada' ORDER BY id DESC LIMIT 1", (nome, impl_id), one=True)
        if log_reord: log_reord['data_criacao'] = format_date_iso_for_json(log_reord.get('data_criacao'))
        return jsonify({'ok': True, 'log_reordenar': log_reord})
    except Exception as e: print(f"Erro reordenar: {e}"); return jsonify({'ok': False, 'error': str(e)}), 500

if __name__ == '__main__':
    # Este bloco só será executado se você rodar 'python app.py'
    # Útil para debug rápido localmente
    try:
        init_db()
    except Exception as e:
        print(f"ERRO CRÍTICO DURANTE init_db() local: {e}")
    app.run(debug=True, host='127.0.0.1', port=5000)

=======
    comentario = query_db("SELECT c.usuario_cs, c.texto, c.imagem_url, t.implantacao_id, t.tarefa_filho FROM comentarios c JOIN tarefas t ON c.tarefa_id = t.id WHERE c.id = %s", (comentario_id,), one=True)
    if not comentario: return jsonify({'ok': False, 'error': 'not_found'}), 404
    if comentario['usuario_cs'] != session['usuario']: return jsonify({'ok': False, 'error': 'forbidden'}), 403
    try:
        if comentario['imagem_url'] and not comentario['imagem_url'].startswith(('http://', 'https://')):
            try:
                filename = os.path.basename(comentario['imagem_url'].split('/')[-1])
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                if os.path.exists(filepath): os.remove(filepath); print(f"Arquivo de imagem local removido: {filepath}")
            except Exception as e: print(f"Erro ao excluir arquivo de imagem local: {e}")
        execute_db("DELETE FROM comentarios WHERE id = %s", (comentario_id,))
        detalhe_log = f"Comentário excluído da tarefa '{comentario['tarefa_filho']}': \"{comentario['texto'][:50]}...\""
        logar_timeline(comentario['implantacao_id'], session['usuario'], 'comentario_excluido', detalhe_log)
        perfil = query_db("SELECT nome FROM perfil_usuario WHERE usuario = %s", (session['usuario'],), one=True)
        nome_usuario = perfil['nome'] if perfil else session['usuario']
        log_exclusao = query_db("SELECT *, %s as usuario_nome FROM timeline_log WHERE implantacao_id = %s AND tipo_evento = 'comentario_excluido' ORDER BY id DESC LIMIT 1", (nome_usuario, comentario['implantacao_id']), one=True)
        # Formata data para JSON
        if log_exclusao and log_exclusao.get('data_criacao'):
             log_exclusao['data_criacao'] = log_exclusao['data_criacao'].strftime('%Y-%m-%d %H:%M:%S')
        return jsonify({'ok': True, 'log_exclusao': log_exclusao})
    except Exception as e:
        print(f"Erro ao excluir comentário: {e}")
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/adicionar_tarefa', methods=['POST'])
def adicionar_tarefa():
    # ... (lógica adaptada - sem datas para formatar aqui) ...
    if 'usuario' not in session:
        flash('Faça login para continuar.', 'error')
        return redirect(url_for('login_cadastro'))
    tarefa_pai, tarefa_filho, tarefa_tag, implantacao_id = request.form.get('tarefa_pai', '').strip(), request.form.get('tarefa_filho', '').strip(), request.form.get('tarefa_tag', '').strip(), request.form.get('implantacao_id')
    if not all([tarefa_pai, tarefa_filho, implantacao_id]):
        flash('Dados inválidos para adicionar tarefa.', 'error')
        return redirect(url_for(request.referrer or 'dashboard'))
    if not query_db("SELECT usuario_cs FROM implantacoes WHERE id = %s AND usuario_cs = %s", (implantacao_id, session['usuario']), one=True):
        flash('Permissão negada.', 'error')
        return redirect(url_for('dashboard'))
    try:
        max_row = query_db("SELECT MAX(ordem) as m FROM tarefas WHERE implantacao_id = %s AND tarefa_pai = %s", (implantacao_id, tarefa_pai), one=True)
        prox_ordem = (max_row['m'] or 0) + 1
        execute_db("INSERT INTO tarefas (implantacao_id, tarefa_pai, tarefa_filho, ordem, tag) VALUES (%s, %s, %s, %s, %s)", (implantacao_id, tarefa_pai, tarefa_filho, prox_ordem, tarefa_tag))
        detalhe_log = f"Tarefa personalizada '{tarefa_filho}' ({tarefa_tag or 'Sem tag'}) adicionada ao módulo '{tarefa_pai}'."
        logar_timeline(implantacao_id, session['usuario'], 'tarefa_adicionada', detalhe_log)
        flash('Tarefa adicionada com sucesso.', 'success')
    except Exception as e:
        print(f"Erro ao adicionar tarefa: {e}")
        flash('Erro ao adicionar tarefa.', 'error')
    return redirect(url_for('ver_implantacao', impl_id=implantacao_id))

@app.route('/reordenar_tarefas', methods=['POST'])
def reordenar_tarefas():
    if 'usuario' not in session: return jsonify({'ok': False, 'error': 'login_required'}), 403
    data = request.get_json() or {}
    implantacao_id, tarefa_pai, ordem_list = data.get('implantacao_id'), data.get('tarefa_pai'), data.get('ordem', [])
    if not all([implantacao_id, tarefa_pai, isinstance(ordem_list, list)]): return jsonify({'ok': False, 'error': 'invalid_payload'}), 400
    if not query_db("SELECT usuario_cs FROM implantacoes WHERE id = %s AND usuario_cs = %s", (implantacao_id, session['usuario']), one=True): return jsonify({'ok': False, 'error': 'forbidden'}), 403
    try:
        for idx, tarefa_id in enumerate(ordem_list, start=1):
            execute_db("UPDATE tarefas SET ordem = %s WHERE id = %s AND implantacao_id = %s AND tarefa_pai = %s", (idx, tarefa_id, implantacao_id, tarefa_pai))
        detalhe_log = f"Tarefas do módulo '{tarefa_pai}' foram reordenadas."
        logar_timeline(implantacao_id, session['usuario'], 'tarefa_reordenada', detalhe_log)
        perfil = query_db("SELECT nome FROM perfil_usuario WHERE usuario = %s", (session['usuario'],), one=True)
        nome_usuario = perfil['nome'] if perfil else session['usuario']
        log_reordenar = query_db("SELECT *, %s as usuario_nome FROM timeline_log WHERE implantacao_id = %s AND tipo_evento = 'tarefa_reordenada' ORDER BY id DESC LIMIT 1", (nome_usuario, implantacao_id), one=True)
        # Formata data para JSON
        if log_reordenar and log_reordenar.get('data_criacao'):
             log_reordenar['data_criacao'] = log_reordenar['data_criacao'].strftime('%Y-%m-%d %H:%M:%S')
        return jsonify({'ok': True, 'log_reordenar': log_reordenar})
    except Exception as e:
        print(f"Erro ao reordenar tarefas: {e}")
        return jsonify({'ok': False, 'error': str(e)}), 500
>>>>>>> 6d78c716439a5aa5a8166507cdeea87fc9f15668
