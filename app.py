import os
import sqlite3
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
from flask import (Flask, redirect, url_for, session, render_template, g, jsonify, request, flash, send_from_directory)
from authlib.integrations.flask_client import OAuth
from urllib.parse import urlencode, unquote # Import unquote
from functools import wraps
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename
from collections import OrderedDict
from datetime import datetime, date
import math
import time
from werkzeug.middleware.proxy_fix import ProxyFix

# --- Importações do Boto3 (AWS SDK / Cloudflare R2) ---
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
# --- FIM: Importações ---

load_dotenv() # Carrega variáveis do .env

# --- CONFIGURAÇÃO INICIAL E AUTHLIB ---
app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

app.secret_key = os.environ.get("FLASK_SECRET_KEY")
if not app.secret_key:
    raise ValueError("FLASK_SECRET_KEY não definida.")

# --- Configuração da Pasta de Upload LOCAL (Manter para fallback) ---
UPLOAD_FOLDER = os.path.join(app.root_path, 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# --- Configuração do Cloudflare R2 (usando boto3) ---
CLOUDFLARE_ENDPOINT_URL = os.environ.get('CLOUDFLARE_ENDPOINT_URL')
CLOUDFLARE_ACCESS_KEY_ID = os.environ.get('CLOUDFLARE_ACCESS_KEY_ID')
CLOUDFLARE_SECRET_ACCESS_KEY = os.environ.get('CLOUDFLARE_SECRET_ACCESS_KEY')
CLOUDFLARE_BUCKET_NAME = os.environ.get('CLOUDFLARE_BUCKET_NAME')
CLOUDFLARE_PUBLIC_URL = os.environ.get('CLOUDFLARE_PUBLIC_URL', '').rstrip('/') # Remove barra final se houver
# AWS_REGION é lido por boto3, mas 'auto' é geralmente ok para R2 com endpoint
AWS_REGION = os.environ.get('AWS_REGION', 'auto')

r2_client = None
if CLOUDFLARE_ENDPOINT_URL and CLOUDFLARE_ACCESS_KEY_ID and CLOUDFLARE_SECRET_ACCESS_KEY and CLOUDFLARE_BUCKET_NAME:
    try:
        r2_client = boto3.client(
            's3',
            endpoint_url=CLOUDFLARE_ENDPOINT_URL,
            aws_access_key_id=CLOUDFLARE_ACCESS_KEY_ID,
            aws_secret_access_key=CLOUDFLARE_SECRET_ACCESS_KEY,
            region_name=AWS_REGION # Pode ser 'auto' ou uma região válida
        )
        # Tenta listar buckets para verificar a conexão (opcional)
        r2_client.list_buckets()
        print(f"Cliente Boto3 R2 inicializado para o bucket '{CLOUDFLARE_BUCKET_NAME}' no endpoint '{CLOUDFLARE_ENDPOINT_URL}'.")
        if not CLOUDFLARE_PUBLIC_URL:
             print("AVISO: CLOUDFLARE_PUBLIC_URL não definida no .env. As URLs das imagens podem não funcionar.")
    except (ClientError, NoCredentialsError) as e:
        print(f"ERRO CRÍTICO ao inicializar cliente Boto3 R2: {e}")
        print("Verifique suas credenciais R2, endpoint e nome do bucket no .env")
        r2_client = None
    except Exception as e:
        print(f"ERRO INESPERADO ao inicializar Boto3 R2: {e}")
        r2_client = None
else:
    print("AVISO: Credenciais/Configuração Cloudflare R2 não encontradas nas variáveis de ambiente. Uploads para R2 desativados.")
# --- FIM: Configuração do R2 ---


oauth = OAuth(app)
# ... (Restante da configuração do Auth0 - INALTERADO) ...
auth0_domain = os.environ.get("AUTH0_DOMAIN")
auth0_client_id = os.environ.get("AUTH0_CLIENT_ID")
auth0_client_secret = os.environ.get("AUTH0_CLIENT_SECRET")
if not all([auth0_domain, auth0_client_id, auth0_client_secret]): raise ValueError("Credenciais Auth0 não definidas.")
auth0 = oauth.register('auth0', client_id=auth0_client_id, client_secret=auth0_client_secret, client_kwargs={'scope': 'openid profile email'}, server_metadata_url=f'https://{auth0_domain}/.well-known/openid-configuration')

# --- Configuração Banco de Dados (INALTERADO) ---
DATABASE_URL = os.environ.get('DATABASE_URL')
USE_SQLITE_LOCALLY = not DATABASE_URL
LOCAL_SQLITE_DB = 'dashboard_simples.db'

# --- Definições Globais (INALTERADO) ---
MODULO_OBRIGATORIO = "Obrigações para finalização"
CHECKLIST_OBRIGATORIO_ITEMS = [ "Fotos da unidade", "Propósito", "Descrição do Grupo", "Detalhes da Empresa", "Inicio em produção", "Documento", "Detalhes da Empresa no Dashboard", "Ticket catraca", "Atendimento OADM", "Módulo OAMD", "Plano de Sucesso", "Fechar grupo no WhatsApp" ]
MODULO_PENDENCIAS = "Pendências"
TAREFAS_TREINAMENTO_PADRAO = { "Welcome": [{'nome': "Contato Inicial Whatsapp/Grupo", 'tag': "Ação interna"}, {'nome': "Criar Banco de Dados", 'tag': "Ação interna"}, {'nome': "Criar Usuário do Proprietário", 'tag': "Ação interna"}, {'nome': "Reunião de Kick-Off", 'tag': "Reunião"}], "Estruturação de BD": [{'nome': "Configurar planos", 'tag': "Ação interna"}, {'nome': "Configurar modelo de contrato", 'tag': "Ação interna"}, {'nome': "Configurar logo da empresa", 'tag': "Ação interna"}, {'nome': "Convênio de cobrança", 'tag': "Ação interna"}, {'nome': "Nota Fiscal", 'tag': "Ação interna"}], "Importação de dados": [{'nome': "Jira de implantação de dados", 'tag': "Ação interna"}, {'nome': "Importação de cartões de crédito", 'tag': "Ação interna"}], "Módulo ADM": [{'nome': "Treinamento Operacional 1", 'tag': "Reunião"}, {'nome': "Treinamento Operacional 2", 'tag': "Reunião"}, {'nome': "Treinamento Gerencial", 'tag': "Reunião"}, {'nome': "WellHub", 'tag': "Ação interna"}, {'nome': "TotalPass", 'tag': "Ação interna"}, {'nome': "Pacto Flow", 'tag': "Reunião"}, {'nome': "Vendas Online", 'tag': "Reunião"}, {'nome': "Verificação de Importação", 'tag': "Reunião"}, {'nome': "Controle de acesso", 'tag': "Reunião"}, {'nome': "App Pacto", 'tag': "Reunião"}], "Módulo Treino": [{'nome': "Estrutural", 'tag': "Reunião"}, {'nome': "Operacional", 'tag': "Reunião"}, {'nome': "Agenda", 'tag': "Reunião"}, {'nome': "Treino Gerencial", 'tag': "Reunião"}, {'nome': "App Treino", 'tag': "Reunião"}, {'nome': "Avaliação Física", 'tag': "Reunião"}, {'nome': "Retira Fichas", 'tag': "Reunião"}], "Módulo CRM": [{'nome': "Estrutural", 'tag': "Reunião"}, {'nome': "Operacional", 'tag': "Reunião"}, {'nome': "Gerencial", 'tag': "Reunião"}, {'nome': "GymBot", 'tag': "Reunião"}, {'nome': "Conversas IA", 'tag': "Reunião"}], "Módulo Financeiro": [{'nome': "Financeiro Simplificado", 'tag': "Reunião"}, {'nome': "Financeiro Avançado", 'tag': "Reunião"}, {'nome': "FyPay", 'tag': "Reunião"}], "Conclusão": [{'nome': "Tira dúvidas", 'tag': "Reunião"}, {'nome': "Concluir processos internos", 'tag': "Ação interna"}] }
JUSTIFICATIVAS_PARADA = ["Pausa solicitada pelo cliente", "Aguardando dados / material do cliente", "Cliente em viagem / Férias", "Aguardando pagamento / Questões financeiras", "Revisão interna de processos", "Outro (detalhar nos comentários da implantação)"]
CARGOS_RESPONSAVEL = ["Proprietário(a)", "Sócio(a)", "Gerente", "Coordenador(a)", "Analista de TI", "Financeiro", "Outro"]
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
CARGOS_LIST = ["Júnior", "Pleno", "Sênior"]

# ----------------------------------------------------------------------
# --- Camada de Acesso a Dados (DAO) --- (INALTERADO) ---
# ----------------------------------------------------------------------
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        if not USE_SQLITE_LOCALLY and DATABASE_URL:
            db = g._database = psycopg2.connect(DATABASE_URL); print("Conectado ao PostgreSQL.")
        elif USE_SQLITE_LOCALLY:
            db = g._database = sqlite3.connect(LOCAL_SQLITE_DB); db.row_factory = sqlite3.Row; print(f"Conectado ao SQLite local: {LOCAL_SQLITE_DB}")
        else: raise Exception("Configuração de banco de dados inválida.")
    return db
@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None: db.close()
def _db_query(query, args=(), one=False):
    db = get_db(); cur = None
    try:
        is_postgres = isinstance(db, psycopg2.extensions.connection)
        if is_postgres: cur = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        else: query = query.replace('%s', '?'); cur = db.cursor()
        cur.execute(query, args); rv = cur.fetchall(); cur.close()
        if not is_postgres: rv = [dict(row) for row in rv]
        return (rv[0] if rv else None) if one else rv
    except Exception as e: print(f"ERRO ao executar SELECT: {e}\nQuery SQL: {query}\nArgumentos: {args}");  raise e # Removed redundant close
def _db_execute(command, args=()):
    db = get_db(); cur = None; returned_id = None
    try:
        is_postgres = isinstance(db, psycopg2.extensions.connection)
        if not is_postgres: command = command.replace('%s', '?')
        cur = db.cursor()
        if is_postgres:
            command_upper = command.strip().upper()
            needs_returning_id = command_upper.startswith("INSERT") and any(tbl in command_upper for tbl in ["INTO IMPLANTACOES", "INTO TAREFAS", "INTO COMENTARIOS", "INTO TIMELINE_LOG"])
            if needs_returning_id and "RETURNING" not in command_upper:
                command += " RETURNING id"; cur.execute(command, args); returned_id = cur.fetchone()[0] if cur.rowcount > 0 else None
            else: cur.execute(command, args)
        else: cur.execute(command, args); returned_id = cur.lastrowid
        db.commit(); cur.close(); return returned_id
    except Exception as e: print(f"ERRO ao executar comando: {e}\nComando SQL: {command}\nArgumentos: {args}"); db.rollback(); raise e # Removed redundant close
def query_db(query, args=(), one=False): return _db_query(query, args, one)
def execute_db(command, args=()): return _db_execute(command, args)

# ----------------------------------------------------------------------
# --- Funções Helper --- (INALTERADO) ---
# ----------------------------------------------------------------------
def _convert_to_date_or_datetime(dt_obj):
    if not dt_obj or not isinstance(dt_obj, str): return dt_obj
    original_str = dt_obj
    try:
        if ' ' in dt_obj or 'T' in dt_obj:
             dt_obj = dt_obj.replace('Z', '').split('+')[0].split('.')[0]
             for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%dT%H:%M:%S'):
                try: return datetime.strptime(dt_obj, fmt)
                except ValueError: continue
             return datetime.strptime(original_str.split()[0], '%Y-%m-%d').date()
        return datetime.strptime(dt_obj, '%Y-%m-%d').date()
    except Exception: return original_str
def format_date_br(dt_obj, include_time=False):
    if not dt_obj: return 'N/A'
    dt_obj = _convert_to_date_or_datetime(dt_obj)
    if not isinstance(dt_obj, (datetime, date)): return 'Data Inválida'
    output_fmt = '%d/%m/%Y %H:%M:%S' if include_time and isinstance(dt_obj, datetime) else '%d/%m/%Y'
    try: return dt_obj.strftime(output_fmt)
    except ValueError: return 'Data Inválida'
def format_date_iso_for_json(dt_obj, only_date=False):
    if not dt_obj: return None
    dt_obj = _convert_to_date_or_datetime(dt_obj)
    if not isinstance(dt_obj, (datetime, date)): return None
    if only_date: output_fmt = '%Y-%m-%d'
    else:
        if isinstance(dt_obj, date) and not isinstance(dt_obj, datetime): dt_obj = datetime.combine(dt_obj, datetime.min.time())
        output_fmt = '%Y-%m-%d %H:%M:%S'
    try: return dt_obj.strftime(output_fmt)
    except ValueError: return None
def allowed_file(filename): return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ----------------------------------------------------------------------
# --- Camada de Serviço (Business Logic) --- (INALTERADO) ---
# ----------------------------------------------------------------------
def logar_timeline(implantacao_id, usuario_cs, tipo_evento, detalhes):
    try: execute_db("INSERT INTO timeline_log (implantacao_id, usuario_cs, tipo_evento, detalhes) VALUES (%s, %s, %s, %s)", (implantacao_id, usuario_cs, tipo_evento, detalhes))
    except Exception as e: print(f"AVISO/ERRO: Falha ao logar evento '{tipo_evento}' para implantação {implantacao_id}: {e}")
def _create_default_tasks(impl_id):
    tasks_added = 0
    for i, tarefa_nome in enumerate(CHECKLIST_OBRIGATORIO_ITEMS, 1): execute_db("INSERT INTO tarefas (implantacao_id, tarefa_pai, tarefa_filho, ordem, tag) VALUES (%s, %s, %s, %s, %s)", (impl_id, MODULO_OBRIGATORIO, tarefa_nome, i, 'Ação interna')); tasks_added += 1
    for modulo, tarefas_info in TAREFAS_TREINAMENTO_PADRAO.items():
        for i, tarefa_info in enumerate(tarefas_info, 1): execute_db("INSERT INTO tarefas (implantacao_id, tarefa_pai, tarefa_filho, ordem, tag) VALUES (%s, %s, %s, %s, %s)", (impl_id, modulo, tarefa_info['nome'], i, tarefa_info.get('tag', ''))); tasks_added += 1
    return tasks_added
def _get_progress(impl_id):
    counts = query_db("SELECT COUNT(*) as total, SUM(CASE WHEN concluida THEN 1 ELSE 0 END) as done FROM tarefas WHERE implantacao_id = %s", (impl_id,), one=True); total, done = (counts.get('total') or 0), (counts.get('done') or 0); return int(round((done / total) * 100)) if total > 0 else 0, total, done
def auto_finalizar_implantacao(impl_id, usuario_cs_email):
    pending_tasks = query_db("SELECT COUNT(*) as total FROM tarefas WHERE implantacao_id = %s AND concluida = %s AND tarefa_pai != %s", (impl_id, 0, MODULO_PENDENCIAS), one=True)
    if pending_tasks and pending_tasks.get('total', 0) == 0:
        impl_status = query_db("SELECT status, nome_empresa FROM implantacoes WHERE id = %s", (impl_id,), one=True)
        if impl_status and impl_status.get('status') == 'andamento':
            execute_db("UPDATE implantacoes SET status = 'finalizada', data_finalizacao = CURRENT_TIMESTAMP WHERE id = %s", (impl_id,)); detalhe = f'Implantação "{impl_status.get("nome_empresa", "N/A")}" auto-finalizada.'; logar_timeline(impl_id, usuario_cs_email, 'auto_finalizada', detalhe); perfil = query_db("SELECT nome FROM perfil_usuario WHERE usuario = %s", (usuario_cs_email,), one=True); nome = perfil.get('nome') if perfil else usuario_cs_email; log_final = query_db("SELECT *, %s as usuario_nome FROM timeline_log WHERE implantacao_id = %s AND tipo_evento = 'auto_finalizada' ORDER BY id DESC LIMIT 1", (nome, impl_id), one=True)
            if log_final: log_final['data_criacao'] = format_date_iso_for_json(log_final.get('data_criacao')); return True, log_final
    return False, None
def get_dashboard_data(user_email):
    impl_list = query_db(""" SELECT *, CASE WHEN status = 'andamento' OR status = 'parada' THEN (CAST(strftime('%J', CURRENT_TIMESTAMP) AS REAL) - CAST(strftime('%J', data_criacao) AS REAL)) ELSE NULL END AS dias_passados FROM implantacoes WHERE usuario_cs = %s ORDER BY data_criacao DESC """, (user_email,))
    dashboard_data = {'andamento': [], 'atrasadas': [], 'futuras': [], 'finalizadas': [], 'paradas': []}; metrics = {'impl_andamento_total': 0, 'implantacoes_atrasadas': 0, 'implantacoes_futuras': 0, 'impl_finalizadas': 0, 'impl_paradas': 0}; all_tasks = query_db("SELECT implantacao_id, concluida FROM tarefas WHERE implantacao_id IN (SELECT id FROM implantacoes WHERE usuario_cs = %s)", (user_email,)); tasks_by_impl = {}; [tasks_by_impl.setdefault(task['implantacao_id'], []).append(task) for task in all_tasks]
    for impl in impl_list:
        impl_id = impl['id']; status = impl['status']; impl['data_criacao_iso'] = format_date_iso_for_json(impl.get('data_criacao'), only_date=True); impl['data_inicio_producao_iso'] = format_date_iso_for_json(impl.get('data_inicio_producao'), only_date=True); impl['data_final_implantacao_iso'] = format_date_iso_for_json(impl.get('data_final_implantacao'), only_date=True); total_tasks = len(tasks_by_impl.get(impl_id, [])); done_tasks = sum(1 for t in tasks_by_impl.get(impl_id, []) if t['concluida']); impl['progresso'] = int(round((done_tasks / total_tasks) * 100)) if total_tasks > 0 else 0
        if status == 'finalizada': dashboard_data['finalizadas'].append(impl); metrics['impl_finalizadas'] += 1
        elif status == 'parada': dashboard_data['paradas'].append(impl); metrics['impl_paradas'] += 1
        elif status == 'futura' or impl['tipo'] == 'futura': dashboard_data['futuras'].append(impl); metrics['implantacoes_futuras'] += 1
        else: dias_passados = int(float(impl.get('dias_passados', 0) or 0)); impl['dias_passados'] = dias_passados;
        if dias_passados > 25: dashboard_data['atrasadas'].append(impl); metrics['implantacoes_atrasadas'] += 1
        else: dashboard_data['andamento'].append(impl)
        metrics['impl_andamento_total'] += 1
    execute_db(""" UPDATE perfil_usuario SET impl_andamento_total = %s, implantacoes_atrasadas = %s, impl_finalizadas = %s, impl_paradas = %s WHERE usuario = %s """, (metrics['impl_andamento_total'], metrics['implantacoes_atrasadas'], metrics['impl_finalizadas'], metrics['impl_paradas'], user_email))
    return dashboard_data, metrics
def _sync_user_profile(user_email, user_name, auth0_user_id):
    try:
        perfil = query_db("SELECT nome FROM perfil_usuario WHERE usuario = %s", (user_email,), one=True)
        if not perfil:
            usuario_existente = query_db("SELECT usuario FROM usuarios WHERE usuario = %s", (user_email,), one=True)
            if not usuario_existente: senha_placeholder = generate_password_hash(auth0_user_id + app.secret_key); execute_db("INSERT INTO usuarios (usuario, senha) VALUES (%s, %s)", (user_email, senha_placeholder)); print(f"Registro criado: {user_email}.")
            execute_db("INSERT INTO perfil_usuario (usuario, nome) VALUES (%s, %s)", (user_email, user_name)); print(f"Perfil criado: {user_email}.")
            return True
        return False
    except Exception as db_error: print(f"ERRO sync usuário {user_email}: {db_error}"); flash("Erro ao sincronizar perfil.", "warning"); return False

# ----------------------------------------------------------------------
# --- Setup do DB --- (INALTERADO) ---
# ----------------------------------------------------------------------
def init_db():
    with app.app_context():
        db = get_db(); cur = db.cursor(); is_postgres = isinstance(db, psycopg2.extensions.connection); pk_type = "SERIAL PRIMARY KEY" if is_postgres else "INTEGER PRIMARY KEY AUTOINCREMENT"; boolean_type = "BOOLEAN" if is_postgres else "INTEGER"; timestamp_type = "TIMESTAMP WITH TIME ZONE" if is_postgres else "DATETIME"; date_type = "DATE" if is_postgres else "TEXT"
        cur.execute(f"CREATE TABLE IF NOT EXISTS usuarios (usuario VARCHAR(255) PRIMARY KEY, senha TEXT NOT NULL)")
        cur.execute(f""" CREATE TABLE IF NOT EXISTS perfil_usuario ( usuario VARCHAR(255) PRIMARY KEY REFERENCES usuarios(usuario) ON DELETE CASCADE, nome TEXT, impl_andamento INTEGER DEFAULT 0, impl_finalizadas INTEGER DEFAULT 0, impl_paradas INTEGER DEFAULT 0, progresso_medio_carteira INTEGER DEFAULT 0, impl_andamento_total INTEGER DEFAULT 0, implantacoes_atrasadas INTEGER DEFAULT 0, cargo TEXT, foto_url TEXT ) """)
        cur.execute(f""" CREATE TABLE IF NOT EXISTS implantacoes ( id {pk_type}, usuario_cs VARCHAR(255) NOT NULL REFERENCES usuarios(usuario) ON DELETE NO ACTION, nome_empresa TEXT NOT NULL, status VARCHAR(50) DEFAULT 'andamento' CHECK(status IN ('andamento', 'futura', 'finalizada', 'parada')), tipo VARCHAR(50) DEFAULT 'agora' CHECK(tipo IN ('agora', 'futura')), data_criacao {timestamp_type} DEFAULT CURRENT_TIMESTAMP, data_finalizacao {timestamp_type}, motivo_parada TEXT DEFAULT '', responsavel_cliente TEXT DEFAULT '', cargo_responsavel TEXT DEFAULT '', telefone_responsavel VARCHAR(50) DEFAULT '', email_responsavel VARCHAR(255) DEFAULT '', data_inicio_producao {date_type} DEFAULT NULL, data_final_implantacao {date_type} DEFAULT NULL, chave_oamd TEXT DEFAULT '', catraca TEXT DEFAULT '', facial TEXT DEFAULT '' ) """)
        cur.execute(f""" CREATE TABLE IF NOT EXISTS tarefas ( id {pk_type}, implantacao_id INTEGER NOT NULL REFERENCES implantacoes(id) ON DELETE CASCADE, tarefa_pai TEXT NOT NULL, tarefa_filho TEXT NOT NULL, concluida {boolean_type} DEFAULT FALSE, ordem INTEGER DEFAULT 0, tag VARCHAR(100) DEFAULT '' ) """)
        cur.execute(f""" CREATE TABLE IF NOT EXISTS comentarios ( id {pk_type}, tarefa_id INTEGER NOT NULL REFERENCES tarefas(id) ON DELETE CASCADE, usuario_cs VARCHAR(255) NOT NULL REFERENCES usuarios(usuario) ON DELETE NO ACTION, texto TEXT NOT NULL, data_criacao {timestamp_type} DEFAULT CURRENT_TIMESTAMP, imagem_url TEXT DEFAULT NULL ) """)
        cur.execute(f""" CREATE TABLE IF NOT EXISTS timeline_log ( id {pk_type}, implantacao_id INTEGER NOT NULL REFERENCES implantacoes(id) ON DELETE CASCADE, usuario_cs VARCHAR(255) NOT NULL REFERENCES usuarios(usuario) ON DELETE NO ACTION, tipo_evento VARCHAR(100) NOT NULL, detalhes TEXT NOT NULL, data_criacao {timestamp_type} DEFAULT CURRENT_TIMESTAMP ) """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_tarefas_implantacao_id ON tarefas (implantacao_id)"); cur.execute("CREATE INDEX IF NOT EXISTS idx_comentarios_tarefa_id ON comentarios (tarefa_id)"); cur.execute("CREATE INDEX IF NOT EXISTS idx_timeline_log_implantacao_id ON timeline_log (implantacao_id)")
        db.commit(); cur.close(); print("Schema DB verificado/inicializado.")

# ----------------------------------------------------------------------
# --- Decoradores e Rotas de Autenticação --- (INALTERADO) ---
# ----------------------------------------------------------------------
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session: flash('Login necessário.', 'info'); return redirect(url_for('login'))
        g.user = session.get('user'); g.user_email = g.user.get('email') if g.user else None
        if not g.user_email: flash("Sessão inválida.", "warning"); session.clear(); return redirect(url_for('logout'))
        g.perfil = query_db("SELECT * FROM perfil_usuario WHERE usuario = %s", (g.user_email,), one=True)
        if not g.perfil: g.perfil = {'nome': g.user.get('name', g.user_email), 'usuario': g.user_email, 'foto_url': None, 'cargo': None}
        return f(*args, **kwargs)
    return decorated_function
@app.route('/login')
def login():
    session.clear(); redirect_uri = url_for('callback', _external=True); return auth0.authorize_redirect(redirect_uri=redirect_uri)
@app.route('/callback')
def callback():
    try:
        token = auth0.authorize_access_token(); userinfo = token.get('userinfo')
        if not userinfo or not userinfo.get('email'): raise Exception("Info do usuário inválida.")
        session['user'] = userinfo; user_email = userinfo.get('email'); user_name = userinfo.get('name', user_email); auth0_user_id = userinfo.get('sub')
        _sync_user_profile(user_email, user_name, auth0_user_id)
        return redirect(url_for('dashboard'))
    except Exception as e: print(f"ERRO callback Auth0: {e}"); flash(f"Erro: {e}.", "error"); session.clear(); return redirect(url_for('home'))
@app.route('/logout')
def logout():
    session.clear(); params = {'returnTo': url_for('home', _external=True), 'client_id': auth0_client_id}; logout_url = f"https://{auth0_domain}/v2/logout?{urlencode(params)}"; return redirect(logout_url)

# ----------------------------------------------------------------------
# --- Rotas Principais ---
# ----------------------------------------------------------------------

@app.route('/uploads/<path:filename>') # Rota para uploads locais (fallback)
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/')
def home():
    if 'user' in session: return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    user_email = g.user_email; user_info = g.user
    try:
        dashboard_data, metrics = get_dashboard_data(user_email)
        perfil_data = g.perfil if g.perfil else {}
        default_metrics = {'nome': user_info.get('name', user_email), 'impl_andamento': 0, 'impl_finalizadas': 0, 'impl_paradas': 0, 'progresso_medio_carteira': 0, 'impl_andamento_total': 0, 'implantacoes_atrasadas': 0, 'implantacoes_futuras': 0}
        final_metrics = {**default_metrics, **perfil_data, **metrics}
        return render_template('dashboard.html', user_info=user_info, metrics=final_metrics,
                               implantacoes_andamento=dashboard_data.get('andamento', []), implantacoes_futuras=dashboard_data.get('futuras', []),
                               implantacoes_finalizadas=dashboard_data.get('finalizadas', []), implantacoes_paradas=dashboard_data.get('paradas', []),
                               implantacoes_atrasadas=dashboard_data.get('atrasadas', []), cargos_responsavel=CARGOS_RESPONSAVEL)
    except Exception as e:
        print(f"ERRO dashboard {user_email}: {e}"); flash("Erro ao carregar dados.", "error")
        return render_template('dashboard.html', user_info=user_info, metrics={}, implantacoes_andamento=[], implantacoes_futuras=[], implantacoes_finalizadas=[], implantacoes_paradas=[], implantacoes_atrasadas=[], cargos_responsavel=CARGOS_RESPONSAVEL, error="Falha.")

# --- ROTA /PERFIL MODIFICADA PARA R2 ---
@app.route('/perfil', methods=['GET', 'POST'])
@login_required
def perfil():
    usuario_cs_email = g.user_email
    if not r2_client or not CLOUDFLARE_PUBLIC_URL: # Verifica se R2 está configurado
        flash("Erro: Serviço de armazenamento R2 não configurado corretamente (verifique .env).", "error")
        return render_template('perfil.html', user_info=g.user, perfil=g.perfil, cargos_list=CARGOS_LIST)

    if request.method == 'POST':
        try:
            nome = request.form.get('nome', '').strip(); cargo = request.form.get('cargo', '').strip()
            if cargo not in CARGOS_LIST: cargo = None
            perfil_atual = g.perfil; foto_url_atual = perfil_atual.get('foto_url')

            # --- Lógica de Upload para R2 ---
            if 'foto_perfil' in request.files:
                file = request.files['foto_perfil']
                if file and file.filename and allowed_file(file.filename):
                    try:
                        nome_base, extensao = os.path.splitext(secure_filename(file.filename)); email_hash = generate_password_hash(usuario_cs_email).split('$')[-1][:8]; object_name = f"profile_pics/perfil_{email_hash}_{int(time.time())}{extensao}"

                        # Faz o upload para o R2
                        file.seek(0) # Garante que o ponteiro do arquivo está no início
                        r2_client.upload_fileobj(
                            file,
                            CLOUDFLARE_BUCKET_NAME,
                            object_name,
                            ExtraArgs={'ContentType': file.content_type} # Define o tipo de conteúdo
                        )

                        # Constrói a URL pública usando a URL base do .env
                        foto_url_atual = f"{CLOUDFLARE_PUBLIC_URL}/{object_name}"
                        print(f"Upload R2 concluído: {foto_url_atual}")

                        # --- Excluir foto ANTIGA do R2 ---
                        if perfil_atual.get('foto_url') and perfil_atual['foto_url'] != foto_url_atual:
                            try:
                                # Extrai a chave do objeto da URL antiga (considerando a URL pública base)
                                old_object_key = perfil_atual['foto_url'].replace(f"{CLOUDFLARE_PUBLIC_URL}/", "")
                                if old_object_key:
                                    print(f"Tentando excluir objeto R2 antigo: {old_object_key}")
                                    r2_client.delete_object(Bucket=CLOUDFLARE_BUCKET_NAME, Key=old_object_key)
                                    print(f"Objeto R2 antigo excluído.")
                            except ClientError as e_delete:
                                if e_delete.response['Error']['Code'] == 'NoSuchKey': print(f"Objeto R2 antigo não encontrado: {old_object_key}")
                                else: print(f"Aviso: Falha ao excluir foto antiga do R2. {e_delete}")
                            except Exception as e_delete: print(f"Aviso: Falha ao excluir foto antiga do R2. {e_delete}")
                    except (ClientError, NoCredentialsError) as e_upload:
                         print(f"ERRO upload R2: {e_upload}"); flash("Erro ao fazer upload da nova foto (credenciais/conexão R2?).", "error")
                    except Exception as e_upload:
                        print(f"ERRO upload R2: {e_upload}"); flash("Erro ao fazer upload da nova foto.", "error")

            # --- Fim da Lógica de Upload R2 ---

            execute_db(""" UPDATE perfil_usuario SET nome = %s, cargo = %s, foto_url = %s WHERE usuario = %s """, (nome, cargo, foto_url_atual, usuario_cs_email))
            flash('Perfil atualizado com sucesso!', 'success'); return redirect(url_for('perfil'))
        except Exception as e: print(f"ERRO GERAL ao atualizar perfil para {usuario_cs_email}: {e}"); flash(f'Erro ao atualizar perfil: {e}', 'error'); return redirect(url_for('perfil'))

    return render_template('perfil.html', user_info=g.user, perfil=g.perfil, cargos_list=CARGOS_LIST)

@app.route('/implantacao/<int:impl_id>')
@login_required
def ver_implantacao(impl_id):
    usuario_cs_email = g.user_email; user_info = g.user
    try:
        implantacao = query_db("SELECT * FROM implantacoes WHERE id = %s AND usuario_cs = %s", (impl_id, usuario_cs_email), one=True)
        if not implantacao: flash('Implantação não encontrada.', 'error'); return redirect(url_for('dashboard'))
        implantacao['data_criacao_fmt_dt_hr'] = format_date_br(implantacao.get('data_criacao'), True); implantacao['data_criacao_fmt_d'] = format_date_br(implantacao.get('data_criacao'), False); implantacao['data_finalizacao_fmt_d'] = format_date_br(implantacao.get('data_finalizacao'), False); implantacao['data_inicio_producao_fmt_d'] = format_date_br(implantacao.get('data_inicio_producao'), False); implantacao['data_final_implantacao_fmt_d'] = format_date_br(implantacao.get('data_final_implantacao'), False)
        implantacao['data_criacao_iso'] = format_date_iso_for_json(implantacao.get('data_criacao'), only_date=True); implantacao['data_inicio_producao_iso'] = format_date_iso_for_json(implantacao.get('data_inicio_producao'), only_date=True); implantacao['data_final_implantacao_iso'] = format_date_iso_for_json(implantacao.get('data_final_implantacao'), only_date=True)
        progresso, _, _ = _get_progress(impl_id)
        tarefas_raw = query_db("SELECT * FROM tarefas WHERE implantacao_id = %s ORDER BY tarefa_pai, ordem", (impl_id,))
        comentarios_raw = query_db(""" SELECT c.*, COALESCE(p.nome, c.usuario_cs) as usuario_nome FROM comentarios c LEFT JOIN perfil_usuario p ON c.usuario_cs = p.usuario WHERE c.tarefa_id IN (SELECT id FROM tarefas WHERE implantacao_id = %s) ORDER BY c.data_criacao DESC """, (impl_id,))
        comentarios_por_tarefa = {}; [comentarios_por_tarefa.setdefault(c['tarefa_id'], []).append({**c, 'data_criacao_fmt_d': format_date_br(c.get('data_criacao'))}) for c in comentarios_raw]
        tarefas_agrupadas_treinamento = OrderedDict(); tarefas_agrupadas_obrigatorio = OrderedDict(); tarefas_agrupadas_pendencias = OrderedDict(); todos_modulos_temp = set()
        for t in tarefas_raw:
            t['comentarios'] = comentarios_por_tarefa.get(t['id'], []); modulo = t['tarefa_pai']; todos_modulos_temp.add(modulo)
            if modulo == MODULO_OBRIGATORIO: tarefas_agrupadas_obrigatorio.setdefault(modulo, []).append(t)
            elif modulo == MODULO_PENDENCIAS: tarefas_agrupadas_pendencias.setdefault(modulo, []).append(t)
            else: tarefas_agrupadas_treinamento.setdefault(modulo, []).append(t)
        for modulo in tarefas_agrupadas_obrigatorio: tarefas_agrupadas_obrigatorio[modulo].sort(key=lambda x: x.get('ordem', 0))
        for modulo in tarefas_agrupadas_pendencias: tarefas_agrupadas_pendencias[modulo].sort(key=lambda x: x.get('ordem', 0))
        for modulo in tarefas_agrupadas_treinamento: tarefas_agrupadas_treinamento[modulo].sort(key=lambda x: x.get('ordem', 0))
        ordered_treinamento = OrderedDict(); [ordered_treinamento.update({mp: tarefas_agrupadas_treinamento.pop(mp)}) for mp in TAREFAS_TREINAMENTO_PADRAO if mp in tarefas_agrupadas_treinamento]; [ordered_treinamento.update({mr: tarefas_agrupadas_treinamento[mr]}) for mr in sorted(tarefas_agrupadas_treinamento.keys())]
        todos_modulos_lista = sorted(list(todos_modulos_temp));
        if MODULO_PENDENCIAS not in todos_modulos_lista: todos_modulos_lista.append(MODULO_PENDENCIAS)
        if MODULO_OBRIGATORIO not in todos_modulos_lista:
            try: idx_pend = todos_modulos_lista.index(MODULO_PENDENCIAS); todos_modulos_lista.insert(idx_pend, MODULO_OBRIGATORIO)
            except ValueError: todos_modulos_lista.insert(0, MODULO_OBRIGATORIO)
        logs_timeline = query_db(""" SELECT tl.*, COALESCE(p.nome, tl.usuario_cs) as usuario_nome FROM timeline_log tl LEFT JOIN perfil_usuario p ON tl.usuario_cs = p.usuario WHERE tl.implantacao_id = %s ORDER BY tl.data_criacao DESC """, (impl_id,))
        for log in logs_timeline: log['data_criacao_fmt_dt_hr'] = format_date_br(log.get('data_criacao'), True)
        nome_usuario_logado = g.perfil.get('nome', usuario_cs_email)
        return render_template('implantacao_detalhes.html', user_info=user_info, implantacao=implantacao, tarefas_agrupadas_obrigatorio=tarefas_agrupadas_obrigatorio, tarefas_agrupadas_treinamento=ordered_treinamento, tarefas_agrupadas_pendencias=tarefas_agrupadas_pendencias, todos_modulos=todos_modulos_lista, modulo_pendencias_nome=MODULO_PENDENCIAS, progresso_porcentagem=progresso, nome_usuario_logado=nome_usuario_logado, email_usuario_logado=usuario_cs_email, justificativas_parada=JUSTIFICATIVAS_PARADA, logs_timeline=logs_timeline, cargos_responsavel=CARGOS_RESPONSAVEL)
    except Exception as e:
        print(f"ERRO detalhes impl ID {impl_id}: {e}"); flash("Erro ao carregar detalhes.", "error"); return redirect(url_for('dashboard'))

# ----------------------------------------------------------------------
# --- Rotas de Ação ---
# ----------------------------------------------------------------------

@app.route('/criar_implantacao', methods=['POST'])
@login_required
def criar_implantacao():
    usuario_cs_email = g.user_email
    nome_empresa = request.form.get('nome_empresa', '').strip(); tipo = request.form.get('tipo', 'agora')
    if not nome_empresa or tipo not in ['agora', 'futura']: flash('Dados inválidos.', 'error'); return redirect(url_for('dashboard'))
    try:
        implantacao_id = execute_db("INSERT INTO implantacoes (usuario_cs, nome_empresa, tipo, data_criacao, status) VALUES (%s, %s, %s, %s, %s)", (usuario_cs_email, nome_empresa, tipo, datetime.now(), 'futura' if tipo == 'futura' else 'andamento'))
        if not implantacao_id: raise Exception("Falha ID.")
        logar_timeline(implantacao_id, usuario_cs_email, 'implantacao_criada', f'Implantação "{nome_empresa}" ({tipo.capitalize()}) criada.')
        tasks_added = _create_default_tasks(implantacao_id); flash(f'Implantação "{nome_empresa}" criada ({tasks_added} tarefas).', 'success')
        return redirect(url_for('ver_implantacao', impl_id=implantacao_id))
    except Exception as e: user_email_for_log = getattr(g, 'user_email', '?'); print(f"ERRO criar impl {user_email_for_log}: {e}"); flash(f'Erro: {e}.', 'error'); return redirect(url_for('dashboard'))

@app.route('/iniciar_implantacao', methods=['POST'])
@login_required
def iniciar_implantacao():
    usuario_cs_email = g.user_email; implantacao_id = request.form.get('implantacao_id')
    try:
        impl = query_db("SELECT usuario_cs, nome_empresa, tipo FROM implantacoes WHERE id = %s", (implantacao_id,), one=True)
        if not impl or impl.get('usuario_cs') != usuario_cs_email or impl.get('tipo') != 'futura': flash('Operação negada.', 'error'); return redirect(request.referrer or url_for('dashboard'))
        execute_db("UPDATE implantacoes SET tipo = 'agora', status = 'andamento', data_criacao = %s WHERE id = %s", (datetime.now(), implantacao_id))
        logar_timeline(implantacao_id, usuario_cs_email, 'status_alterado', f'Implantação "{impl.get("nome_empresa", "N/A")}" iniciada.'); flash('Implantação iniciada!', 'success')
        return redirect(url_for('ver_implantacao', impl_id=implantacao_id))
    except Exception as e: print(f"Erro iniciar ID {implantacao_id}: {e}"); flash('Erro ao iniciar.', 'error'); return redirect(url_for('dashboard'))

@app.route('/finalizar_implantacao', methods=['POST'])
@login_required
def finalizar_implantacao():
    usuario_cs_email = g.user_email; implantacao_id = request.form.get('implantacao_id'); redirect_target = request.form.get('redirect_to', 'dashboard')
    try:
        impl = query_db("SELECT usuario_cs, nome_empresa, status FROM implantacoes WHERE id = %s", (implantacao_id,), one=True)
        if not impl or impl.get('usuario_cs') != usuario_cs_email or impl.get('status') != 'andamento': raise Exception('Operação negada.')
        pending_tasks = query_db("SELECT COUNT(*) as total FROM tarefas WHERE implantacao_id = %s AND concluida = %s AND tarefa_pai != %s", (implantacao_id, 0, MODULO_PENDENCIAS), one=True)
        if pending_tasks and pending_tasks.get('total', 0) > 0:
            total_pendentes = pending_tasks.get('total'); flash(f'Não pode finalizar: {total_pendentes} tarefas obrigatórias/treinamento pendentes.', 'error'); dest = 'ver_implantacao' if redirect_target == 'detalhes' else 'dashboard'; return redirect(url_for(dest, impl_id=implantacao_id if dest == 'ver_implantacao' else None))
        execute_db("UPDATE implantacoes SET status = 'finalizada', data_finalizacao = CURRENT_TIMESTAMP WHERE id = %s", (implantacao_id,))
        logar_timeline(implantacao_id, usuario_cs_email, 'status_alterado', f'Implantação "{impl.get("nome_empresa", "N/A")}" finalizada.'); flash('Implantação finalizada!', 'success')
    except Exception as e: print(f"Erro finalizar ID {implantacao_id}: {e}"); flash(f'Erro: {e}', 'error')
    dest = 'ver_implantacao' if redirect_target == 'detalhes' else 'dashboard'; return redirect(url_for(dest, impl_id=implantacao_id if dest == 'ver_implantacao' else None))

@app.route('/parar_implantacao', methods=['POST'])
@login_required
def parar_implantacao():
    usuario_cs_email = g.user_email; implantacao_id = request.form.get('implantacao_id'); motivo = request.form.get('motivo_parada', '').strip()
    if not motivo: flash('Motivo obrigatório.', 'error'); return redirect(url_for('ver_implantacao', impl_id=implantacao_id))
    try:
        impl = query_db("SELECT usuario_cs, nome_empresa, status FROM implantacoes WHERE id = %s", (implantacao_id,), one=True)
        if not impl or impl.get('usuario_cs') != usuario_cs_email or impl.get('status') != 'andamento': raise Exception('Operação negada.')
        execute_db("UPDATE implantacoes SET status = 'parada', data_finalizacao = CURRENT_TIMESTAMP, motivo_parada = %s WHERE id = %s", (motivo, implantacao_id))
        logar_timeline(implantacao_id, usuario_cs_email, 'status_alterado', f'Implantação "{impl.get("nome_empresa", "N/A")}" parada. Motivo: {motivo}'); flash('Implantação parada.', 'success')
    except Exception as e: print(f"Erro parar ID {implantacao_id}: {e}"); flash(f'Erro: {e}', 'error')
    return redirect(url_for('ver_implantacao', impl_id=implantacao_id))

@app.route('/retomar_implantacao', methods=['POST'])
@login_required
def retomar_implantacao():
    usuario_cs_email = g.user_email; implantacao_id = request.form.get('implantacao_id'); redirect_to = request.form.get('redirect_to', 'dashboard')
    try:
        impl = query_db("SELECT usuario_cs, nome_empresa, status FROM implantacoes WHERE id = %s", (implantacao_id,), one=True)
        if not impl or impl.get('usuario_cs') != usuario_cs_email or impl.get('status') != 'parada': flash('Apenas paradas podem ser retomadas.', 'warning'); return redirect(request.referrer or url_for('dashboard'))
        execute_db("UPDATE implantacoes SET status = 'andamento', data_finalizacao = NULL, motivo_parada = '' WHERE id = %s", (implantacao_id,))
        logar_timeline(implantacao_id, usuario_cs_email, 'status_alterado', f'Implantação "{impl.get("nome_empresa", "N/A")}" retomada.'); flash('Implantação retomada.', 'success')
    except Exception as e: print(f"Erro retomar ID {implantacao_id}: {e}"); flash(f'Erro: {e}', 'error')
    dest = 'ver_implantacao' if redirect_to == 'detalhes' else 'dashboard'; return redirect(url_for(dest, impl_id=implantacao_id if dest == 'ver_implantacao' else None))

@app.route('/atualizar_detalhes_empresa', methods=['POST'])
@login_required
def atualizar_detalhes_empresa():
    usuario_cs_email = g.user_email; implantacao_id = request.form.get('implantacao_id'); redirect_to = request.form.get('redirect_to', 'dashboard')
    if not query_db("SELECT id FROM implantacoes WHERE id = %s AND usuario_cs = %s", (implantacao_id, usuario_cs_email), one=True): flash('Permissão negada.', 'error'); return redirect(url_for('dashboard'))
    try:
        data_inicio_prod = request.form.get('data_inicio_producao') or None; data_final_impl = request.form.get('data_final_implantacao') or None
        query = """ UPDATE implantacoes SET responsavel_cliente = %s, cargo_responsavel = %s, telefone_responsavel = %s, email_responsavel = %s, data_inicio_producao = %s, data_final_implantacao = %s, chave_oamd = %s, catraca = %s, facial = %s WHERE id = %s AND usuario_cs = %s """
        args = (request.form.get('responsavel_cliente', '').strip(), request.form.get('cargo_responsavel', '').strip(), request.form.get('telefone_responsavel', '').strip(), request.form.get('email_responsavel', '').strip(), data_inicio_prod, data_final_impl, request.form.get('chave_oamd', '').strip(), request.form.get('catraca', '').strip(), request.form.get('facial', '').strip(), implantacao_id, usuario_cs_email)
        execute_db(query, args); logar_timeline(implantacao_id, usuario_cs_email, 'detalhes_alterados', 'Detalhes atualizados.'); flash('Detalhes atualizados!', 'success')
    except Exception as e: print(f"Erro atualizar detalhes ID {implantacao_id}: {e}"); flash('Erro ao atualizar.', 'error')
    dest = 'ver_implantacao' if redirect_to == 'detalhes' else 'dashboard'; return redirect(url_for(dest, impl_id=implantacao_id if dest == 'ver_implantacao' else None))

@app.route('/excluir_implantacao', methods=['POST'])
@login_required
def excluir_implantacao():
    usuario_cs_email = g.user_email; implantacao_id = request.form.get('implantacao_id')
    if not query_db("SELECT id FROM implantacoes WHERE id = %s AND usuario_cs = %s", (implantacao_id, usuario_cs_email), one=True): flash('Permissão negada.', 'error'); return redirect(url_for('dashboard'))
    if not r2_client: flash("Erro: Serviço R2 não configurado.", "error"); return redirect(request.referrer or url_for('dashboard'))
    try:
        comentarios_img = query_db(""" SELECT c.imagem_url FROM comentarios c JOIN tarefas t ON c.tarefa_id = t.id WHERE t.implantacao_id = %s AND c.imagem_url IS NOT NULL AND c.imagem_url != '' """, (implantacao_id,))
        for c in comentarios_img:
            imagem_url = c.get('imagem_url')
            if imagem_url and CLOUDFLARE_PUBLIC_URL and imagem_url.startswith(CLOUDFLARE_PUBLIC_URL): # Verifica se é uma URL R2
                print(f"Excluindo imagem R2: {imagem_url}")
                try:
                    object_key = imagem_url.replace(f"{CLOUDFLARE_PUBLIC_URL}/", "") # Remove base da URL
                    if object_key: r2_client.delete_object(Bucket=CLOUDFLARE_BUCKET_NAME, Key=object_key); print(f"Objeto R2 excluído: {object_key}")
                except ClientError as e_delete: print(f"Aviso R2 ({e_delete.response['Error']['Code']}): {object_key}")
                except Exception as e_delete: print(f"Aviso R2: {object_key}. {e_delete}")
        execute_db("DELETE FROM implantacoes WHERE id = %s", (implantacao_id,)); flash('Implantação excluída.', 'success')
    except Exception as e: print(f"Erro excluir ID {implantacao_id}: {e}"); flash('Erro ao excluir.', 'error')
    return redirect(url_for('dashboard'))

# ----------------------------------------------------------------------
# --- Rotas API ---
# ----------------------------------------------------------------------

@app.route('/toggle_tarefa/<int:tarefa_id>', methods=['POST'])
@login_required
def toggle_tarefa(tarefa_id):
    usuario_cs_email = g.user_email
    try:
        tarefa = query_db(""" SELECT t.*, i.usuario_cs, i.id as implantacao_id, i.status FROM tarefas t JOIN implantacoes i ON t.implantacao_id = i.id WHERE t.id = %s """, (tarefa_id,), one=True)
        if not tarefa or tarefa.get('usuario_cs') != usuario_cs_email: return jsonify({'ok': False, 'error': 'forbidden'}), 403
        if tarefa.get('status') in ['finalizada', 'parada', 'futura']: return jsonify({'ok': False, 'error': 'Status inválido.'}), 400
        novo_status_bool = not tarefa.get('concluida', False); execute_db("UPDATE tarefas SET concluida = %s WHERE id = %s", (novo_status_bool, tarefa_id))
        detalhe = f"Tarefa '{tarefa['tarefa_filho']}': {'Concluída' if novo_status_bool else 'Não Concluída'}."
        logar_timeline(tarefa['implantacao_id'], usuario_cs_email, 'tarefa_alterada', detalhe)
        finalizada, log_finalizacao = auto_finalizar_implantacao(tarefa['implantacao_id'], usuario_cs_email)
        novo_prog, _, _ = _get_progress(tarefa['implantacao_id'])
        nome = g.perfil.get('nome', usuario_cs_email); log_tarefa = query_db("SELECT *, %s as usuario_nome FROM timeline_log WHERE implantacao_id = %s AND tipo_evento = 'tarefa_alterada' ORDER BY id DESC LIMIT 1", (nome, tarefa['implantacao_id']), one=True)
        if log_tarefa: log_tarefa['data_criacao'] = format_date_iso_for_json(log_tarefa.get('data_criacao'))
        return jsonify({'ok': True, 'novo_status': 1 if novo_status_bool else 0, 'implantacao_finalizada': finalizada, 'novo_progresso': novo_prog, 'log_tarefa': log_tarefa, 'log_finalizacao': log_finalizacao})
    except Exception as e: print(f"ERRO toggle tarefa ID {tarefa_id}: {e}"); return jsonify({'ok': False, 'error': f"Erro: {e}"}), 500

@app.route('/adicionar_comentario/<int:tarefa_id>', methods=['POST'])
@login_required
def adicionar_comentario(tarefa_id):
    usuario_cs_email = g.user_email; texto = request.form.get('comentario', '')[:8000].strip(); img_url = None
    if not r2_client or not CLOUDFLARE_PUBLIC_URL: return jsonify({'ok': False, 'error': 'Serviço R2 não configurado.'}), 500

    if 'imagem' in request.files:
        file = request.files.get('imagem')
        if file and file.filename and allowed_file(file.filename):
            try:
                filename = secure_filename(file.filename); nome_base, extensao = os.path.splitext(filename); nome_unico = f"{nome_base}_task{tarefa_id}_{int(time.time())}{extensao}"
                tarefa_info_temp = query_db("SELECT implantacao_id FROM tarefas WHERE id = %s", (tarefa_id,), one=True)
                if not tarefa_info_temp: raise Exception("Tarefa não encontrada.")
                # Upload para R2
                try:
                    object_name = f"comment_images/impl_{tarefa_info_temp['implantacao_id']}/task_{tarefa_id}/{nome_unico}"
                    file.seek(0); r2_client.upload_fileobj(file, CLOUDFLARE_BUCKET_NAME, object_name, ExtraArgs={'ContentType': file.content_type})
                    img_url = f"{CLOUDFLARE_PUBLIC_URL}/{object_name}"; print(f"SUCESSO (R2): Upload para {object_name}. URL: {img_url}")
                except (ClientError, NoCredentialsError) as upload_err: print(f"ERRO upload R2 comentário: {upload_err}"); flash("Erro upload imagem R2.", "error"); img_url = None
            except Exception as e: return jsonify({'ok': False, 'error': f'Falha imagem: {e}'}), 500
        elif file and file.filename and not allowed_file(file.filename): return jsonify({'ok': False, 'error': 'Tipo inválido.'}), 400
    if not texto and not img_url: return jsonify({'ok': False, 'error': 'Comentário vazio.'}), 400
    try:
        tarefa = query_db("SELECT i.usuario_cs, i.id as implantacao_id, t.tarefa_filho FROM tarefas t JOIN implantacoes i ON t.implantacao_id = i.id WHERE t.id = %s", (tarefa_id,), one=True)
        if not tarefa or tarefa.get('usuario_cs') != usuario_cs_email: return jsonify({'ok': False, 'error': 'forbidden'}), 403
        agora = datetime.now(); novo_id = execute_db("INSERT INTO comentarios (tarefa_id, usuario_cs, texto, data_criacao, imagem_url) VALUES (%s, %s, %s, %s, %s)", (tarefa_id, usuario_cs_email, texto, agora, img_url))
        if not novo_id: raise Exception("Falha ID.")
        detalhe = f"Comentário em '{tarefa['tarefa_filho']}':\n{texto}" if texto else f"Imagem em '{tarefa['tarefa_filho']}'."
        if texto and img_url: detalhe = f"Comentário em '{tarefa['tarefa_filho']}':\n{texto}\n[Imagem]"; logar_timeline(tarefa['implantacao_id'], usuario_cs_email, 'novo_comentario', detalhe)
        nome = g.perfil.get('nome', usuario_cs_email); log_com = query_db("SELECT *, %s as usuario_nome FROM timeline_log WHERE implantacao_id = %s AND tipo_evento = 'novo_comentario' ORDER BY id DESC LIMIT 1", (nome, tarefa['implantacao_id']), one=True)
        data_criacao_str = format_date_iso_for_json(agora);
        if log_com: log_com['data_criacao'] = format_date_iso_for_json(log_com.get('data_criacao'))
        return jsonify({'ok': True, 'comentario': {'id': novo_id, 'tarefa_id': tarefa_id, 'usuario_cs': usuario_cs_email, 'usuario_nome': nome, 'texto': texto, 'imagem_url': img_url, 'data_criacao': data_criacao_str}, 'log_comentario': log_com})
    except Exception as e: print(f"ERRO salvar comentário {tarefa_id}: {e}"); return jsonify({'ok': False, 'error': f"Erro: {e}"}), 500

@app.route('/excluir_comentario/<int:comentario_id>', methods=['POST'])
@login_required
def excluir_comentario(comentario_id):
    usuario_cs_email = g.user_email
    if not r2_client: return jsonify({'ok': False, 'error': 'Serviço R2 não configurado.'}), 500
    try:
        comentario = query_db(""" SELECT c.*, i.id as impl_id, t.tarefa_filho FROM comentarios c JOIN tarefas t ON c.tarefa_id = t.id JOIN implantacoes i ON t.implantacao_id = i.id WHERE c.id = %s """, (comentario_id,), one=True)
        if not comentario or comentario.get('usuario_cs') != usuario_cs_email: return jsonify({'ok': False, 'error': 'forbidden'}), 403
        imagem_url = comentario.get('imagem_url')
        if imagem_url and CLOUDFLARE_PUBLIC_URL and imagem_url.startswith(CLOUDFLARE_PUBLIC_URL):
            print(f"Excluindo imagem R2: {imagem_url}")
            try:
                object_key = imagem_url.replace(f"{CLOUDFLARE_PUBLIC_URL}/", "")
                if object_key: r2_client.delete_object(Bucket=CLOUDFLARE_BUCKET_NAME, Key=object_key); print(f"Objeto R2 excluído: {object_key}")
            except ClientError as e_delete: print(f"Aviso R2 ({e_delete.response['Error']['Code']}): {object_key}")
            except Exception as e_delete: print(f"Aviso R2: {object_key}. {e_delete}")

        execute_db("DELETE FROM comentarios WHERE id = %s", (comentario_id,)); logar_timeline(comentario['impl_id'], usuario_cs_email, 'comentario_excluido', f"Comentário em '{comentario['tarefa_filho']}' excluído.")
        nome = g.perfil.get('nome', usuario_cs_email); log_exclusao = query_db("SELECT *, %s as usuario_nome FROM timeline_log WHERE implantacao_id = %s AND tipo_evento = 'comentario_excluido' ORDER BY id DESC LIMIT 1", (nome, comentario['impl_id']), one=True)
        if log_exclusao: log_exclusao['data_criacao'] = format_date_iso_for_json(log_exclusao.get('data_criacao'))
        return jsonify({'ok': True, 'log_exclusao': log_exclusao, 'tarefa_id': comentario['tarefa_id']})
    except Exception as e: print(f"ERRO excluir comentário ID {comentario_id}: {e}"); return jsonify({'ok': False, 'error': f"Erro: {e}"}), 500

@app.route('/adicionar_tarefa', methods=['POST'])
@login_required
def adicionar_tarefa():
    usuario_cs_email = g.user_email; implantacao_id = request.form.get('implantacao_id'); tarefa_filho = request.form.get('tarefa_filho', '').strip(); tarefa_pai = request.form.get('tarefa_pai', '').strip(); tag = request.form.get('tag', '').strip()
    if not all([implantacao_id, tarefa_filho, tarefa_pai]): flash('Dados inválidos.', 'error'); return redirect(request.referrer or url_for('ver_implantacao', impl_id=implantacao_id))
    try:
        impl = query_db("SELECT id, nome_empresa, status FROM implantacoes WHERE id = %s AND usuario_cs = %s", (implantacao_id, usuario_cs_email), one=True)
        if not impl: flash('Permissão negada.', 'error'); return redirect(url_for('dashboard'))
        if impl.get('status') == 'finalizada': flash('Não pode adicionar tarefas.', 'warning'); return redirect(url_for('ver_implantacao', impl_id=implantacao_id))
        max_ordem = query_db("SELECT MAX(ordem) as max_o FROM tarefas WHERE implantacao_id = %s AND tarefa_pai = %s", (implantacao_id, tarefa_pai), one=True); nova_ordem = (max_ordem.get('max_o') or 0) + 1
        execute_db("INSERT INTO tarefas (implantacao_id, tarefa_pai, tarefa_filho, tag, ordem, concluida) VALUES (%s, %s, %s, %s, %s, %s)", (implantacao_id, tarefa_pai, tarefa_filho, tag, nova_ordem, 0))
        logar_timeline(implantacao_id, usuario_cs_email, 'tarefa_adicionada', f"Tarefa '{tarefa_filho}' adicionada a '{tarefa_pai}'."); flash('Tarefa adicionada!', 'success')
    except Exception as e: print(f"Erro adicionar tarefa ID {implantacao_id}: {e}"); flash(f'Erro: {e}', 'error')
    return redirect(url_for('ver_implantacao', impl_id=implantacao_id))

@app.route('/excluir_tarefa/<int:tarefa_id>', methods=['POST'])
@login_required
def excluir_tarefa(tarefa_id):
    usuario_cs_email = g.user_email
    if not r2_client: return jsonify({'ok': False, 'error': 'Serviço R2 não configurado.'}), 500
    try:
        tarefa = query_db(""" SELECT t.tarefa_filho, i.id as impl_id, i.usuario_cs, i.status FROM tarefas t JOIN implantacoes i ON t.implantacao_id = i.id WHERE t.id = %s """, (tarefa_id,), one=True)
        if not tarefa or tarefa.get('usuario_cs') != usuario_cs_email: return jsonify({'ok': False, 'error': 'forbidden'}), 403
        impl_id = tarefa['impl_id']; nome_tarefa = tarefa['tarefa_filho']
        if tarefa.get('status') in ['finalizada']: return jsonify({'ok': False, 'error': 'Não pode excluir tarefas.'}), 400

        # Excluir imagens associadas ANTES
        comentarios_tarefa = query_db("SELECT id, imagem_url FROM comentarios WHERE tarefa_id = %s", (tarefa_id,))
        for com in comentarios_tarefa:
             imagem_url = com.get('imagem_url')
             if imagem_url and CLOUDFLARE_PUBLIC_URL and imagem_url.startswith(CLOUDFLARE_PUBLIC_URL):
                print(f"Excluindo imagem do comentário {com['id']} (tarefa {tarefa_id}): {imagem_url}")
                try:
                    object_key = imagem_url.replace(f"{CLOUDFLARE_PUBLIC_URL}/", "")
                    if object_key: r2_client.delete_object(Bucket=CLOUDFLARE_BUCKET_NAME, Key=object_key); print(f"Objeto R2 excluído: {object_key}")
                except ClientError as e_delete: print(f"Aviso R2 ({e_delete.response['Error']['Code']}): {object_key}")
                except Exception as e_delete: print(f"Aviso R2: {object_key}. {e_delete}")

        # Agora exclui a tarefa
        execute_db("DELETE FROM tarefas WHERE id = %s", (tarefa_id,)); logar_timeline(impl_id, usuario_cs_email, 'tarefa_excluida', f"Tarefa '{nome_tarefa}' excluída.")
        finalizada, log_finalizacao = auto_finalizar_implantacao(impl_id, usuario_cs_email); novo_prog, _, _ = _get_progress(impl_id)
        nome = g.perfil.get('nome', usuario_cs_email); log_exclusao = query_db("SELECT *, %s as usuario_nome FROM timeline_log WHERE implantacao_id = %s AND tipo_evento = 'tarefa_excluida' ORDER BY id DESC LIMIT 1", (nome, impl_id), one=True)
        if log_exclusao: log_exclusao['data_criacao'] = format_date_iso_for_json(log_exclusao.get('data_criacao'))
        return jsonify({'ok': True, 'log_exclusao': log_exclusao, 'novo_progresso': novo_prog, 'implantacao_finalizada': finalizada, 'log_finalizacao': log_finalizacao})
    except Exception as e: print(f"ERRO excluir tarefa ID {tarefa_id}: {e}"); return jsonify({'ok': False, 'error': f"Erro: {e}"}), 500

@app.route('/reordenar_tarefas', methods=['POST'])
@login_required
def reordenar_tarefas():
    usuario_cs_email = g.user_email
    try:
        data = request.get_json(); impl_id = data.get('implantacao_id'); tarefa_pai = data.get('tarefa_pai'); nova_ordem_ids = data.get('ordem')
        if not all([impl_id, tarefa_pai, isinstance(nova_ordem_ids, list)]): return jsonify({'ok': False, 'error': 'Dados inválidos.'}), 400
        if not query_db("SELECT id FROM implantacoes WHERE id = %s AND usuario_cs = %s", (impl_id, usuario_cs_email), one=True): return jsonify({'ok': False, 'error': 'forbidden'}), 403
        for index, tarefa_id in enumerate(nova_ordem_ids, 1): execute_db("UPDATE tarefas SET ordem = %s WHERE id = %s AND implantacao_id = %s AND tarefa_pai = %s", (index, tarefa_id, impl_id, tarefa_pai))
        logar_timeline(impl_id, usuario_cs_email, 'tarefas_reordenadas', f"Ordem em '{tarefa_pai}' alterada.")
        nome = g.perfil.get('nome', usuario_cs_email); log_reordenar = query_db("SELECT *, %s as usuario_nome FROM timeline_log WHERE implantacao_id = %s AND tipo_evento = 'tarefas_reordenadas' ORDER BY id DESC LIMIT 1", (nome, impl_id), one=True)
        if log_reordenar: log_reordenar['data_criacao'] = format_date_iso_for_json(log_reordenar.get('data_criacao'))
        return jsonify({'ok': True, 'log_reordenar': log_reordenar})
    except Exception as e: print(f"ERRO reordenar: {e}"); return jsonify({'ok': False, 'error': f"Erro: {e}"}), 500

# ----------------------------------------------------------------------
# --- Bloco de Execução Principal ---
# ----------------------------------------------------------------------

if __name__ == '__main__':
    print("Iniciando app Flask...")
    try:
        init_db()
    except Exception as e:
        print(f"ERRO CRÍTICO init_db: {e}")

    if not r2_client:
        print("\n!!! ATENÇÃO: Cliente R2 não inicializado. Uploads R2 não funcionarão. Verifique .env !!!\n")

    app.run(debug=True, host='127.0.0.1', port=5000)