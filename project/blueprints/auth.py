from functools import wraps
from flask import (
    Blueprint, redirect, url_for, session, render_template, g, flash, 
    current_app, request
)
from werkzeug.security import generate_password_hash
from urllib.parse import urlencode

from ..extensions import oauth
from ..db import query_db, execute_db
from ..constants import ADMIN_EMAIL, PERFIL_ADMIN, PERFIL_COLABORADOR

auth_bp = Blueprint('auth', __name__)

def _sync_user_profile(user_email, user_name, auth0_user_id):
    """Garante que o usuário do Auth0 exista no DB local e defina o perfil inicial."""
    try:
        perfil = query_db("SELECT nome FROM perfil_usuario WHERE usuario = %s", (user_email,), one=True)
        
        # Define o perfil de acesso inicial, forçando 'Administrador' para o ADMIN_EMAIL
        perfil_acesso_final = PERFIL_COLABORADOR
        if user_email == ADMIN_EMAIL:
            perfil_acesso_final = PERFIL_ADMIN

        if not perfil:
            # Lógica de criação na tabela 'usuarios'
            usuario_existente = query_db("SELECT usuario FROM usuarios WHERE usuario = %s", (user_email,), one=True)
            if not usuario_existente:
                senha_placeholder = generate_password_hash(auth0_user_id + current_app.secret_key)
                execute_db(
                    "INSERT INTO usuarios (usuario, senha) VALUES (%s, %s)",
                    (user_email, senha_placeholder)
                )
                print(f"Registro de usuário criado: {user_email}.")
            
            # Cria o perfil associado com a permissão correta
            execute_db(
                "INSERT INTO perfil_usuario (usuario, nome, perfil_acesso) VALUES (%s, %s, %s)",
                (user_email, user_name, perfil_acesso_final)
            )
            print(f"Perfil criado: {user_email} com perfil: {perfil_acesso_final}.")
            
        else:
            # Garante que o ADMIN_EMAIL fixo seja sempre Administrador, caso tenha sido rebaixado
            perfil_acesso_atual = query_db("SELECT perfil_acesso FROM perfil_usuario WHERE usuario = %s", (user_email,), one=True)
            if perfil_acesso_atual.get('perfil_acesso') != PERFIL_ADMIN and user_email == ADMIN_EMAIL:
                 execute_db(
                    "UPDATE perfil_usuario SET perfil_acesso = %s WHERE usuario = %s",
                    (PERFIL_ADMIN, user_email)
                 )
                 print(f"Perfil de acesso atualizado: {user_email} forçado para {PERFIL_ADMIN}.")

    except Exception as db_error:
        print(f"ERRO CRÍTICO ao sincronizar perfil {user_email}: {db_error}")
        flash("Erro ao sincronizar perfil do usuário com o banco de dados.", "warning")
        pass


# --- Decoradores de Autenticação e Permissão ---

def login_required(f):
    """Decorator para proteger rotas que exigem login."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            flash('Login necessário para acessar esta página.', 'info')
            return redirect(url_for('auth.login'))
        
        g.user = session.get('user')
        g.user_email = g.user.get('email') if g.user else None
        
        if not g.user_email:
            flash("Sessão inválida ou email não encontrado.", "warning")
            session.clear()
            return redirect(url_for('auth.logout'))
        
        # Carrega o perfil do usuário no 'g'
        g.perfil = query_db("SELECT * FROM perfil_usuario WHERE usuario = %s", (g.user_email,), one=True)
        
        # Fallback e sincronização
        if not g.perfil:
            _sync_user_profile(g.user_email, g.user.get('name', g.user_email), g.user.get('sub'))
            g.perfil = query_db("SELECT * FROM perfil_usuario WHERE usuario = %s", (g.user_email,), one=True)
            if not g.perfil:
                 g.perfil = {
                    'nome': g.user.get('name', g.user_email),
                    'usuario': g.user_email,
                    'foto_url': None,
                    'cargo': None,
                    'perfil_acesso': None
                }
        
        # --- DEBUG CRÍTICO AQUI ---
        perfil_acesso_debug = g.perfil.get('perfil_acesso') if g.perfil else 'NÃO CARREGADO'
        print(f"\n[DEBUG] Usuário logado: {g.user_email}, Perfil de Acesso: {perfil_acesso_debug}, Rota: {request.path}\n")
        # ---------------------------

        return f(*args, **kwargs)
    return decorated_function
    
def permission_required(required_profiles):
    """Decorator para proteger rotas por Perfil de Acesso."""
    def decorator(f):
        @wraps(f)
        @login_required
        def decorated_function(*args, **kwargs):
            user_perfil = g.perfil.get('perfil_acesso') if g.perfil else None
            
            if user_perfil not in required_profiles:
                flash('Acesso negado. Você não tem permissão para esta funcionalidade.', 'error')
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

        # Garante que o usuário existe no nosso DB
        _sync_user_profile(user_email, user_name, auth0_user_id)
        
        return redirect(url_for('main.dashboard'))
        
    except Exception as e:
        print(f"ERRO no callback do Auth0: {e}")
        flash(f"Erro durante a autenticação: {e}.", "error")
        session.clear()
        return redirect(url_for('main.home'))

@auth_bp.route('/logout')
def logout():
    """Desloga o usuário da sessão local e do Auth0."""
    session.clear()
    
    # Parâmetros para o logout do Auth0
    params = {
        'returnTo': url_for('main.home', _external=True),
        'client_id': current_app.config['AUTH0_CLIENT_ID']
    }
    logout_url = f"https://{current_app.config['AUTH0_DOMAIN']}/v2/logout?{urlencode(params)}"
    
    return redirect(logout_url)