from functools import wraps
from flask import (
    Blueprint, redirect, url_for, session, render_template, g, flash,
    current_app, request, abort
)
from werkzeug.security import generate_password_hash, check_password_hash
from urllib.parse import urlencode
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

from psycopg2 import IntegrityError as Psycopg2IntegrityError
from sqlite3 import IntegrityError as Sqlite3IntegrityError

from ..db import query_db, execute_db
from ..constants import ADMIN_EMAIL, PERFIL_ADMIN, PERFIL_IMPLANTADOR, PERFIS_COM_GESTAO
from ..core.extensions import limiter
from ..config.logging_config import auth_logger, security_logger

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
                senha_placeholder = generate_password_hash(auth0_user_id + current_app.secret_key)
                execute_db(
                    "INSERT INTO usuarios (usuario, senha) VALUES (%s, %s)",
                    (user_email, senha_placeholder)
                )
                auth_logger.info(f'User account created: {user_email}')
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
            except Exception as e:
                print(f"Erro no _sync_user_profile durante o fallback do @login_required: {e}")

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
@rate_limit("100 per minute")
@login_required
def change_password():
    """Permite ao usuário autenticado alterar sua senha."""
    if request.method == 'GET':
        try:
            session.pop('_flashes', None)
        except Exception:
            pass
        return render_template('change_password.html', auth0_enabled=False)

    current_password = request.form.get('current_password', '')
    new_password = request.form.get('new_password', '')
    new_password_confirm = request.form.get('new_password_confirm', '')

    if not all([current_password, new_password, new_password_confirm]):
        flash('Preencha todos os campos.', 'error')
        return render_template('change_password.html', auth0_enabled=False)

    try:
        from ..common.validation import validate_password_strength, ValidationError
        validate_password_strength(new_password)
    except ValidationError as ve:
        flash(str(ve), 'error')
        return render_template('change_password.html', auth0_enabled=False)

    if new_password != new_password_confirm:
        flash('As senhas novas não coincidem.', 'error')
        return render_template('change_password.html', auth0_enabled=False)

    usuario = query_db("SELECT usuario, senha FROM usuarios WHERE usuario = %s", (g.user_email,), one=True)
    if not usuario:
        flash('Conta não encontrada.', 'error')
        return render_template('change_password.html', auth0_enabled=False)

    if not check_password_hash(usuario.get('senha'), current_password):
        flash('Senha atual incorreta.', 'error')
        return render_template('change_password.html', auth0_enabled=False)

    try:
        senha_hash = generate_password_hash(new_password)
        execute_db("UPDATE usuarios SET senha = %s WHERE usuario = %s", (senha_hash, g.user_email))
        auth_logger.info(f'User changed password: {g.user_email}')
        flash('Senha alterada com sucesso.', 'success')
        return redirect(url_for('main.dashboard'))
    except Exception as e:
        auth_logger.error(f'Error changing password for {g.user_email}: {str(e)}')
        flash('Erro ao alterar senha. Tente novamente.', 'error')
        return render_template('change_password.html', auth0_enabled=False)


@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
@rate_limit("100 per minute")
def forgot_password():
    """Solicita recuperação de senha via e-mail com token."""
    if request.method == 'GET':
        try:
            session.pop('_flashes', None)
        except Exception:
            pass
        return render_template('forgot_password.html', auth0_enabled=False)

    email = (request.form.get('email') or '').strip().lower()
    try:
        from ..common.validation import validate_email
        email = validate_email(email)
    except Exception:
        flash('E-mail inválido.', 'error')
        return render_template('forgot_password.html', auth0_enabled=False)

    usuario = query_db("SELECT usuario FROM usuarios WHERE usuario = %s", (email,), one=True)
    if not usuario:
        flash('E-mail não encontrado.', 'error')
        return render_template('forgot_password.html', auth0_enabled=False)

    s = _get_reset_serializer()
    token = s.dumps({'email': email})
    reset_url = url_for('auth.reset_password', token=token, _external=True)

    try:
        from ..mail.email_utils import send_email_global
        subject = 'Recuperação de senha - CS Onboarding'
        body_html = f"""
            <p>Olá,</p>
            <p>Para redefinir sua senha, clique no link abaixo. Ele expira em 1 hora.</p>
            <p><a href="{reset_url}">Redefinir senha</a></p>
            <p>Se você não solicitou, ignore este e-mail.</p>
        """
        body_text = (
            "Olá,\n\n"
            "Para redefinir sua senha, use o link abaixo. Ele expira em 1 hora.\n"
            f"{reset_url}\n\n"
            "Se você não solicitou, ignore este e-mail.\n"
        )
        send_email_global(subject, body_html, [email], body_text=body_text)
        flash('Enviamos um link de redefinição de senha para seu e-mail.', 'success')
    except Exception as e:
        auth_logger.warning(f'Password reset email not sent (fallback): {e}')
        flash('Sistema de e-mail não está configurado. Use o link para redefinir:', 'warning')
        flash(reset_url, 'info')

    return redirect(url_for('auth.login'))


@auth_bp.route('/check-email', methods=['GET'])
def check_email():
    email = (request.args.get('email') or '').strip().lower()
    try:
        from ..common.validation import validate_email
        email = validate_email(email)
    except Exception:
        from flask import jsonify
        return jsonify({'valid': False, 'exists': False})
    usuario = query_db("SELECT usuario FROM usuarios WHERE usuario = %s", (email,), one=True)
    from flask import jsonify
    return jsonify({'valid': True, 'exists': bool(usuario)})


@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
@rate_limit("100 per minute")
def reset_password(token):
    """Redefine a senha usando token temporário."""

    s = _get_reset_serializer()
    try:
        data = s.loads(token, max_age=3600)
        email = data.get('email')
    except SignatureExpired:
        flash('O link expirou. Solicite novamente.', 'error')
        return redirect(url_for('auth.forgot_password'))
    except BadSignature:
        flash('Link inválido.', 'error')
        return redirect(url_for('auth.forgot_password'))

    if request.method == 'GET':
        try:
            session.pop('_flashes', None)
        except Exception:
            pass
        return render_template('reset_password.html', auth0_enabled=False)

    new_password = request.form.get('new_password', '')
    new_password_confirm = request.form.get('new_password_confirm', '')
    if not all([new_password, new_password_confirm]):
        flash('Preencha todos os campos.', 'error')
        return render_template('reset_password.html', auth0_enabled=False)

    try:
        from ..common.validation import validate_password_strength, ValidationError
        validate_password_strength(new_password)
    except ValidationError as ve:
        flash(str(ve), 'error')
        return render_template('reset_password.html', auth0_enabled=False)

    if new_password != new_password_confirm:
        flash('As senhas não coincidem.', 'error')
        return render_template('reset_password.html', auth0_enabled=False)

    try:
        senha_hash = generate_password_hash(new_password)
        execute_db("UPDATE usuarios SET senha = %s WHERE usuario = %s", (senha_hash, email))
        auth_logger.info(f'User reset password: {email}')
        flash('Senha redefinida com sucesso. Faça login.', 'success')
        return redirect(url_for('auth.login'))
    except Exception as e:
        auth_logger.error(f'Error resetting password for {email}: {str(e)}')
        flash('Erro ao redefinir senha. Tente novamente.', 'error')
        return render_template('reset_password.html', auth0_enabled=False)


@auth_bp.route('/login', methods=['GET', 'POST'])
@rate_limit("100 per minute")
def login():
    if request.method == 'GET':
        try:
            session.pop('_flashes', None)
        except Exception:
            pass
        return render_template('login.html', auth0_enabled=False, use_custom_auth=True)

    email = (request.form.get('email') or '').strip().lower()
    password = request.form.get('password', '')

    if not email or not password:
        flash('Por favor, preencha todos os campos.', 'error')
        return render_template('login.html', auth0_enabled=False, use_custom_auth=True)

    try:
        from ..common.validation import validate_email
        email = validate_email(email)
    except Exception:
        flash('E-mail inválido.', 'error')
        return render_template('login.html', auth0_enabled=False, use_custom_auth=True)

    usuario = query_db("SELECT usuario, senha FROM usuarios WHERE usuario = %s", (email,), one=True)

    if not usuario:
        auth_logger.warning(f'Login attempt with non-existent email: {email}')
        flash('E-mail ou senha incorretos.', 'error')
        return render_template('login.html', auth0_enabled=False, use_custom_auth=True)

    if not check_password_hash(usuario.get('senha'), password):
        auth_logger.warning(f'Failed login attempt for: {email}')
        flash('E-mail ou senha incorretos.', 'error')
        return render_template('login.html', auth0_enabled=False, use_custom_auth=True)

    perfil = query_db("SELECT nome FROM perfil_usuario WHERE usuario = %s", (email,), one=True)
    nome = perfil.get('nome') if perfil else email

    session['user'] = {
        'email': email,
        'name': nome,
        'sub': f'local|{email}'
    }
    session.permanent = True

    auth_logger.info(f'User logged in successfully: {email}')
    flash(f'Bem-vindo, {nome}!', 'success')
    return redirect(url_for('main.dashboard'))


@auth_bp.route('/callback')
@rate_limit("100 per minute")
def callback():
    """Manipula o retorno do Auth0 após o login."""

    if not current_app.config.get('AUTH0_ENABLED', True):
        flash('Auth0 desativado no ambiente de desenvolvimento. Use dev_login.', 'info')
        return redirect(url_for('main.dashboard'))

    from ..extensions import oauth

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
        flash(f"Erro durante a autenticação: Algo deu errado, por favor tente novamente.", "error")
        session.clear()
        return redirect(url_for('main.home'))


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
    if current_app.config.get('AUTH0_ENABLED', True):
        return redirect(url_for('auth.login'))

    flask_env = os.environ.get('FLASK_ENV', 'production')
    flask_debug = current_app.config.get('DEBUG', False)
    use_sqlite = current_app.config.get('USE_SQLITE_LOCALLY', False)

    if flask_env == 'production' or (not flask_debug and not use_sqlite):
        security_logger.warning(f'Tentativa de acesso a /dev-login em ambiente de produção')
        abort(404)

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
    if current_app.config.get('AUTH0_ENABLED', True):
        return redirect(url_for('auth.login'))

    flask_env = os.environ.get('FLASK_ENV', 'production')
    flask_debug = current_app.config.get('DEBUG', False)
    use_sqlite = current_app.config.get('USE_SQLITE_LOCALLY', False)

    if flask_env == 'production' or (not flask_debug and not use_sqlite):
        security_logger.warning(f'Tentativa de acesso a /dev-login-as em ambiente de produção')
        abort(404)

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
@rate_limit("100 per minute")
def register():
    """Página de registro de novos usuários."""

    if current_app.config.get('AUTH0_ENABLED', True):
        flash('Registro via Auth0. Use o botão de login para se registrar.', 'info')
        return redirect(url_for('auth.login'))

    if request.method == 'GET':
        try:
            session.pop('_flashes', None)
        except Exception:
            pass
        return render_template('register.html', auth0_enabled=False)

    email = (request.form.get('email') or '').strip().lower()
    nome = (request.form.get('nome') or '').strip()
    password = request.form.get('password', '')
    password_confirm = request.form.get('password_confirm', '')

    if not all([email, nome, password, password_confirm]):
        flash('Por favor, preencha todos os campos.', 'error')
        return render_template('register.html', auth0_enabled=False)

    try:
        from ..common.validation import validate_email
        email = validate_email(email)
    except Exception as e:
        flash(f'E-mail inválido: {str(e)}', 'error')
        return render_template('register.html', auth0_enabled=False)

    try:
        from ..common.validation import sanitize_string
        nome = sanitize_string(nome, min_length=2, max_length=100, allow_html=False)
    except Exception as e:
        flash(f'Nome inválido: {str(e)}', 'error')
        return render_template('register.html', auth0_enabled=False)

    try:
        from ..common.validation import validate_password_strength, ValidationError
        validate_password_strength(password)
    except ValidationError as ve:
        flash(str(ve), 'error')
        return render_template('register.html', auth0_enabled=False)

    if password != password_confirm:
        flash('As senhas não coincidem.', 'error')
        return render_template('register.html', auth0_enabled=False)

    usuario_existente = query_db("SELECT usuario FROM usuarios WHERE usuario = %s", (email,), one=True)
    if usuario_existente:
        flash('Este e-mail já está cadastrado. Faça login ou use outro e-mail.', 'error')
        return render_template('register.html', auth0_enabled=False)

    try:
        senha_hash = generate_password_hash(password)
        execute_db(
            "INSERT INTO usuarios (usuario, senha) VALUES (%s, %s)",
            (email, senha_hash)
        )

        execute_db(
            "INSERT INTO perfil_usuario (usuario, nome, perfil_acesso) VALUES (%s, %s, %s)",
            (email, nome, None)
        )

        auth_logger.info(f'New user registered: {email}')
        flash('Conta criada com sucesso! Faça login para continuar.', 'success')
        return redirect(url_for('auth.login'))

    except (Psycopg2IntegrityError, Sqlite3IntegrityError):
        flash('Este e-mail já está cadastrado.', 'error')
        return render_template('register.html', auth0_enabled=False)
    except Exception as e:
        auth_logger.error(f'Error registering user {email}: {str(e)}')
        flash('Erro ao criar conta. Tente novamente mais tarde.', 'error')
        return render_template('register.html', auth0_enabled=False)
