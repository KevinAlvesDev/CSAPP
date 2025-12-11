import secrets
from functools import wraps
from sqlite3 import IntegrityError as Sqlite3IntegrityError
from urllib.parse import urlencode

from flask import Blueprint, abort, current_app, flash, g, redirect, render_template, request, session, url_for
from itsdangerous import URLSafeTimedSerializer
from psycopg2 import IntegrityError as Psycopg2IntegrityError
from werkzeug.security import generate_password_hash

from ..config.logging_config import auth_logger, security_logger
from ..constants import ADMIN_EMAIL, PERFIL_ADMIN, PERFIL_IMPLANTADOR, PERFIS_COM_GESTAO
from ..core.extensions import limiter
from ..db import execute_db, query_db

auth_bp = Blueprint('auth', __name__)


def _get_reset_serializer():
    secret_key = current_app.config.get('SECRET_KEY') or current_app.secret_key
    return URLSafeTimedSerializer(secret_key, salt='password-reset')


def _sync_user_profile(user_email, user_name, auth0_user_id):
    """Garante que o usuário do Auth0 exista no DB local e defina o perfil inicial."""
    try:
        usuario_existente = query_db("SELECT usuario FROM usuarios WHERE usuario = %s", (user_email,), one=True)
        perfil_existente = query_db("SELECT nome FROM perfil_usuario WHERE usuario = %s", (user_email,), one=True)

        perfil_acesso_final = None
        if user_email == ADMIN_EMAIL:
            perfil_acesso_final = PERFIL_ADMIN
            auth_logger.info(f'Admin user {user_email} detected')

        if not usuario_existente:
            try:
                senha_placeholder = generate_password_hash(secrets.token_urlsafe(32))
                execute_db(
                    "INSERT INTO usuarios (usuario, senha) VALUES (%s, %s)",
                    (user_email, senha_placeholder)
                )
                auth_logger.info(f'User account created: {user_email}')
            except (Psycopg2IntegrityError, Sqlite3IntegrityError):
                raise ValueError("Usuário já cadastrado")
            except Exception as db_error:
                raise db_error

        if not perfil_existente:
            execute_db(
                "INSERT INTO perfil_usuario (usuario, nome, perfil_acesso) VALUES (%s, %s, %s)",
                (user_email, user_name, perfil_acesso_final)
            )
            auth_logger.info(f'User profile created: {user_email} with role {perfil_acesso_final}')
        elif user_email == ADMIN_EMAIL:
            perfil_acesso_atual = query_db("SELECT perfil_acesso FROM perfil_usuario WHERE usuario = %s", (user_email,), one=True)
            if perfil_acesso_atual.get('perfil_acesso') != PERFIL_ADMIN:
                execute_db("UPDATE perfil_usuario SET perfil_acesso = %s WHERE usuario = %s", (PERFIL_ADMIN, user_email))
                auth_logger.info(f'Admin role enforced for user: {user_email}')

    except ValueError as ve:
        raise ve
    except Exception as db_error:
        auth_logger.error(f'Critical error syncing user profile {user_email}: {str(db_error)}')
        flash("Erro ao sincronizar perfil do usuário com o banco de dados.", "warning")
        raise db_error


def login_required(f):
    """
    Decorator para proteger rotas que exigem login.
    Assume que @app.before_request (em __init__.py) já carregou g.user e g.perfil.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not g.user_email:
            try:
                auth_logger.info(f'Login required: anonymous access to {request.path}')
            except Exception:
                pass

            if request.is_json or request.headers.get('Accept', '').startswith('application/json'):
                from flask import jsonify
                return jsonify({'error': 'Não autenticado', 'message': 'Login necessário'}), 401

            try:
                if current_app.secret_key:
                    flash('Login necessário para acessar esta página.', 'info')
            except Exception:
                pass
            return redirect(url_for('auth.login'))

        if not g.perfil or g.perfil.get('perfil_acesso') is None:
            try:
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

            except ValueError as ve:
                flash(str(ve), "error")
                session.clear()
                return redirect(url_for('auth.login'))
            except Exception:
                pass

        perfil_acesso_debug = g.perfil.get('perfil_acesso') if g.perfil else 'NÃO CARREGADO'
        auth_logger.info(f'User authenticated: {g.user_email}, Role: {perfil_acesso_debug}, Path: {request.path}')

        return f(*args, **kwargs)
    return decorated_function


def permission_required(required_profiles):
    """Decorator para proteger rotas por Perfil de Acesso."""
    def decorator(f):
        @wraps(f)
        @login_required
        def decorated_function(*args, **kwargs):
            user_perfil = g.perfil.get('perfil_acesso') if g.perfil else None

            if user_perfil is None or user_perfil not in required_profiles:
                if any(p in required_profiles for p in PERFIS_COM_GESTAO):
                    try:
                        if current_app.secret_key:
                            flash('Seu perfil de acesso atual não tem permissão para essa função, entre em contato com um administrador.', 'error')
                    except Exception:
                        pass
                else:
                    try:
                        if current_app.secret_key:
                            flash('Acesso negado. Você não tem permissão para esta funcionalidade.', 'error')
                    except Exception:
                        pass

                security_logger.warning(f'Access denied for user {g.user_email} with role {user_perfil} trying to access {request.path}')
                return redirect(url_for('main.dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def admin_required(f):
    """Protege rotas que exigem perfil Administrador."""
    return permission_required([PERFIL_ADMIN])(f)


def rate_limit(max_requests):
    """Decorator condicional para rate limiting."""
    def decorator(f):
        try:
            from flask import current_app
            if current_app and not current_app.config.get('RATELIMIT_ENABLED', True):
                return f
        except Exception:
            pass
        if limiter:
            return limiter.limit(max_requests)(f)
        return f
    return decorator


@auth_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Rota desativada: alteração de senha não permitida (login exclusivo via Google)."""
    flash('Gerenciamento de credenciais é feito via Google.', 'info')
    return redirect(url_for('main.dashboard'))


@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Rota desativada: recuperação de senha não permitida (login exclusivo via Google)."""
    flash('Login exclusivo via Google. Recupere sua senha no Google se necessário.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/check-email', methods=['GET'])
def check_email():
    """Rota desativada."""
    from flask import jsonify
    return jsonify({'valid': False, 'exists': False, 'message': 'Endpoint desativado'})


@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Rota desativada."""
    flash('Login exclusivo via Google.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    Página de login.
    Agora suporta apenas login via Google OAuth.
    O POST foi removido pois não há mais formulário de senha.
    """
    # Se usuário já estiver logado, redireciona para dashboard
    if g.user:
        return redirect(url_for('main.dashboard'))

    # Renderiza a página de login (que agora só tem o botão do Google)
    login_bg_file = current_app.config.get('LOGIN_BG_FILE', 'imagens/teladelogin.jpg')
    return render_template('login.html', auth0_enabled=False, use_custom_auth=True, login_bg_file=login_bg_file)



@auth_bp.route('/check_user_external', methods=['POST'])
def check_user_external():
    """
    Endpoint para verificar se o usuário existe no banco externo.
    Retorna JSON para uso via AJAX na tela de login.
    """
    data = request.get_json()
    email = data.get('email')

    if not email:
        return {'status': 'error', 'message': 'Email não fornecido'}, 400

    try:
        from ..common.validation import validate_email
        email = validate_email(email)
    except Exception:
         return {'status': 'error', 'message': 'Email inválido'}, 400

    try:
        cs_user = _find_cs_user_by_email_safe(email)
        if cs_user:
            if cs_user.get('ativo'):
                return {
                    'status': 'success',
                    'message': 'Usuário encontrado',
                    'user_name': cs_user.get('nome')
                }, 200
            else:
                return {
                    'status': 'error',
                    'message': 'Usuário encontrado, mas inativo'
                }, 200
        else:
            return {
                'status': 'error',
                'message': 'Usuário não encontrado na base CS'
            }, 200
    except Exception as e:
        auth_logger.error(f"Erro na verificação externa via API: {e}")
        return {'status': 'error', 'message': 'Erro ao consultar banco externo'}, 500


@auth_bp.route('/callback')
@rate_limit("100 per minute")
def callback():
    """Manipula o retorno do Auth0 após o login."""

    if not current_app.config.get('AUTH0_ENABLED', True):
        flash('Auth0 desativado no ambiente de desenvolvimento. Use dev_login.', 'info')
        return redirect(url_for('main.dashboard'))

    from ..core.extensions import oauth

    try:
        auth0 = oauth.create_client('auth0')
        token = auth0.authorize_access_token()
        userinfo = token.get('userinfo')

        if not userinfo or not userinfo.get('email'):
            raise Exception("Informação do usuário inválida recebida do Auth0.")

        session['user'] = userinfo
        session.permanent = True

        user_email = userinfo.get('email')
        user_name = userinfo.get('name', user_email)
        auth0_user_id = userinfo.get('sub')

        _sync_user_profile(user_email, user_name, auth0_user_id)

        auth_logger.info(f'User logged in successfully: {user_email}')
        return redirect(url_for('main.dashboard'))

    except ValueError as ve:
        auth_logger.error(f'Erro no callback (duplicação): {ve}')
        flash(str(ve), "error")
        session.clear()
        return redirect(url_for('auth.login'))
    except Exception as e:
        auth_logger.error(f'Erro no callback do Auth0: {e}', exc_info=True)
        flash("Erro durante a autenticação: Algo deu errado, por favor tente novamente.", "error")
        session.clear()
        return redirect(url_for('main.home'))


@auth_bp.route('/login/google')
def google_login():
    """
    Inicia o fluxo de login com Google.
    
    Rota: /login/google
    Endpoint: auth.google_login
    
    Descrição:
    - Verifica se o Google OAuth está ativado.
    - Redireciona o usuário para a página de consentimento do Google.
    - Define o callback para 'auth.google_callback'.
    """
    from ..core.extensions import oauth

    auth_logger.info("Iniciando fluxo de login com Google")

    if not current_app.config.get('GOOGLE_OAUTH_ENABLED'):
        auth_logger.error("Google OAuth não está habilitado nas configurações")
        flash('Login com Google não está configurado.', 'error')
        return redirect(url_for('auth.login'))

    # Usar SEMPRE o host atual para evitar perda de sessão/state
    redirect_uri = url_for('auth.google_callback', _external=True)

    auth_logger.info(f"Redirecionando para Google com callback: {redirect_uri}")
    return oauth.google.authorize_redirect(redirect_uri)


@auth_bp.route('/login/google/callback')
def google_callback():
    """
    Callback do login com Google.
    
    Rota: /login/google/callback
    Endpoint: auth.google_callback
    
    Descrição:
    - Recebe o código de autorização do Google.
    - Troca o código por um token de acesso.
    - Obtém informações do perfil do usuário.
    - Valida se o e-mail pertence ao domínio @pactosolucoes.com.br.
    - Valida se o usuário existe e está ativo na base externa (OAMD).
    - Cria ou atualiza o usuário localmente.
    - Inicia a sessão do usuário.
    """
    from ..core.extensions import oauth

    auth_logger.info("Recebido callback do Google")

    try:
        token = oauth.google.authorize_access_token()
        auth_logger.info("Token de acesso obtido com sucesso")

        # userinfo geralmente vem no token se openid scope for usado,
        # mas garantimos chamando userinfo() se disponivel ou pegando do token
        user_info = token.get('userinfo')
        if not user_info:
             user_info = oauth.google.userinfo()

        auth_logger.info(f"Informações do usuário obtidas: {user_info.get('email')}")

        email = user_info.get('email')

        if not email:
            auth_logger.error("E-mail não encontrado nas informações do usuário")
            flash('Não foi possível obter o e-mail da sua conta Google.', 'error')
            return redirect(url_for('auth.login'))

        # Validação de Domínio
        if not email.endswith('@pactosolucoes.com.br'):
            auth_logger.warning(f'Google Login blocked: Invalid domain {email}')
            flash('Acesso restrito a contas @pactosolucoes.com.br', 'error')
            return redirect(url_for('auth.login'))

        # --- VALIDAÇÃO EXTERNA (OAMD) ---
        try:
            # Verificar se a URL do banco externo está configurada
            external_db_configured = bool(current_app.config.get('EXTERNAL_DB_URL'))

            # Tentar buscar usuário se o banco estiver configurado ou se estivermos em modo DEBUG (para usar o mock)
            # Em produção sem URL, find_cs_user_by_email retornaria None, mas queremos tratar isso diferentemente

            if external_db_configured or current_app.config.get('DEBUG', False):
                cs_user = _find_cs_user_by_email_safe(email)

                if not cs_user:
                    # Se o banco está configurado e não achou -> Bloqueia
                    if external_db_configured:
                        auth_logger.warning(f'Login blocked: User not found in External CS DB: {email}')
                        flash('Acesso negado. Usuário não identificado na base de Customer Success (OAMD). Por favor, entre em contato com o suporte ou verifique se seu cadastro no OAMD está ativo e correto.', 'error')
                        return redirect(url_for('auth.login'))
                    else:
                        # Se não está configurado mas tentou (DEBUG mock), e falhou -> Bloqueia (comportamento do mock)
                        # Mas se o mock não rodou (ex: email errado), cai aqui
                         auth_logger.warning(f'Login blocked: User not found (Mock/Dev): {email}')
                         flash('Acesso negado. Usuário não identificado (Dev Mode).', 'error')
                         return redirect(url_for('auth.login'))

                if not cs_user.get('ativo'):
                    auth_logger.warning(f'Login blocked: Inactive user in External CS DB: {email}')
                    flash('Acesso negado. Seu cadastro de CS está inativo.', 'error')
                    return redirect(url_for('auth.login'))

                auth_logger.info(f"External auth check passed for {email} (CS: {cs_user.get('nome')})")
                user_name_final = cs_user.get('nome')

            else:
                # FALLBACK DE PRODUÇÃO SEM BANCO EXTERNO
                # Se não temos URL de banco externo e NÃO estamos em DEBUG,
                # assumimos que a validação de domínio do Google é suficiente.
                auth_logger.warning(f"External DB check SKIPPED for {email} (No Config). Relying on Google Domain.")
                # Usar nome do Google
                user_name_final = user_info.get('name', email)

        except Exception as e:
            auth_logger.error(f'External DB check failed during login: {e}', exc_info=True)
            # Em caso de erro técnico no banco (timeout, etc), decidir se bloqueia ou libera.
            # Por segurança, geralmente bloqueia, ou libera com restrições.
            # Vamos manter o bloqueio para forçar correção, a menos que explicitamente desejado o contrário.
            flash('Erro ao validar credenciais externas. Tente novamente.', 'error')
            return redirect(url_for('auth.login'))
        # -------------------------------------

        # Sincronizar usuário
        # Usamos o 'sub' do Google como ID único
        _sync_user_profile(email, user_name_final, user_info.get('sub'))

        # Configurar sessão (compatível com a estrutura existente que espera session['user'])
        session['user'] = user_info

        session.permanent = True

        # Opcional: Armazenar token se precisar acessar APIs do Google depois
        # session['google_token'] = token

        auth_logger.info(f'User logged in via Google: {email}')
        return redirect(url_for('main.dashboard'))

    except Exception as e:
        auth_logger.error(f'Google Login Callback Error: {e}', exc_info=True)
        flash('Erro ao realizar login com Google. Tente novamente.', 'error')
        return redirect(url_for('auth.login'))


@auth_bp.route('/logout')
def logout():
    """Desloga o usuário da sessão local e do Auth0."""
    session.clear()

    if current_app.config.get('AUTH0_ENABLED', True):
        params = {
            'returnTo': url_for('main.home', _external=True),
            'client_id': current_app.config['AUTH0_CLIENT_ID']
        }
        logout_url = f"https://{current_app.config['AUTH0_DOMAIN']}/v2/logout?{urlencode(params)}"
        return redirect(logout_url)
    else:
        flash('Logout local efetuado (Auth0 desativado).', 'info')
        return redirect(url_for('main.home'))


@auth_bp.route('/dev-login', methods=['GET'])
def dev_login():
    """Login de desenvolvimento: cria sessão local sem Auth0.

    SEGURANÇA: Esta rota só funciona em ambiente de desenvolvimento.
    Em produção, retorna 404 para evitar acesso não autorizado.
    """

    import os

    flask_env = os.environ.get('FLASK_ENV', 'production')
    flask_debug = current_app.config.get('DEBUG', False)
    use_sqlite = current_app.config.get('USE_SQLITE_LOCALLY', False)

    if flask_env == 'production' or (not flask_debug and not use_sqlite):
        security_logger.warning('Tentativa de acesso a /dev-login em ambiente de produção')
        abort(404)

    if current_app.config.get('AUTH0_ENABLED', True):
        return redirect(url_for('auth.login'))

    dev_email = ADMIN_EMAIL
    session['user'] = {
        'email': dev_email,
        'name': 'Dev User',
        'sub': 'dev|local'
    }

    session.permanent = True

    try:
        _sync_user_profile(dev_email, 'Dev User', 'dev|local')
    except Exception as e:
        auth_logger.warning(f"Falha ao sincronizar perfil dev {dev_email}: {e}")

    auth_logger.info(f'Dev login realizado: {dev_email}')
    flash('Logado em modo desenvolvimento com acesso de Administrador.', 'success')
    return redirect(url_for('main.dashboard'))


@auth_bp.route('/dev-login-as', methods=['GET', 'POST'])
def dev_login_as():
    """Login de desenvolvimento com e-mail arbitrário (somente quando Auth0 está desativado).

    SEGURANÇA: Esta rota só funciona em ambiente de desenvolvimento.
    Em produção, retorna 404 para evitar acesso não autorizado.
    """

    import os

    flask_env = os.environ.get('FLASK_ENV', 'production')
    flask_debug = current_app.config.get('DEBUG', False)
    use_sqlite = current_app.config.get('USE_SQLITE_LOCALLY', False)

    if flask_env == 'production' or (not flask_debug and not use_sqlite):
        security_logger.warning('Tentativa de acesso a /dev-login-as em ambiente de produção')
        abort(404)

    if current_app.config.get('AUTH0_ENABLED', True):
        return redirect(url_for('auth.login'))

    if request.method == 'GET':
        try:
            session.pop('_flashes', None)
        except Exception:
            pass
        return render_template('dev_login.html', auth0_enabled=False)

    email = (request.form.get('email') or '').strip()
    name = (request.form.get('name') or email).strip()

    if not email:
        flash('Informe um e-mail válido.', 'error')
        return redirect(url_for('auth.dev_login_as'))

    try:
        from ..common.validation import validate_email
        email = validate_email(email)
    except Exception:
        flash('E-mail inválido.', 'error')
        return redirect(url_for('auth.dev_login_as'))

    session['user'] = {
        'email': email,
        'name': name or email,
        'sub': 'dev|manual'
    }
    session.permanent = True

    try:
        _sync_user_profile(email, name or email, 'dev|manual')

        if email != ADMIN_EMAIL:
            try:
                execute_db(
                    "UPDATE perfil_usuario SET perfil_acesso = %s WHERE usuario = %s AND (perfil_acesso IS NULL OR perfil_acesso = '')",
                    (PERFIL_IMPLANTADOR, email)
                )
            except Exception as role_err:
                auth_logger.warning(f"Não foi possível definir perfil Implantador para {email}: {role_err}")
    except Exception as e:
        auth_logger.warning(f"Falha ao sincronizar perfil dev para {email}: {e}")

    flash(f'Logado como {email} (desenvolvimento).', 'success')
    return redirect(url_for('main.dashboard'))


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Rota desativada: registro não permitido (login exclusivo via Google)."""
    flash('Novos cadastros devem ser feitos pelo administrador ou via Google Login.', 'info')
    return redirect(url_for('auth.login'))
def _find_cs_user_by_email_safe(email):
    try:
        if not current_app.config.get('EXTERNAL_DB_URL'):
            return None
        from ..database.external_db import find_cs_user_by_email
        return find_cs_user_by_email(email)
    except Exception as e:
        auth_logger.warning(f"External DB lookup failed: {e}")
        return None
