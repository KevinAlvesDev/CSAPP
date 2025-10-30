from functools import wraps
from flask import (
    Blueprint, redirect, url_for, session, render_template, g, flash, 
    current_app, request, jsonify
)
from werkzeug.security import generate_password_hash
from urllib.parse import urlencode

try:
    from psycopg2 import IntegrityError as Psycopg2IntegrityError
except ImportError:
    Psycopg2IntegrityError = None
    
try:
    from sqlite3 import IntegrityError as Sqlite3IntegrityError
except ImportError:
    Sqlite3IntegrityError = None


from ..extensions import oauth
from ..db import query_db, execute_db
from ..constants import ADMIN_EMAIL, PERFIL_ADMIN, PERFIL_IMPLANTADOR, PERFIS_COM_GESTAO

auth_bp = Blueprint('auth', __name__)

def _sync_user_profile(user_email, user_name, auth0_user_id):
    """Garante que o usuário do Auth0 exista no DB local e defina o perfil inicial."""
    try:
        usuario_existente = query_db("SELECT usuario FROM usuarios WHERE usuario = %s", (user_email,), one=True)
        perfil_existente = query_db("SELECT nome FROM perfil_usuario WHERE usuario = %s", (user_email,), one=True)

        perfil_acesso_final = None 
        if user_email == ADMIN_EMAIL:
            perfil_acesso_final = PERFIL_ADMIN

        if not usuario_existente:
            try:
                senha_placeholder = generate_password_hash(auth0_user_id + current_app.secret_key)
                execute_db(
                    "INSERT INTO usuarios (usuario, senha) VALUES (%s, %s)",
                    (user_email, senha_placeholder)
                )
                print(f"Registro de usuário criado: {user_email}.")
            except (Psycopg2IntegrityError, Sqlite3IntegrityError) as e:
                 print(f"AVISO: Tentativa de inserir usuário duplicado {user_email}: {e}")
                 raise ValueError("Usuário já cadastrado") 
            except Exception as db_error:
                print(f"ERRO ao inserir usuário {user_email}: {db_error}")
                raise db_error

        if not perfil_existente:
            execute_db(
                "INSERT INTO perfil_usuario (usuario, nome, perfil_acesso) VALUES (%s, %s, %s)",
                (user_email, user_name, perfil_acesso_final)
            )
            print(f"Perfil criado: {user_email} com perfil: {perfil_acesso_final}.")
        elif user_email == ADMIN_EMAIL:
             perfil_acesso_atual = query_db("SELECT perfil_acesso FROM perfil_usuario WHERE usuario = %s", (user_email,), one=True)
             if perfil_acesso_atual.get('perfil_acesso') != PERFIL_ADMIN:
                  execute_db("UPDATE perfil_usuario SET perfil_acesso = %s WHERE usuario = %s", (PERFIL_ADMIN, user_email))
                  print(f"Perfil de acesso atualizado: {user_email} forçado para {PERFIL_ADMIN}.")

    except ValueError as ve: 
        raise ve
    except Exception as db_error:
        print(f"ERRO CRÍTICO ao sincronizar perfil {user_email}: {db_error}")
        raise db_error 


# --- Decoradores de Autenticação e Permissão ---

def login_required(f):
    """
    Decorator para proteger rotas.
    MODIFICADO: Retorna 401 (JSON) para pedidos de API, 
    e redireciona (302) para pedidos de navegador.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        
        # --- INÍCIO DA NOVA CORREÇÃO (Tratar Preflight OPTIONS) ---
        # Permite que os pedidos OPTIONS (preflight do CORS) passem
        # antes de verificar o login. A extensão Flask-CORS irá tratá-los.
        if request.method == 'OPTIONS':
            return f(*args, **kwargs)
        # --- FIM DA NOVA CORREÇÃO ---
            
        if 'user' not in session:
            # (Início da correção anterior)
            is_api_request = request.origin == 'http://localhost:5173' or \
                             request.headers.get('X-Requested-With') == 'XMLHttpRequest' or \
                             'application/json' in request.headers.get('Accept', '')

            if is_api_request:
                return jsonify(success=False, error="Autenticação necessária."), 401
            else:
                flash('Login necessário para acessar esta página.', 'info')
                return redirect(url_for('auth.login'))
            # (Fim da correção anterior)
        
        g.user = session.get('user')
        g.user_email = g.user.get('email') if g.user else None
        
        if not g.user_email:
            session.clear()
            return jsonify(success=False, error="Sessão inválida."), 401
        
        g.perfil = query_db("SELECT * FROM perfil_usuario WHERE usuario = %s", (g.user_email,), one=True)
        
        if not g.perfil:
            sincronizacao_ok = False
            try:
                _sync_user_profile(g.user_email, g.user.get('name', g.user_email), g.user.get('sub'))
                sincronizacao_ok = True
            except ValueError as ve:
                 session.clear()
                 return jsonify(success=False, error=str(ve)), 400
            except Exception as e:
                 print(f"Erro no _sync_user_profile durante o fallback: {e}")
                 
            if sincronizacao_ok:
                 g.perfil = query_db("SELECT * FROM perfil_usuario WHERE usuario = %s", (g.user_email,), one=True)
                 
            if not g.perfil:
                 g.perfil = {
                    'nome': g.user.get('name', g.user_email),
                    'usuario': g.user_email,
                    'foto_url': None,
                    'cargo': None,
                    'perfil_acesso': None
                }
        
        perfil_acesso_debug = g.perfil.get('perfil_acesso') if g.perfil else 'NÃO CARREGADO'
        print(f"\n[DEBUG] Usuário logado: {g.user_email}, Perfil de Acesso: {perfil_acesso_debug}, Rota: {request.path}\n")

        return f(*args, **kwargs)
    return decorated_function
    
def permission_required(required_profiles):
    """Decorator para proteger rotas por Perfil de Acesso (Modificado para API)."""
    def decorator(f):
        @wraps(f)
        @login_required 
        def decorated_function(*args, **kwargs):
            
            # (O request.method == 'OPTIONS' já foi tratado em @login_required)
            
            user_perfil = g.perfil.get('perfil_acesso') if g.perfil else None
            
            if user_perfil is None or user_perfil not in required_profiles:
                mensagem_erro = 'Acesso negado. Você não tem permissão para esta funcionalidade.'
                if any(p in required_profiles for p in PERFIS_COM_GESTAO):
                     mensagem_erro = 'Seu perfil de acesso atual não tem permissão para essa função, entre em contato com um administrador.'

                is_api_request = request.origin == 'http://localhost:5173' or \
                                 'application/json' in request.headers.get('Accept', '')

                if is_api_request:
                    return jsonify(success=False, error=mensagem_erro), 403 # 403 Forbidden
                else:
                    flash(mensagem_erro, 'error')
                    return redirect(url_for('main.dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# --- Rotas de Autenticação ---

@auth_bp.route('/login')
def login():
    """Redireciona o usuário para a página de login do Auth0."""
    session.clear()
    
    redirect_uri = url_for('auth.callback', _external=True)
    
    auth0 = oauth.create_client('auth0')
    return auth0.authorize_redirect(redirect_uri=redirect_uri)

@auth_bp.route('/callback')
def callback():
    """Manipula o retorno do Auth0 após o login."""
    try:
        auth0 = oauth.create_client('auth0')
        token = auth0.authorize_access_token()
        userinfo = token.get('userinfo')
        
        if not userinfo or not userinfo.get('email'):
            raise Exception("Informação do usuário inválida recebida do Auth0.")
        
        session['user'] = userinfo
        user_email = userinfo.get('email')
        user_name = userinfo.get('name', user_email)
        auth0_user_id = userinfo.get('sub')

        _sync_user_profile(user_email, user_name, auth0_user_id)
        
        # Redireciona para a raiz do front-end (React).
        return redirect('http://localhost:5173/') 
        
    except ValueError as ve:
        print(f"ERRO no callback (duplicação): {ve}")
        session.clear()
        return redirect(f"http://localhost:5173/login?error={urlencode({'message': str(ve)})}")
    except Exception as e:
        print(f"ERRO no callback do Auth0: {e}")
        session.clear()
        return redirect(f"http://localhost:5173/login?error={urlencode({'message': 'Erro na autenticação'})}")

@auth_bp.route('/logout')
def logout():
    """Desloga o usuário da sessão local e do Auth0."""
    session.clear()
    
    params = {
        'returnTo': 'http://localhost:5173/login', # Redireciona para o login do React
        'client_id': current_app.config['AUTH0_CLIENT_ID']
    }
    logout_url = f"https://{current_app.config['AUTH0_DOMAIN']}/v2/logout?{urlencode(params)}"
    
    return redirect(logout_url)