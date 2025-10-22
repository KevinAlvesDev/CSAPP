import os
import sqlite3
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
from flask import (Flask, redirect, url_for, session, render_template, g, jsonify, request, flash, send_from_directory)
from authlib.integrations.flask_client import OAuth
from urllib.parse import urlencode
from functools import wraps
from werkzeug.security import generate_password_hash # Só para placeholder de senha
from werkzeug.utils import secure_filename
from collections import OrderedDict
from datetime import datetime, date

# --- Firebase Admin (Para Storage - Manter para o futuro) ---
# import firebase_admin
# from firebase_admin import credentials, storage
# -----------------------------------------------------------

load_dotenv() # Carrega variáveis do .env

# --- INICIALIZAÇÃO DO FIREBASE (Para Storage - Manter para o futuro) ---
# Descomente e preencha quando for implementar o Storage
# try:
#     cred = credentials.Certificate('firebase-service-account.json')
#     firebase_admin.initialize_app(cred, {
#         'storageBucket': 'SEU_BUCKET_ID_FIREBASE_AQUI' # <-- PREENCHER QUANDO USAR
#     })
#     print("Firebase Admin SDK inicializado.")
# except FileNotFoundError:
#      print("AVISO: Arquivo 'firebase-service-account.json' não encontrado. Necessário para Firebase Storage.")
# except Exception as e:
#     print(f"AVISO: Erro ao inicializar Firebase Admin SDK: {e}")
# -----------------------------------------------------------

app = Flask(__name__)
# Carrega a chave secreta do Flask do .env
app.secret_key = os.environ.get("FLASK_SECRET_KEY")
if not app.secret_key:
    raise ValueError("FLASK_SECRET_KEY não definida no ambiente ou .env. Gere uma chave segura.")

# --- CONFIGURAÇÃO DO AUTHLIB / AUTH0 ---
oauth = OAuth(app)
# Carrega credenciais Auth0 do .env
auth0_domain = os.environ.get("AUTH0_DOMAIN")
auth0_client_id = os.environ.get("AUTH0_CLIENT_ID")
auth0_client_secret = os.environ.get("AUTH0_CLIENT_SECRET")

# Validação das credenciais Auth0
if not all([auth0_domain, auth0_client_id, auth0_client_secret]):
     raise ValueError("Credenciais Auth0 (DOMAIN, CLIENT_ID, CLIENT_SECRET) não definidas no ambiente ou .env. Verifique seu arquivo .env.")

# Registra o cliente OAuth para Auth0
auth0 = oauth.register(
    'auth0',
    client_id=auth0_client_id,
    client_secret=auth0_client_secret,
    client_kwargs={
        'scope': 'openid profile email', # Escopos OIDC para obter informações do usuário
    },
    # URL para descoberta automática das configurações OIDC do Auth0
    server_metadata_url=f'https://{auth0_domain}/.well-known/openid-configuration'
)
# -------------------------------

# --- Configuração Banco de Dados ---
DATABASE_URL = os.environ.get('DATABASE_URL')
# Usa SQLite localmente APENAS se DATABASE_URL não estiver definida
USE_SQLITE_LOCALLY = not DATABASE_URL
LOCAL_SQLITE_DB = 'dashboard_simples.db' # Nome do arquivo SQLite local

# --- Definições Globais (Tarefas Padrão, Justificativas, Cargos) ---
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
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'} # Extensões permitidas para upload

# --- Funções de Banco de Dados (Adaptadas para PostgreSQL e SQLite) ---
def get_db():
    """Obtém uma conexão com o banco de dados (PostgreSQL ou SQLite)."""
    db = getattr(g, '_database', None)
    if db is None:
        if not USE_SQLITE_LOCALLY and DATABASE_URL:
            try:
                # Conecta ao PostgreSQL usando a URL do ambiente
                db = g._database = psycopg2.connect(DATABASE_URL)
                print("Conectado ao PostgreSQL.")
            except psycopg2.OperationalError as e:
                print(f"ERRO CRÍTICO: Não foi possível conectar ao PostgreSQL: {e}")
                # Em um app real, talvez lançar uma exceção ou retornar um erro HTTP
                raise e # Re-lança a exceção para parar a execução se o DB for essencial
        elif USE_SQLITE_LOCALLY:
            # Conecta ao SQLite local
            db = g._database = sqlite3.connect(LOCAL_SQLITE_DB)
            # Configura para retornar linhas como dicionários (semelhante ao DictCursor)
            db.row_factory = sqlite3.Row
            print(f"Conectado ao SQLite local: {LOCAL_SQLITE_DB}")
        else:
            # Caso de erro: sem URL de produção e SQLite desativado
             raise Exception("Configuração de banco de dados inválida: DATABASE_URL não definida e fallback SQLite desativado.")
    return db

@app.teardown_appcontext
def close_connection(exception):
    """Fecha a conexão com o banco de dados ao final da requisição."""
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()
        # print("Conexão DB fechada.") # Descomente para debug

def query_db(query, args=(), one=False):
    """Executa uma query SELECT e retorna os resultados como dicionários."""
    db = get_db()
    cur = None
    try:
        is_postgres = isinstance(db, psycopg2.extensions.connection)
        is_sqlite = isinstance(db, sqlite3.Connection)

        if is_postgres:
            # Usa DictCursor para PostgreSQL retornar dicionários
            cur = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        elif is_sqlite:
            # Adapta placeholders de %s para ? para SQLite
            query = query.replace('%s', '?')
            cur = db.cursor() # row_factory já foi definido na conexão
        else:
            raise TypeError("Tipo de conexão de banco de dados não suportado.")

        cur.execute(query, args)
        
        # SQLite com row_factory retorna objetos Row, converte para dict
        if is_sqlite:
             rows = cur.fetchall()
             # Garante que temos uma lista de dicionários
             rv = [dict(row) for row in rows]
        else: # PostgreSQL com DictCursor já retorna algo iterável como dict
            rv = cur.fetchall()
            # Garante que temos uma lista de dicionários padrão
            rv = [dict(row) for row in rv]


        cur.close()
        # Retorna o primeiro resultado se 'one=True', caso contrário a lista completa
        return (rv[0] if rv else None) if one else rv
    except Exception as e:
        print(f"ERRO ao executar query: {e}\nQuery SQL: {query}\nArgumentos: {args}")
        if cur: cur.close() # Tenta fechar o cursor em caso de erro
        # Considerar relançar a exceção ou retornar None/[] dependendo do caso de uso
        raise e # Relançar por padrão para indicar falha

def execute_db(command, args=()):
    """Executa um comando SQL (INSERT, UPDATE, DELETE) e retorna o ID inserido (se aplicável)."""
    db = get_db()
    cur = None
    returned_id = None
    try:
        is_postgres = isinstance(db, psycopg2.extensions.connection)
        is_sqlite = isinstance(db, sqlite3.Connection)

        # Adapta placeholders para SQLite
        if is_sqlite:
            command = command.replace('%s', '?')

        cur = db.cursor()

        # Lógica para obter ID de retorno (PostgreSQL usa RETURNING, SQLite usa lastrowid)
        if is_postgres:
            command_upper = command.strip().upper()
            # Verifica se é um INSERT em tabelas específicas que queremos o ID
            needs_returning_id = command_upper.startswith("INSERT") and \
                                 any(tbl in command_upper for tbl in ["INTO IMPLANTACOES", "INTO TAREFAS", "INTO COMENTARIOS", "INTO TIMELINE_LOG"])

            # Adiciona RETURNING id se necessário e ainda não presente
            if needs_returning_id and "RETURNING" not in command_upper:
                command += " RETURNING id"
                cur.execute(command, args)
                # Pega o ID retornado se a inserção foi bem-sucedida
                returned_id = cur.fetchone()[0] if cur.rowcount > 0 else None
            else:
                # Executa comando sem esperar retorno de ID (UPDATE, DELETE, ou INSERT sem RETURNING)
                cur.execute(command, args)
        elif is_sqlite:
             # Executa comando no SQLite
             cur.execute(command, args)
             # Obtém o ID da última linha inserida
             returned_id = cur.lastrowid
        else:
            raise TypeError("Tipo de conexão de banco de dados não suportado.")

        db.commit() # Confirma a transação
        cur.close()
        return returned_id # Retorna o ID inserido ou None
    except Exception as e:
        print(f"ERRO ao executar comando: {e}\nComando SQL: {command}\nArgumentos: {args}")
        if cur: cur.close() # Tenta fechar o cursor
        db.rollback() # Desfaz a transação em caso de erro
        raise e # Relança a exceção

def init_db():
    """Verifica e cria as tabelas do banco de dados se não existirem."""
    with app.app_context(): # Garante que temos o contexto da aplicação
        db = get_db()
        cur = db.cursor()
        is_postgres = isinstance(db, psycopg2.extensions.connection)

        # Define tipos de dados compatíveis com PostgreSQL e SQLite
        pk_type = "SERIAL PRIMARY KEY" if is_postgres else "INTEGER PRIMARY KEY AUTOINCREMENT"
        boolean_type = "BOOLEAN" if is_postgres else "INTEGER" # SQLite usa 0/1 para booleano
        timestamp_type = "TIMESTAMP WITH TIME ZONE" if is_postgres else "DATETIME" # SQLite não tem timezone
        date_type = "DATE" if is_postgres else "TEXT" # SQLite armazena datas como TEXTO (ISO 8601 recomendado)

        # Criação das tabelas usando f-strings (cuidado com injeção SQL se viesse de input)
        # Tabela usuarios: senha ainda é NOT NULL, mas não será usada para login Auth0
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS usuarios (
                usuario VARCHAR(255) PRIMARY KEY, -- Email usado como ID principal aqui
                senha TEXT NOT NULL -- Usaremos hash do ID Auth0 como placeholder seguro
            )
        """)
        # Tabela perfil_usuario: armazena nome e métricas
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS perfil_usuario (
                usuario VARCHAR(255) PRIMARY KEY REFERENCES usuarios(usuario) ON DELETE CASCADE,
                nome TEXT,
                impl_andamento INTEGER DEFAULT 0,
                impl_finalizadas INTEGER DEFAULT 0,
                impl_paradas INTEGER DEFAULT 0,
                progresso_medio_carteira INTEGER DEFAULT 0,
                impl_andamento_total INTEGER DEFAULT 0,
                implantacoes_atrasadas INTEGER DEFAULT 0
                -- Adicionar outras métricas se necessário
            )
        """)
        # Tabela implantacoes: dados principais da implantação
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS implantacoes (
                id {pk_type},
                usuario_cs VARCHAR(255) NOT NULL REFERENCES usuarios(usuario) ON DELETE NO ACTION, -- Chave estrangeira para o email do CS
                nome_empresa TEXT NOT NULL,
                status VARCHAR(50) DEFAULT 'andamento' CHECK(status IN ('andamento', 'futura', 'finalizada', 'parada')),
                tipo VARCHAR(50) DEFAULT 'agora' CHECK(tipo IN ('agora', 'futura')),
                data_criacao {timestamp_type} DEFAULT CURRENT_TIMESTAMP,
                data_finalizacao {timestamp_type}, -- Usado para marcar finalização ou parada
                motivo_parada TEXT DEFAULT '',
                -- Detalhes do cliente
                responsavel_cliente TEXT DEFAULT '',
                cargo_responsavel TEXT DEFAULT '',
                telefone_responsavel VARCHAR(50) DEFAULT '',
                email_responsavel VARCHAR(255) DEFAULT '',
                -- Datas importantes
                data_inicio_producao {date_type} DEFAULT NULL,
                data_final_implantacao {date_type} DEFAULT NULL, -- Data prevista/real de fim
                -- Atributos específicos
                chave_oamd TEXT DEFAULT '',
                catraca TEXT DEFAULT '',
                facial TEXT DEFAULT ''
            )
        """)
        # Tabela tarefas: checklist da implantação
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS tarefas (
                id {pk_type},
                implantacao_id INTEGER NOT NULL REFERENCES implantacoes(id) ON DELETE CASCADE,
                tarefa_pai TEXT NOT NULL, -- Módulo/Agrupador
                tarefa_filho TEXT NOT NULL, -- Nome da tarefa específica
                concluida {boolean_type} DEFAULT FALSE,
                ordem INTEGER DEFAULT 0, -- Para ordenação dentro do módulo
                tag VARCHAR(100) DEFAULT '' -- Ex: 'Reunião', 'Ação interna'
            )
        """)
        # Tabela comentarios: comentários associados a tarefas
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS comentarios (
                id {pk_type},
                tarefa_id INTEGER NOT NULL REFERENCES tarefas(id) ON DELETE CASCADE,
                usuario_cs VARCHAR(255) NOT NULL REFERENCES usuarios(usuario) ON DELETE NO ACTION, -- Quem comentou
                texto TEXT NOT NULL,
                data_criacao {timestamp_type} DEFAULT CURRENT_TIMESTAMP,
                imagem_url TEXT DEFAULT NULL -- URL da imagem (Firebase Storage/S3)
            )
        """)
        # Tabela timeline_log: histórico de eventos da implantação
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS timeline_log (
                id {pk_type},
                implantacao_id INTEGER NOT NULL REFERENCES implantacoes(id) ON DELETE CASCADE,
                usuario_cs VARCHAR(255) NOT NULL REFERENCES usuarios(usuario) ON DELETE NO ACTION, -- Quem realizou a ação
                tipo_evento VARCHAR(100) NOT NULL, -- Ex: 'tarefa_alterada', 'status_alterado'
                detalhes TEXT NOT NULL, -- Descrição do evento
                data_criacao {timestamp_type} DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Criação de índices para otimizar consultas
        cur.execute("CREATE INDEX IF NOT EXISTS idx_tarefas_implantacao_id ON tarefas (implantacao_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_comentarios_tarefa_id ON comentarios (tarefa_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_timeline_log_implantacao_id ON timeline_log (implantacao_id)")

        db.commit() # Confirma a criação das tabelas/índices
        cur.close()
        print("Schema do banco de dados verificado/inicializado com sucesso.")


# --- Funções Helper (Formatação de Data, Upload, Lógica de Negócio) ---

def format_date_br(dt_obj, include_time=False):
    """Formata um objeto datetime/date ou string ISO para o formato DD/MM/AAAA [HH:MM:SS]."""
    if not dt_obj:
        return 'N/A'

    # Tenta converter string para objeto datetime/date
    if isinstance(dt_obj, str):
        original_str = dt_obj # Guarda para possível fallback
        try:
            # Tenta formato com hora primeiro
            if ' ' in dt_obj or 'T' in dt_obj:
                 # Remove 'Z' ou timezone offset se houver, strptime não lida bem com eles diretamente
                 dt_obj = dt_obj.replace('Z', '').split('+')[0].split('.')[0]
                 # Tenta alguns formatos comuns
                 for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S'):
                    try:
                        dt_obj = datetime.strptime(dt_obj, fmt)
                        break # Sai do loop se a conversão for bem-sucedida
                    except ValueError:
                        continue # Tenta o próximo formato
                 else: # Se nenhum formato funcionou
                      raise ValueError("Formato de data/hora string não reconhecido")
            # Tenta formato só com data
            else:
                dt_obj = datetime.strptime(dt_obj, '%Y-%m-%d').date()
        except ValueError as e:
            print(f"AVISO: Não foi possível converter a string '{original_str}' para data/hora: {e}")
            return 'Data Inválida' # Retorna indicando erro na string original

    # Verifica se temos um objeto date ou datetime válido após a conversão
    if not isinstance(dt_obj, (datetime, date)):
        print(f"AVISO: Tipo de dado inesperado para formatação de data: {type(dt_obj)}")
        return 'N/A'

    # Define o formato de saída (string para strftime)
    if include_time and isinstance(dt_obj, datetime):
        output_fmt = '%d/%m/%Y %H:%M:%S'
    else:
        output_fmt = '%d/%m/%Y'

    # Tenta formatar e retorna
    try:
        return dt_obj.strftime(output_fmt)
    except ValueError:
        # Pode acontecer com datas muito antigas ou inválidas
        print(f"AVISO: Erro ao formatar objeto data/hora: {dt_obj}")
        return 'Data Inválida'


def format_date_iso_for_json(dt_obj):
    """Formata um objeto datetime/date para string ISO 'YYYY-MM-DD HH:MM:SS' para JSON."""
    if not dt_obj or not isinstance(dt_obj, (datetime, date)):
        return None
    # Converte date para datetime (meia-noite) se necessário
    if isinstance(dt_obj, date) and not isinstance(dt_obj, datetime):
        dt_obj = datetime.combine(dt_obj, datetime.min.time())
    try:
        # Formato ISO padrão sem timezone (mais simples para JSON)
        return dt_obj.strftime('%Y-%m-%d %H:%M:%S')
    except ValueError:
        print(f"AVISO: Erro ao formatar data para ISO JSON: {dt_obj}")
        return None

def allowed_file(filename):
    """Verifica se a extensão do arquivo é permitida."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- Decorador @login_required ---
def login_required(f):
    """
    Decorador para proteger rotas. Verifica se 'user' está na sessão.
    Redireciona para /login se não estiver logado.
    Disponibiliza g.user e g.user_email para a rota protegida.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Verifica se a chave 'user' (contendo o userinfo do Auth0) existe na sessão
        if 'user' not in session:
            flash('Login necessário para acessar esta página.', 'info')
            # Redireciona para a rota /login, que iniciará o fluxo Auth0
            return redirect(url_for('login'))

        # Disponibiliza informações do usuário logado via 'g' (objeto global da requisição)
        g.user = session.get('user') # Dicionário com infos do Auth0
        g.user_email = g.user.get('email') if g.user else None # Pega o email

        # Verificação extra: Garante que temos um email na sessão
        if not g.user_email:
             flash("Sessão inválida ou email não encontrado. Faça login novamente.", "warning")
             # Limpa a sessão e redireciona para o logout completo via Auth0
             session.clear()
             return redirect(url_for('logout'))

        # Se tudo estiver OK, executa a função da rota original
        return f(*args, **kwargs)
    return decorated_function

# --- Rotas de Autenticação (Auth0) ---

@app.route('/login')
def login():
    """Inicia o processo de login redirecionando para o Auth0."""
    print("Iniciando fluxo de login Auth0...")
    session.clear() # Limpa qualquer sessão Flask antiga
    # Monta a URL de redirecionamento para o callback DESTE app
    redirect_uri = url_for('callback', _external=True)
    print(f"Redirecionando para Auth0 com callback para: {redirect_uri}")
    # Usa o Authlib para gerar a URL de autorização do Auth0 e redireciona o usuário
    return auth0.authorize_redirect(redirect_uri=redirect_uri)

@app.route('/callback')
def callback():
    """Rota de callback que o Auth0 chama após o login."""
    print("Recebendo callback do Auth0...")
    try:
        # Troca o código de autorização recebido por tokens (ID Token, Access Token)
        token = auth0.authorize_access_token()
        if not token:
            raise Exception("Falha ao obter token do Auth0.")
        
        # O ID Token contém as informações do usuário (claims OIDC)
        userinfo = token.get('userinfo')

        # Se userinfo não veio no ID Token (menos comum), busca no endpoint /userinfo
        if not userinfo:
            print("Userinfo não veio no token, buscando via endpoint...")
            resp = auth0.get('userinfo')
            resp.raise_for_status() # Lança exceção se a requisição falhar
            userinfo = resp.json()

        # Validação mínima do userinfo
        if not userinfo or not userinfo.get('email'):
             raise Exception("Informações do usuário (userinfo) inválidas ou sem email.")
        
        print(f"Login bem-sucedido via Auth0 para usuário: {userinfo.get('email')}")

        # Guarda as informações do usuário na sessão segura do Flask
        session['user'] = userinfo
        user_email = userinfo.get('email')
        user_name = userinfo.get('name', user_email) # Usa nome, ou email como fallback
        auth0_user_id = userinfo.get('sub') # ID único do usuário no Auth0 ('sub'ject)

        # --- SINCRONIZAÇÃO COM BANCO DE DADOS LOCAL ---
        # Verifica se o usuário já existe no nosso banco de dados pelo email
        try:
            perfil = query_db("SELECT nome FROM perfil_usuario WHERE usuario = %s", (user_email,), one=True)
            
            # Se não existe, cria o registro nas tabelas 'usuarios' e 'perfil_usuario'
            if not perfil:
                print(f"Usuário {user_email} não encontrado no DB local. Criando registro...")
                
                # Verifica se o email já existe na tabela 'usuarios' (pode acontecer se perfil falhou antes)
                usuario_existente = query_db("SELECT usuario FROM usuarios WHERE usuario = %s", (user_email,), one=True)
                if not usuario_existente:
                    # Cria um hash seguro do ID do Auth0 + secret key como senha placeholder
                    # Esta senha NUNCA será usada para login, mas o campo é NOT NULL
                    senha_placeholder = generate_password_hash(auth0_user_id + app.secret_key)
                    execute_db("INSERT INTO usuarios (usuario, senha) VALUES (%s, %s)", (user_email, senha_placeholder))
                    print(f"Registro criado em 'usuarios' para {user_email}.")

                # Cria o perfil do usuário
                execute_db("INSERT INTO perfil_usuario (usuario, nome) VALUES (%s, %s)", (user_email, user_name))
                print(f"Perfil criado em 'perfil_usuario' para {user_email}.")
            else:
                 print(f"Usuário {user_email} já existe no DB local.")

        except Exception as db_error:
            # Loga o erro mas permite que o usuário continue para o dashboard
            print(f"ERRO NÃO FATAL ao sincronizar usuário {user_email} com DB local: {db_error}")
            flash("Ocorreu um problema ao sincronizar seu perfil com nossos registros. Algumas informações podem não estar atualizadas.", "warning")
            # Não impede o login, mas registra o problema

        # Redireciona para o dashboard após login e sincronização (ou tentativa)
        return redirect(url_for('dashboard'))

    except Exception as e:
        # Captura erros gerais durante o callback (token inválido, falha na rede, etc.)
        print(f"ERRO CRÍTICO no callback do Auth0: {e}")
        flash(f"Erro durante a autenticação: {e}. Tente novamente.", "error")
        session.clear() # Limpa a sessão em caso de erro grave
        return redirect(url_for('home')) # Redireciona para a página inicial/login

@app.route('/logout')
def logout():
    """Desloga o usuário da sessão Flask e redireciona para o logout do Auth0."""
    print("Iniciando processo de logout...")
    # Limpa a sessão do Flask (remove 'user')
    session.clear()
    
    # Monta a URL de logout do Auth0, incluindo parâmetros necessários:
    # returnTo: Para onde o Auth0 deve redirecionar o usuário após o logout
    # client_id: Identifica qual aplicação está solicitando o logout
    params = {
        'returnTo': url_for('home', _external=True), # Redireciona para a home do app
        'client_id': auth0_client_id
    }
    # Constrói a URL completa do endpoint de logout do Auth0
    logout_url = f"https://{auth0_domain}/v2/logout?{urlencode(params)}"
    print(f"Redirecionando para logout no Auth0: {logout_url}")
    # Redireciona o navegador do usuário para o Auth0 para encerrar a sessão lá também
    return redirect(logout_url)

# --- Rotas Principais da Aplicação ---

@app.route('/')
def home():
    """Página inicial. Redireciona para o dashboard se logado, senão mostra login."""
    if 'user' in session:
        # Se o usuário já está logado (tem 'user' na sessão), vai para o dashboard
        return redirect(url_for('dashboard'))
    # Se não está logado, renderiza a página de login/boas-vindas
    return render_template('login.html')

@app.route('/dashboard')
@login_required # Protege a rota: só acessível se logado
def dashboard():
    """Exibe o dashboard principal com métricas e listas de implantações."""
    user_email = g.user_email # Obtém o email do usuário logado (definido pelo @login_required)
    user_info = g.user # Obtém todas as infos do usuário da sessão (para passar ao template)

    try:
        # Busca dados do dashboard e métricas do banco de dados
        dashboard_data, metrics = get_dashboard_data(user_email)
        # Busca o perfil local do usuário
        perfil = query_db("SELECT * FROM perfil_usuario WHERE usuario = %s", (user_email,), one=True)
        perfil_data = perfil if perfil else {} # Usa dados do perfil ou um dict vazio

        # Define métricas padrão e mescla com as do banco e as calculadas
        default_metrics = {
            'nome': user_info.get('name', user_email), # Pega nome do Auth0, fallback para email
            'impl_andamento': 0, 'impl_finalizadas': 0, 'impl_paradas': 0,
            'progresso_medio_carteira': 0, 'impl_andamento_total': 0,
            'implantacoes_atrasadas': 0, 'implantacoes_futuras': 0
        }
        # Mescla as métricas: calculadas > perfil_db > padrão
        final_metrics = {**default_metrics, **perfil_data, **metrics}

        # Renderiza o template do dashboard passando todos os dados necessários
        return render_template('dashboard.html',
                               user_info=user_info, # Infos do Auth0 para o cabeçalho
                               metrics=final_metrics,
                               # Passa as listas de implantações separadamente
                               implantacoes_andamento=dashboard_data.get('andamento', []),
                               implantacoes_futuras=dashboard_data.get('futuras', []),
                               implantacoes_finalizadas=dashboard_data.get('finalizadas', []),
                               implantacoes_paradas=dashboard_data.get('paradas', []),
                               implantacoes_atrasadas=dashboard_data.get('atrasadas', []),
                               cargos_responsavel=CARGOS_RESPONSAVEL # Lista de cargos para o modal
                               )
    except Exception as e:
        print(f"ERRO ao carregar dashboard para {user_email}: {e}")
        flash("Erro ao carregar os dados do dashboard. Tente atualizar a página.", "error")
        # Renderiza o template com dados vazios ou uma mensagem de erro
        return render_template('dashboard.html', user_info=user_info, error="Falha ao carregar dados.")


@app.route('/implantacao/<int:impl_id>')
@login_required # Protege a rota
def ver_implantacao(impl_id):
    """Exibe os detalhes de uma implantação específica (checklist, timeline)."""
    usuario_cs_email = g.user_email # Email do usuário logado
    user_info = g.user # Infos completas para passar ao template (ex: nome no cabeçalho)

    try:
        # Busca a implantação no banco, garantindo que pertence ao usuário logado
        implantacao = query_db("SELECT * FROM implantacoes WHERE id = %s AND usuario_cs = %s", (impl_id, usuario_cs_email), one=True)
        
        # Se não encontrou ou não pertence ao usuário, redireciona
        if not implantacao:
            flash('Implantação não encontrada ou acesso negado.', 'error')
            return redirect(url_for('dashboard'))

        # Formata as datas da implantação para exibição no template (DD/MM/AAAA HH:MM:SS ou DD/MM/AAAA)
        implantacao['data_criacao_fmt_dt_hr'] = format_date_br(implantacao.get('data_criacao'), True)
        implantacao['data_criacao_fmt_d'] = format_date_br(implantacao.get('data_criacao'), False)
        implantacao['data_finalizacao_fmt_d'] = format_date_br(implantacao.get('data_finalizacao'), False)
        implantacao['data_inicio_producao_fmt_d'] = format_date_br(implantacao.get('data_inicio_producao'), False)
        implantacao['data_final_implantacao_fmt_d'] = format_date_br(implantacao.get('data_final_implantacao'), False)

        # Calcula o progresso (total vs concluídas)
        counts = query_db("SELECT COUNT(*) as total, SUM(CASE WHEN concluida THEN 1 ELSE 0 END) as done FROM tarefas WHERE implantacao_id = %s", (impl_id,), one=True)
        total_t, concl_t = (counts.get('total') or 0), (counts.get('done') or 0)
        progresso = int(round((concl_t / total_t) * 100)) if total_t > 0 else 0

        # Busca tarefas e agrupa por módulo (tarefa_pai)
        tarefas_raw = query_db("SELECT * FROM tarefas WHERE implantacao_id = %s ORDER BY tarefa_pai, ordem", (impl_id,))
        
        # Busca comentários associados às tarefas desta implantação
        comentarios_raw = query_db("""
            SELECT c.*, p.nome as usuario_nome
            FROM comentarios c
            LEFT JOIN perfil_usuario p ON c.usuario_cs = p.usuario -- Usa LEFT JOIN caso perfil não exista
            WHERE c.tarefa_id IN (SELECT id FROM tarefas WHERE implantacao_id = %s)
            ORDER BY c.data_criacao DESC -- Mais recentes primeiro na lista de comentários
        """, (impl_id,))

        # Agrupa comentários por tarefa_id e formata data
        comentarios_por_tarefa = {}
        for c in comentarios_raw:
            c['data_criacao_fmt_d'] = format_date_br(c.get('data_criacao')) # Formata data do comentário
            # Garante que usuario_nome tenha um valor (fallback para email se perfil não encontrado)
            c['usuario_nome'] = c.get('usuario_nome') or c.get('usuario_cs')
            comentarios_por_tarefa.setdefault(c['tarefa_id'], []).append(c)

        # Agrupa tarefas por módulo (tarefa_pai) e adiciona os comentários
        tarefas_temp = {}
        for t in tarefas_raw:
            t['comentarios'] = comentarios_por_tarefa.get(t['id'], []) # Adiciona lista de comentários à tarefa
            tarefas_temp.setdefault(t['tarefa_pai'], []).append(t)

        # Ordena os módulos: primeiro os padrão na ordem definida, depois os personalizados
        tarefas_agrupadas = OrderedDict()
        # Adiciona módulos padrão na ordem correta
        for modulo_padrao in TAREFAS_PADRAO:
            if modulo_padrao in tarefas_temp:
                # Ordena tarefas dentro do módulo pela coluna 'ordem'
                 tarefas_agrupadas[modulo_padrao] = sorted(tarefas_temp.pop(modulo_padrao), key=lambda x: x.get('ordem', 0))
        # Adiciona módulos personalizados restantes (ordenados alfabeticamente)
        for modulo_restante in sorted(tarefas_temp.keys()):
             tarefas_agrupadas[modulo_restante] = sorted(tarefas_temp[modulo_restante], key=lambda x: x.get('ordem', 0))

        # Busca nome local do usuário logado (pode ser diferente do Auth0 se não sincronizado)
        perfil_local = query_db("SELECT nome FROM perfil_usuario WHERE usuario = %s", (usuario_cs_email,), one=True)
        nome_usuario_logado = perfil_local.get('nome') if perfil_local else usuario_cs_email

        # Busca o histórico (timeline log) da implantação
        logs_timeline = query_db("""
            SELECT tl.*, COALESCE(p.nome, tl.usuario_cs) as usuario_nome -- Fallback para email se perfil não existe
            FROM timeline_log tl
            LEFT JOIN perfil_usuario p ON tl.usuario_cs = p.usuario
            WHERE tl.implantacao_id = %s
            ORDER BY tl.data_criacao DESC -- Mais recentes primeiro
        """, (impl_id,))

        # Formata datas dos logs
        for log in logs_timeline:
            log['data_criacao_fmt_dt_hr'] = format_date_br(log.get('data_criacao'), True)

        # Renderiza o template de detalhes passando todos os dados
        return render_template('implantacao_detalhes.html',
                               user_info=user_info, # Infos do Auth0 para cabeçalho, etc.
                               implantacao=implantacao,
                               tarefas_agrupadas=tarefas_agrupadas,
                               progresso_porcentagem=progresso,
                               nome_usuario_logado=nome_usuario_logado, # Nome do perfil local
                               email_usuario_logado=usuario_cs_email, # Email para verificações JS (ex: botão excluir comentário)
                               justificativas_parada=JUSTIFICATIVAS_PARADA, # Para o modal de Parar
                               logs_timeline=logs_timeline,
                               cargos_responsavel=CARGOS_RESPONSAVEL # Para o modal de Editar Detalhes
                               )
    except Exception as e:
        print(f"ERRO ao carregar detalhes da implantação ID {impl_id} para {usuario_cs_email}: {e}")
        flash("Erro ao carregar os detalhes da implantação. Tente novamente.", "error")
        return redirect(url_for('dashboard'))

# --- Rotas de Ação (CRUD Implantações - Protegidas) ---
# Lembre-se de adicionar @login_required e usar g.user_email

@app.route('/criar_implantacao', methods=['POST'])
@login_required
def criar_implantacao():
    """Cria uma nova implantação e suas tarefas padrão."""
    usuario_cs_email = g.user_email
    nome_empresa = request.form.get('nome_empresa', '').strip()
    tipo = request.form.get('tipo', 'agora') # 'agora' ou 'futura'

    # Validação simples
    if not nome_empresa:
        flash('Nome da empresa não pode estar vazio.', 'error')
        return redirect(url_for('dashboard'))
    if tipo not in ['agora', 'futura']:
        flash('Tipo de implantação inválido.', 'error')
        return redirect(url_for('dashboard'))

    try:
        # Insere a nova implantação no banco
        implantacao_id = execute_db(
            "INSERT INTO implantacoes (usuario_cs, nome_empresa, tipo, data_criacao) VALUES (%s, %s, %s, %s)",
            (usuario_cs_email, nome_empresa, tipo, datetime.now())
        )
        if not implantacao_id:
            raise Exception("Falha ao obter ID da nova implantação do banco de dados.")

        # Loga o evento de criação
        logar_timeline(implantacao_id, usuario_cs_email, 'implantacao_criada', f'Implantação "{nome_empresa}" (Tipo: {tipo.capitalize()}) criada.')

        # Cria as tarefas padrão para a nova implantação
        tasks_added = 0
        for modulo, tarefas_info in TAREFAS_PADRAO.items():
            for i, tarefa_info in enumerate(tarefas_info, 1): # Começa ordem em 1
                execute_db(
                    "INSERT INTO tarefas (implantacao_id, tarefa_pai, tarefa_filho, ordem, tag) VALUES (%s, %s, %s, %s, %s)",
                    (implantacao_id, modulo, tarefa_info['nome'], i, tarefa_info.get('tag', ''))
                )
                tasks_added += 1
        
        print(f"{tasks_added} tarefas padrão adicionadas para implantação ID {implantacao_id}.")
        flash(f'Implantação "{nome_empresa}" criada com sucesso!', 'success')
        # Redireciona para a página de detalhes da nova implantação
        return redirect(url_for('ver_implantacao', impl_id=implantacao_id))

    except Exception as e:
        print(f"ERRO CRÍTICO ao criar implantação ou tarefas para {usuario_cs_email}: {e}")
        flash(f'Erro grave ao criar implantação: {e}. Contate o suporte.', 'error')
        return redirect(url_for('dashboard'))


@app.route('/iniciar_implantacao', methods=['POST'])
@login_required
def iniciar_implantacao():
    """Muda o status de uma implantação 'futura' para 'andamento'."""
    usuario_cs_email = g.user_email
    implantacao_id = request.form.get('implantacao_id')
    
    if not implantacao_id:
        flash('ID da implantação não fornecido.', 'error')
        return redirect(url_for('dashboard'))

    try:
        # Verifica se a implantação existe, pertence ao usuário e é 'futura'
        impl = query_db("SELECT usuario_cs, nome_empresa, tipo FROM implantacoes WHERE id = %s", (implantacao_id,), one=True)
        
        if not impl:
            flash('Implantação não encontrada.', 'error')
            return redirect(url_for('dashboard'))
        if impl.get('usuario_cs') != usuario_cs_email:
            flash('Você não tem permissão para alterar esta implantação.', 'error')
            return redirect(url_for('dashboard'))
        if impl.get('tipo') != 'futura':
            flash('Apenas implantações futuras podem ser iniciadas.', 'warning')
            # Redireciona de volta para detalhes se estava lá, senão dashboard
            return redirect(request.referrer or url_for('dashboard'))

        # Atualiza o status e tipo (redundante, mas garante), e data de criação para agora
        execute_db("UPDATE implantacoes SET tipo = 'agora', status = 'andamento', data_criacao = %s WHERE id = %s", (datetime.now(), implantacao_id))
        
        # Loga o evento
        logar_timeline(implantacao_id, usuario_cs_email, 'status_alterado', f'Implantação "{impl.get("nome_empresa", "N/A")}" iniciada (movida de "Futura" para "Em Andamento").')
        flash('Implantação iniciada com sucesso!', 'success')
        # Redireciona para a página de detalhes da implantação iniciada
        return redirect(url_for('ver_implantacao', impl_id=implantacao_id))

    except Exception as e:
        print(f"Erro ao iniciar implantação ID {implantacao_id}: {e}")
        flash('Erro ao iniciar implantação.', 'error')
        return redirect(url_for('dashboard'))


@app.route('/finalizar_implantacao', methods=['POST'])
@login_required
def finalizar_implantacao():
    """Marca uma implantação 'andamento' como 'finalizada'."""
    usuario_cs_email = g.user_email
    implantacao_id = request.form.get('implantacao_id')
    redirect_target = request.form.get('redirect_to', 'dashboard') # Onde voltar?

    if not implantacao_id:
        flash('ID da implantação não fornecido.', 'error')
        return redirect(url_for('dashboard'))

    try:
        # Verifica se a implantação existe, pertence ao usuário e está 'andamento'
        impl = query_db("SELECT usuario_cs, nome_empresa, status FROM implantacoes WHERE id = %s", (implantacao_id,), one=True)
        
        if not impl:
             flash('Implantação não encontrada.', 'error')
             return redirect(url_for('dashboard'))
        if impl.get('usuario_cs') != usuario_cs_email:
             flash('Você não tem permissão para alterar esta implantação.', 'error')
             return redirect(url_for('dashboard'))
        if impl.get('status') != 'andamento':
             flash('Apenas implantações em andamento podem ser finalizadas manualmente.', 'warning')
             # Redireciona para o local apropriado
             dest = 'ver_implantacao' if redirect_target == 'detalhes' else 'dashboard'
             return redirect(url_for(dest, impl_id=implantacao_id if dest == 'ver_implantacao' else None))

        # Atualiza status e data de finalização
        execute_db("UPDATE implantacoes SET status = 'finalizada', data_finalizacao = CURRENT_TIMESTAMP WHERE id = %s", (implantacao_id,))
        
        # Atualiza métricas do perfil (se existir)
        execute_db("UPDATE perfil_usuario SET impl_finalizadas = impl_finalizadas + 1, impl_andamento_total = GREATEST(0, impl_andamento_total - 1) WHERE usuario = %s", (usuario_cs_email,))
        
        # Loga o evento
        logar_timeline(implantacao_id, usuario_cs_email, 'status_alterado', f'Implantação "{impl.get("nome_empresa", "N/A")}" marcada como "Finalizada" manualmente.')
        flash('Implantação finalizada com sucesso!', 'success')

    except Exception as e:
        print(f"Erro ao finalizar implantação ID {implantacao_id}: {e}")
        flash('Erro ao finalizar implantação.', 'error')

    # Redireciona para o local apropriado
    dest = 'ver_implantacao' if redirect_target == 'detalhes' else 'dashboard'
    return redirect(url_for(dest, impl_id=implantacao_id if dest == 'ver_implantacao' else None))


@app.route('/parar_implantacao', methods=['POST'])
@login_required
def parar_implantacao():
    """Marca uma implantação 'andamento' como 'parada' com um motivo."""
    usuario_cs_email = g.user_email
    implantacao_id = request.form.get('implantacao_id')
    motivo = request.form.get('motivo_parada', '').strip()
    redirect_target = request.form.get('redirect_to', 'detalhes') # Geralmente chamado de detalhes

    # Validações
    if not implantacao_id:
         flash('ID da implantação não fornecido.', 'error')
         return redirect(url_for('dashboard'))
    if not motivo:
         flash('O motivo da parada é obrigatório.', 'error')
         # Tenta voltar para a página de detalhes onde o modal está
         return redirect(url_for('ver_implantacao', impl_id=implantacao_id))

    try:
        # Verifica se a implantação existe, pertence ao usuário e está 'andamento'
        impl = query_db("SELECT usuario_cs, nome_empresa, status FROM implantacoes WHERE id = %s", (implantacao_id,), one=True)

        if not impl:
            flash('Implantação não encontrada.', 'error')
            return redirect(url_for('dashboard'))
        if impl.get('usuario_cs') != usuario_cs_email:
            flash('Você não tem permissão para alterar esta implantação.', 'error')
            return redirect(url_for('dashboard'))
        if impl.get('status') != 'andamento':
            flash('Apenas implantações em andamento podem ser paradas.', 'warning')
            return redirect(url_for('ver_implantacao', impl_id=implantacao_id))

        # Atualiza status, motivo e data (usando data_finalizacao para data da parada)
        execute_db("UPDATE implantacoes SET status = 'parada', data_finalizacao = CURRENT_TIMESTAMP, motivo_parada = %s WHERE id = %s", (motivo, implantacao_id))
        
        # Atualiza métricas do perfil
        execute_db("UPDATE perfil_usuario SET impl_paradas = impl_paradas + 1, impl_andamento_total = GREATEST(0, impl_andamento_total - 1) WHERE usuario = %s", (usuario_cs_email,))
        
        # Loga o evento
        logar_timeline(implantacao_id, usuario_cs_email, 'status_alterado', f'Implantação "{impl.get("nome_empresa", "N/A")}" marcada como "Parada". Motivo: {motivo}')
        flash('Implantação parada com sucesso.', 'success')

    except Exception as e:
        print(f"Erro ao parar implantação ID {implantacao_id}: {e}")
        flash('Erro ao parar implantação.', 'error')

    # Volta para a página de detalhes por padrão
    return redirect(url_for('ver_implantacao', impl_id=implantacao_id))


@app.route('/retomar_implantacao', methods=['POST'])
@login_required
def retomar_implantacao():
    """Muda o status de uma implantação 'parada' de volta para 'andamento'."""
    usuario_cs_email = g.user_email
    implantacao_id = request.form.get('implantacao_id')
    redirect_to = request.form.get('redirect_to', 'dashboard') # dashboard ou detalhes

    if not implantacao_id:
        flash('ID da implantação não fornecido.', 'error')
        return redirect(url_for('dashboard'))

    try:
        # Verifica se a implantação existe, pertence ao usuário e está 'parada'
        impl = query_db("SELECT usuario_cs, nome_empresa, status FROM implantacoes WHERE id = %s", (implantacao_id,), one=True)

        if not impl:
            flash('Implantação não encontrada.', 'error')
            return redirect(url_for('dashboard'))
        if impl.get('usuario_cs') != usuario_cs_email:
            flash('Você não tem permissão para alterar esta implantação.', 'error')
            return redirect(url_for('dashboard'))
        if impl.get('status') != 'parada':
            flash('Apenas implantações paradas podem ser retomadas.', 'warning')
            dest = 'ver_implantacao' if redirect_to == 'detalhes' else 'dashboard'
            return redirect(url_for(dest, impl_id=implantacao_id if dest == 'ver_implantacao' else None))

        # Atualiza status, limpa motivo e data de finalização/parada
        execute_db("UPDATE implantacoes SET status = 'andamento', data_finalizacao = NULL, motivo_parada = '' WHERE id = %s", (implantacao_id,))
        
        # Atualiza métricas do perfil
        execute_db("UPDATE perfil_usuario SET impl_paradas = GREATEST(0, impl_paradas - 1), impl_andamento_total = impl_andamento_total + 1 WHERE usuario = %s", (usuario_cs_email,))
        
        # Loga o evento
        logar_timeline(implantacao_id, usuario_cs_email, 'status_alterado', f'Implantação "{impl.get("nome_empresa", "N/A")}" retomada (status alterado de "Parada" para "Em Andamento").')
        flash('Implantação retomada com sucesso.', 'success')

    except Exception as e:
        print(f"Erro ao retomar implantação ID {implantacao_id}: {e}")
        flash('Erro ao retomar implantação.', 'error')

    # Redireciona para o local apropriado
    dest = 'ver_implantacao' if redirect_to == 'detalhes' else 'dashboard'
    return redirect(url_for(dest, impl_id=implantacao_id if dest == 'ver_implantacao' else None))


@app.route('/atualizar_detalhes_empresa', methods=['POST'])
@login_required
def atualizar_detalhes_empresa():
    """Atualiza os campos de detalhes do cliente/implantação."""
    usuario_cs_email = g.user_email
    implantacao_id = request.form.get('implantacao_id')
    redirect_to = request.form.get('redirect_to', 'dashboard') # dashboard ou detalhes

    if not implantacao_id:
        flash('ID da implantação não fornecido.', 'error')
        return redirect(url_for('dashboard'))

    # Verifica permissão
    if not query_db("SELECT id FROM implantacoes WHERE id = %s AND usuario_cs = %s", (implantacao_id, usuario_cs_email), one=True):
        flash('Você não tem permissão para editar esta implantação.', 'error')
        return redirect(url_for('dashboard'))

    try:
        # Pega dados do formulário, tratando datas vazias como None
        data_inicio_prod = request.form.get('data_inicio_producao') or None
        data_final_impl = request.form.get('data_final_implantacao') or None
        
        # Prepara a query de atualização
        query = """
            UPDATE implantacoes SET
                responsavel_cliente = %s,
                cargo_responsavel = %s,
                telefone_responsavel = %s,
                email_responsavel = %s,
                data_inicio_producao = %s,
                data_final_implantacao = %s,
                chave_oamd = %s,
                catraca = %s,
                facial = %s
            WHERE id = %s AND usuario_cs = %s
        """
        args = (
            request.form.get('responsavel_cliente', '').strip(),
            request.form.get('cargo_responsavel', '').strip(),
            request.form.get('telefone_responsavel', '').strip(),
            request.form.get('email_responsavel', '').strip(),
            data_inicio_prod, # Pode ser None
            data_final_impl,  # Pode ser None
            request.form.get('chave_oamd', '').strip(),
            request.form.get('catraca', '').strip(),
            request.form.get('facial', '').strip(),
            implantacao_id,
            usuario_cs_email
        )
        
        execute_db(query, args)
        
        # Loga o evento
        logar_timeline(implantacao_id, usuario_cs_email, 'detalhes_alterados', 'Os detalhes da empresa/cliente foram atualizados.')
        flash('Detalhes da empresa atualizados com sucesso!', 'success')

    except Exception as e:
        print(f"Erro ao atualizar detalhes da implantação ID {implantacao_id}: {e}")
        flash('Erro ao atualizar detalhes da empresa.', 'error')

    # Redireciona para o local apropriado
    dest = 'ver_implantacao' if redirect_to == 'detalhes' else 'dashboard'
    return redirect(url_for(dest, impl_id=implantacao_id if dest == 'ver_implantacao' else None))


@app.route('/excluir_implantacao', methods=['POST'])
@login_required
def excluir_implantacao():
    """Exclui permanentemente uma implantação e seus dados associados."""
    usuario_cs_email = g.user_email
    implantacao_id = request.form.get('implantacao_id')

    if not implantacao_id:
        flash('ID da implantação inválido.', 'error')
        return redirect(url_for('dashboard'))

    # Verifica permissão
    if not query_db("SELECT id FROM implantacoes WHERE id = %s AND usuario_cs = %s", (implantacao_id, usuario_cs_email), one=True):
        flash('Permissão negada ou implantação não encontrada.', 'error')
        return redirect(url_for('dashboard'))

    try:
        # --- EXCLUIR ARQUIVOS DO STORAGE (Importante!) ---
        # Busca URLs das imagens associadas a esta implantação
        comentarios_img = query_db("""
            SELECT c.imagem_url FROM comentarios c
            JOIN tarefas t ON c.tarefa_id = t.id
            WHERE t.implantacao_id = %s AND c.imagem_url IS NOT NULL AND c.imagem_url != ''
        """, (implantacao_id,))

        # Tenta excluir cada imagem do Firebase Storage (ou S3)
        # DESCOMENTE E ADAPTE QUANDO IMPLEMENTAR O STORAGE
        # bucket = storage.bucket() # Obter o bucket do Firebase
        for c in comentarios_img:
            img_url = c.get('imagem_url')
            if img_url:
                try:
                    # Extrair o 'blob_path' da URL (depende de como você salvou)
                    # Exemplo: se URL é https://storage.googleapis.com/bucket/path/to/file.jpg
                    # blob_path seria "path/to/file.jpg"
                    # blob_path = "/".join(urlparse(img_url).path.split('/')[2:]) # Adapte conforme necessário!

                    # blob = bucket.blob(blob_path)
                    # if blob.exists():
                    #     blob.delete()
                    #     print(f"Arquivo excluído do Storage: {blob_path}")
                    # else:
                    #     print(f"AVISO: Arquivo não encontrado no Storage para exclusão: {blob_path}")
                     print(f"Lembrete: Implementar exclusão do Storage para URL: {img_url}") # Placeholder
                except Exception as storage_error:
                    # Loga o erro mas continua a exclusão do banco
                    print(f"ERRO ao excluir arquivo do Storage ({img_url}): {storage_error}")
        # ----------------------------------------------------

        # Exclui a implantação do banco de dados (ON DELETE CASCADE cuidará das tarefas, comentários, logs)
        execute_db("DELETE FROM implantacoes WHERE id = %s", (implantacao_id,))
        
        # Atualiza métricas (difícil saber o status anterior, pode precisar recalcular tudo ou simplificar)
        # Poderia buscar o status antes de deletar para decrementar o contador certo
        # execute_db("UPDATE perfil_usuario SET ... WHERE usuario = %s", (usuario_cs_email,)) # Implementar lógica de métricas

        flash('Implantação excluída permanentemente com sucesso.', 'success')
    except Exception as e:
        print(f"Erro ao excluir implantação ID {implantacao_id}: {e}")
        flash('Erro ao excluir a implantação.', 'error')

    # Sempre volta para o dashboard após excluir
    return redirect(url_for('dashboard'))


# --- Rotas API (Tarefas, Comentários, Ordenação - Protegidas) ---

@app.route('/toggle_tarefa/<int:tarefa_id>', methods=['POST'])
@login_required
def toggle_tarefa(tarefa_id):
    """Marca/desmarca uma tarefa como concluída via API (JSON)."""
    usuario_cs_email = g.user_email
    try:
        # Busca tarefa e verifica permissão
        tarefa = query_db("""
            SELECT t.*, i.usuario_cs, i.id as implantacao_id
            FROM tarefas t JOIN implantacoes i ON t.implantacao_id = i.id
            WHERE t.id = %s
        """, (tarefa_id,), one=True)

        if not tarefa or tarefa.get('usuario_cs') != usuario_cs_email:
            return jsonify({'ok': False, 'error': 'forbidden'}), 403

        # Determina o novo status e o ID da implantação
        novo_status_bool = not tarefa.get('concluida', False)
        impl_id = tarefa.get('implantacao_id')

        # Atualiza o status da tarefa no banco
        execute_db("UPDATE tarefas SET concluida = %s WHERE id = %s", (novo_status_bool, tarefa_id))
        
        # Loga o evento de alteração da tarefa
        agora_str_br = datetime.now().strftime('%d/%m/%Y %H:%M')
        detalhe = f"Atualização tarefa: {tarefa['tarefa_filho']}.\n{'Concluída: ' + agora_str_br if novo_status_bool else 'Status: Não Concluída.'}"
        logar_timeline(impl_id, usuario_cs_email, 'tarefa_alterada', detalhe)

        # Verifica se a implantação deve ser auto-finalizada
        finalizada, log_finalizacao = auto_finalizar_implantacao(impl_id, usuario_cs_email)

        # Recalcula o progresso da implantação
        counts = query_db("SELECT COUNT(*) as total, SUM(CASE WHEN concluida THEN 1 ELSE 0 END) as done FROM tarefas WHERE implantacao_id = %s", (impl_id,), one=True)
        total, done = (counts.get('total') or 0), (counts.get('done') or 0)
        novo_prog = int(round((done / total) * 100)) if total > 0 else 0

        # Busca nome local e último log da tarefa para retornar ao frontend
        perfil = query_db("SELECT nome FROM perfil_usuario WHERE usuario = %s", (usuario_cs_email,), one=True)
        nome = perfil.get('nome') if perfil else usuario_cs_email
        log_tarefa = query_db("SELECT *, %s as usuario_nome FROM timeline_log WHERE implantacao_id = %s AND tipo_evento = 'tarefa_alterada' ORDER BY id DESC LIMIT 1", (nome, impl_id), one=True)
        
        # Formata datas dos logs para JSON (ISO)
        if log_tarefa: log_tarefa['data_criacao'] = format_date_iso_for_json(log_tarefa.get('data_criacao'))
        # log_finalizacao já vem formatado de auto_finalizar_implantacao

        # Retorna sucesso e dados atualizados para o frontend
        return jsonify({
            'ok': True,
            'novo_status': 1 if novo_status_bool else 0, # 1 para concluída, 0 para não
            'implantacao_finalizada': finalizada,
            'novo_progresso': novo_prog,
            'log_tarefa': log_tarefa,
            'log_finalizacao': log_finalizacao
        })
    except Exception as e:
        print(f"ERRO ao alternar tarefa ID {tarefa_id}: {e}")
        return jsonify({'ok': False, 'error': f"Erro interno do servidor: {e}"}), 500


@app.route('/adicionar_comentario/<int:tarefa_id>', methods=['POST'])
@login_required
def adicionar_comentario(tarefa_id):
    """Adiciona um comentário (texto e/ou imagem) a uma tarefa via API (JSON)."""
    usuario_cs_email = g.user_email
    texto = request.form.get('comentario', '')[:8000].strip() # Limita tamanho do texto
    img_url = None # URL virá do Storage na nuvem

    # --- LÓGICA DE UPLOAD PARA FIREBASE STORAGE (ou S3) ---
    # Esta parte PRECISA ser implementada corretamente
    if 'imagem' in request.files:
        file = request.files.get('imagem')
        if file and file.filename and allowed_file(file.filename):
            try:
                # 1. Gerar nome único para o arquivo
                filename = secure_filename(file.filename)
                nome_base, extensao = os.path.splitext(filename)
                # Inclui ID da tarefa e timestamp para garantir unicidade e organização
                nome_unico = f"{nome_base}_task{tarefa_id}_{int(datetime.now().timestamp())}{extensao}"

                # 2. Definir o caminho no Storage (ex: comentarios/impl_ID/tarefa_ID/nome_unico.jpg)
                # Buscar implantacao_id primeiro
                tarefa_info_temp = query_db("SELECT implantacao_id FROM tarefas WHERE id = %s", (tarefa_id,), one=True)
                if not tarefa_info_temp: raise Exception("Tarefa não encontrada para upload.")
                impl_id_temp = tarefa_info_temp.get('implantacao_id')
                
                blob_path = f"comentarios/impl_{impl_id_temp}/tarefa_{tarefa_id}/{nome_unico}"
                
                print(f"Tentando upload para Storage: {blob_path}")

                # 3. Fazer upload usando o SDK (ex: firebase-admin)
                # DESCOMENTE e preencha quando firebase_admin estiver inicializado
                # bucket = storage.bucket() # Obter bucket configurado
                # blob = bucket.blob(blob_path)
                
                # Envia o arquivo para o Firebase Storage
                # blob.upload_from_file(file, content_type=file.content_type)
                
                # 4. Tornar o arquivo público (se necessário) e obter a URL
                # blob.make_public()
                # img_url = blob.public_url # Esta é a URL que será salva no banco

                print(f"SUCESSO (Simulado): Upload para {blob_path}. URL pública seria: {img_url}") # Simulação

                # *** Placeholder - Remove after implementing Storage ***
                img_url = f"/placeholder/{nome_unico}" # URL placeholder
                print(f"AVISO: Usando URL placeholder para imagem: {img_url}. Implementar Storage!")
                # ******************************************************

            except Exception as e:
                print(f"ERRO CRÍTICO durante upload para Storage: {e}")
                # Pode retornar erro ou apenas logar e continuar com texto
                return jsonify({'ok': False, 'error': f'Falha no upload da imagem: {e}'}), 500
        elif file and file.filename and not allowed_file(file.filename):
             return jsonify({'ok': False, 'error': 'Tipo de arquivo de imagem não permitido.'}), 400

    # Valida se há texto ou imagem
    if not texto and not img_url:
        return jsonify({'ok': False, 'error': 'Comentário vazio (sem texto ou imagem válida).'}), 400

    try:
        # Verifica permissão na tarefa (após tentativa de upload)
        tarefa = query_db("SELECT i.usuario_cs, i.id as implantacao_id, t.tarefa_filho FROM tarefas t JOIN implantacoes i ON t.implantacao_id = i.id WHERE t.id = %s", (tarefa_id,), one=True)
        if not tarefa or tarefa.get('usuario_cs') != usuario_cs_email:
            # Se deu erro aqui APÓS upload, idealmente deletaríamos a imagem do Storage
            print(f"AVISO: Upload feito para {img_url} mas usuário {usuario_cs_email} não tem permissão na tarefa {tarefa_id}.")
            return jsonify({'ok': False, 'error': 'forbidden'}), 403

        # Insere o comentário no banco de dados com a URL da imagem (do Storage)
        agora = datetime.now()
        novo_id = execute_db(
            "INSERT INTO comentarios (tarefa_id, usuario_cs, texto, data_criacao, imagem_url) VALUES (%s, %s, %s, %s, %s)",
            (tarefa_id, usuario_cs_email, texto, agora, img_url)
        )
        if not novo_id: raise Exception("Falha ao obter ID do novo comentário do banco de dados.")

        # Loga o evento na timeline
        detalhe = f"Novo comentário em '{tarefa['tarefa_filho']}':\n{texto}" if texto else f"Nova imagem adicionada em '{tarefa['tarefa_filho']}'."
        if texto and img_url: detalhe = f"Novo comentário em '{tarefa['tarefa_filho']}':\n{texto}\n[Imagem Anexada]"
        logar_timeline(tarefa['implantacao_id'], usuario_cs_email, 'novo_comentario', detalhe)

        # Prepara dados de retorno para o frontend (incluindo o último log)
        perfil = query_db("SELECT nome FROM perfil_usuario WHERE usuario = %s", (usuario_cs_email,), one=True)
        nome = perfil.get('nome') if perfil else usuario_cs_email
        log_com = query_db("SELECT *, %s as usuario_nome FROM timeline_log WHERE implantacao_id = %s AND tipo_evento = 'novo_comentario' ORDER BY id DESC LIMIT 1", (nome, tarefa['implantacao_id']), one=True)
        
        # Formata datas para JSON (ISO)
        data_criacao_str = format_date_iso_for_json(agora)
        if log_com: log_com['data_criacao'] = format_date_iso_for_json(log_com.get('data_criacao'))

        # Retorna sucesso e os dados do novo comentário + log
        return jsonify({
            'ok': True,
            'comentario': {
                'id': novo_id,
                'tarefa_id': tarefa_id,
                'usuario_cs': usuario_cs_email,
                'usuario_nome': nome,
                'texto': texto,
                'imagem_url': img_url, # A URL PÚBLICA DO STORAGE
                'data_criacao': data_criacao_str # Data formatada para JS
            },
            'log_comentario': log_com
        })
    except Exception as e:
        print(f"ERRO ao salvar comentário na tarefa {tarefa_id}: {e}")
        # Se deu erro APÓS upload, idealmente deletaríamos a imagem do Storage
        if img_url: print(f"AVISO: Erro ao salvar comentário no DB, mas upload pode ter ocorrido: {img_url}")
        return jsonify({'ok': False, 'error': f"Erro interno do servidor ao salvar comentário: {e}"}), 500

# --- Bloco de Execução Principal ---
if __name__ == '__main__':
    print("Iniciando app Flask em modo de desenvolvimento...")
    try:
        # Garante que as tabelas existam ao iniciar localmente
        init_db()
    except Exception as e:
        print(f"ERRO CRÍTICO durante inicialização do banco de dados local: {e}")
        # Considerar encerrar a aplicação se o DB for essencial
        # exit(1)
    
    # Executa o servidor Flask em modo debug (recarrega automaticamente)
    # ATENÇÃO: debug=True NUNCA deve ser usado em produção!
    app.run(debug=True, host='127.0.0.1', port=5000)