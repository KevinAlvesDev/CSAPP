import contextlib
import os
from functools import wraps

from flask import Blueprint, abort, current_app, flash, g, redirect, render_template, request, session, url_for

from ..config.logging_config import auth_logger, security_logger
from ..constants import ADMIN_EMAIL, PERFIL_ADMIN, PERFIL_IMPLANTADOR, PERFIS_COM_GESTAO
from ..core.extensions import limiter
from ..domain.auth_service import (
    find_cs_user_external_service,
    get_user_profile_service,
    sync_user_profile_service,
    update_user_role_service,
)

auth_bp = Blueprint("auth", __name__)


def login_required(f):
    """
    Decorator para proteger rotas que exigem login.
    Assume que @app.before_request (em __init__.py) já carregou g.user e g.perfil.
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not g.user_email:
            with contextlib.suppress(Exception):
                auth_logger.info(f"Login required: anonymous access to {request.path}")

            if request.is_json or request.headers.get("Accept", "").startswith("application/json"):
                from flask import jsonify

                return jsonify({"error": "Não autenticado", "message": "Login necessário"}), 401

            try:
                if current_app.secret_key:
                    flash("Login necessário para acessar esta página.", "info")
            except Exception:
                pass
            return redirect(url_for("auth.login"))

        if not g.perfil or g.perfil.get("perfil_acesso") is None:
            try:
                sync_user_profile_service(g.user_email, g.user.get("name", g.user_email), g.user.get("sub"))
                g.perfil = get_user_profile_service(g.user_email)

                if not g.perfil:
                    g.perfil = {
                        "nome": g.user.get("name", g.user_email),
                        "usuario": g.user_email,
                        "foto_url": None,
                        "cargo": None,
                        "perfil_acesso": None,
                    }

            except ValueError as ve:
                flash(str(ve), "error")
                session.clear()
                return redirect(url_for("auth.login"))
            except Exception:
                pass

        perfil_acesso_debug = g.perfil.get("perfil_acesso") if g.perfil else "NÃO CARREGADO"
        auth_logger.info(f"User authenticated: {g.user_email}, Role: {perfil_acesso_debug}, Path: {request.path}")

        return f(*args, **kwargs)

    return decorated_function


def permission_required(required_profiles):
    """Decorator para proteger rotas por Perfil de Acesso."""

    def decorator(f):
        @wraps(f)
        @login_required
        def decorated_function(*args, **kwargs):
            user_perfil = g.perfil.get("perfil_acesso") if g.perfil else None

            if user_perfil is None or user_perfil not in required_profiles:
                if any(p in required_profiles for p in PERFIS_COM_GESTAO):
                    try:
                        if current_app.secret_key:
                            flash(
                                "Seu perfil de acesso atual não tem permissão para essa função, entre em contato com um administrador.",
                                "error",
                            )
                    except Exception:
                        pass
                else:
                    try:
                        if current_app.secret_key:
                            flash("Acesso negado. Você não tem permissão para esta funcionalidade.", "error")
                    except Exception:
                        pass

                security_logger.warning(
                    f"Access denied for user {g.user_email} with role {user_perfil} trying to access {request.path}"
                )
                return redirect(url_for("core.modules_selection"))
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

            if current_app and not current_app.config.get("RATELIMIT_ENABLED", True):
                return f
        except Exception:
            pass
        if limiter:
            return limiter.limit(max_requests)(f)
        return f

    return decorator


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """
    Página de login.
    Agora suporta apenas login via Google OAuth.
    O POST foi removido pois não há mais formulário de senha.
    """
    # Se usuário já estiver logado, redireciona para seleção de módulos
    if g.user:
        return redirect(url_for("core.modules_selection"))

    # Renderiza a página de login
    login_bg_file = current_app.config.get("LOGIN_BG_FILE", "imagens/teladelogin.jpg")
    try:
        static_folder = os.path.abspath(current_app.static_folder or "")
        candidate_path = os.path.join(static_folder, login_bg_file)
        if not (static_folder and os.path.isfile(candidate_path)):
            # Tentar fallback padrão
            fallback = os.path.join(static_folder, "imagens", "teladelogin.jpg")
            if os.path.isfile(fallback):
                login_bg_file = "imagens/teladelogin.jpg"
            else:
                # Detectar automaticamente qualquer imagem disponível em /static/imagens
                imgs_dir = os.path.join(static_folder, "imagens")
                chosen = None
                try:
                    for fname in os.listdir(imgs_dir):
                        lower = fname.lower()
                        if lower.endswith((".jpg", ".jpeg", ".png", ".webp")):
                            chosen = fname
                            # Preferir arquivos contendo '25' ou 'anos'
                            if "25" in lower or "anos" in lower:
                                chosen = fname
                                break
                    login_bg_file = f"imagens/{chosen}" if chosen else "imagens/teladelogin.jpg"
                except Exception:
                    login_bg_file = "imagens/teladelogin.jpg"
    except Exception:
        login_bg_file = "imagens/teladelogin.jpg"
    google_enabled = current_app.config.get("GOOGLE_OAUTH_ENABLED", False)
    return render_template(
        "auth/login.html", auth0_enabled=False, use_custom_auth=google_enabled, login_bg_file=login_bg_file
    )


@auth_bp.route("/check_user_external", methods=["POST"])
@limiter.limit("10 per minute")  # Prevenir enumeração de usuários
def check_user_external() -> tuple[dict, int]:
    """
    Endpoint para verificar se o usuário existe no banco externo.
    Retorna JSON para uso via AJAX na tela de login.
    """
    data = request.get_json()
    email = data.get("email")

    if not email:
        return {"status": "error", "message": "Email não fornecido"}, 400

    try:
        from ..common.validation import validate_email

        email = validate_email(email)
    except Exception:
        return {"status": "error", "message": "Email inválido"}, 400

    try:
        cs_user = find_cs_user_external_service(email)
        if cs_user:
            if cs_user.get("ativo"):
                return {"status": "success", "message": "Usuário encontrado", "user_name": cs_user.get("nome")}, 200
            else:
                return {"status": "error", "message": "Usuário encontrado, mas inativo"}, 200
        else:
            return {"status": "error", "message": "Usuário não encontrado na base CS"}, 200
    except Exception as e:
        auth_logger.error(f"Erro na verificação externa via API: {e}")
        return {"status": "error", "message": "Erro ao consultar banco externo"}, 500


@auth_bp.route("/login/google")
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

    if not current_app.config.get("GOOGLE_OAUTH_ENABLED"):
        auth_logger.error("Google OAuth não está habilitado nas configurações")
        flash("Login com Google não está configurado.", "error")
        return redirect(url_for("auth.login"))

    # Usar SEMPRE o host atual para evitar perda de sessão/state
    redirect_uri = url_for("auth.google_callback", _external=True)

    # CORREÇÃO CRÍTICA PARA REDIRECT_URI_MISMATCH:
    # Se não estivermos rodando localmente (SQLite/Debug), forçar HTTPS na URI de retorno.
    # Isso resolve problemas onde o servidor está atrás de um proxy HTTP mas o Google espera HTTPS.
    is_local = current_app.config.get("USE_SQLITE_LOCALLY", False) or current_app.config.get("DEBUG", False)
    if not is_local and redirect_uri.startswith("http://"):
        redirect_uri = redirect_uri.replace("http://", "https://", 1)
        auth_logger.info(f"Forçando HTTPS na redirect_uri: {redirect_uri}")

    auth_logger.info(f"Redirecionando para Google com callback (FINAL): {redirect_uri}")
    # prompt='select_account' força o Google a mostrar a tela de escolha de conta
    return oauth.google.authorize_redirect(redirect_uri, prompt="select_account")


@auth_bp.route("/login/google/callback")
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
    from ..constants import ADMIN_EMAIL
    from ..core.extensions import oauth

    auth_logger.info("Recebido callback do Google")

    try:
        token = oauth.google.authorize_access_token()
        auth_logger.info("Token de acesso obtido com sucesso")

        # userinfo geralmente vem no token se openid scope for usado,
        # mas garantimos chamando userinfo() se disponivel ou pegando do token
        user_info = token.get("userinfo")
        if not user_info:
            user_info = oauth.google.userinfo()

        auth_logger.info(f"Informações do usuário obtidas: {user_info.get('email')}")

        email = user_info.get("email")

        if not email:
            auth_logger.error("E-mail não encontrado nas informações do usuário")
            flash("Não foi possível obter o e-mail da sua conta Google.", "error")
            return redirect(url_for("auth.login"))

        # Validação de Domínio
        # Permitir login do ADMIN_EMAIL mesmo se for de outro domínio (ex: gmail)
        from ..constants import ADMIN_EMAIL

        email_clean = (email or "").strip().lower()
        is_admin_email = email_clean == (ADMIN_EMAIL or "").strip().lower()

        # Permitir explicitamente o e-mail solicitado, ignorando env vars antigas
        is_master_user = email_clean == "kevinalveswp@gmail.com"

        if not email.endswith("@pactosolucoes.com.br") and not is_admin_email and not is_master_user:
            auth_logger.warning(f"Google Login blocked: Invalid domain {email}")
            flash("Acesso restrito a contas @pactosolucoes.com.br", "error")
            return redirect(url_for("auth.login"))

        # --- LOGIN SIMPLIFICADO ---
        # Validação apenas por domínio Google (@pactosolucoes.com.br)
        # O banco externo OAMD não é mais obrigatório para login
        auth_logger.info(f"Login aprovado para {email} (domínio válido)")
        user_name_final = user_info.get("name", email)
        # -------------------------------------

        # Sincronizar usuário
        # Usamos o 'sub' do Google como ID único
        sync_user_profile_service(email, user_name_final, user_info.get("sub"))

        # Enforce admin role for ADMIN_EMAIL
        try:
            from ..constants import ADMIN_EMAIL, PERFIL_ADMIN

            if (email or "").strip().lower() == (ADMIN_EMAIL or "").strip().lower():
                auth_logger.info(f"Forcing admin role for {email}")
                update_user_role_service(email, PERFIL_ADMIN)
        except Exception as admin_err:
            auth_logger.error(f"Failed to set admin role: {admin_err}")

        # Configurar sessão (compatível com a estrutura existente que espera session['user'])
        session["user"] = user_info

        session.permanent = True

        # Salvar token do Google no banco de dados para autorização incremental
        try:
            from datetime import datetime, timedelta

            from ..domain.google_oauth_service import save_user_google_token

            # Preparar token para salvar
            token_to_save = {
                "access_token": token.get("access_token"),
                "refresh_token": token.get("refresh_token"),
                "token_type": token.get("token_type", "Bearer"),
                "expires_at": datetime.utcnow() + timedelta(seconds=token.get("expires_in", 3600)),
                "scope": token.get("scope", "openid email profile"),
            }

            save_user_google_token(email, token_to_save)
            auth_logger.info(f"Token do Google salvo no banco para {email}")
        except Exception as token_err:
            auth_logger.warning(f"Falha ao salvar token do Google: {token_err}")

        auth_logger.info(f"User logged in via Google: {email}")
        return redirect(url_for("core.modules_selection"))

    except Exception as e:
        auth_logger.error(f"Google Login Callback Error: {e}", exc_info=True)
        flash("Erro ao realizar login com Google. Tente novamente.", "error")
        return redirect(url_for("auth.login"))


@auth_bp.route("/logout")
def logout():
    """Desloga o usuário da sessão local."""
    session.clear()
    flash("Você saiu do sistema.", "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/dev-login", methods=["GET"])
def dev_login():
    """Login de desenvolvimento: cria sessão local sem Auth0.

    SEGURANÇA: Esta rota só funciona em ambiente de desenvolvimento.
    Em produção, retorna 404 para evitar acesso não autorizado.
    """

    import os

    flask_env = os.environ.get("FLASK_ENV", "production")
    flask_debug = current_app.config.get("DEBUG", False)
    use_sqlite = current_app.config.get("USE_SQLITE_LOCALLY", False)

    if flask_env == "production" or (not flask_debug and not use_sqlite):
        security_logger.warning("Tentativa de acesso a /dev-login em ambiente de produção")
        abort(404)

    if current_app.config.get("AUTH0_ENABLED", True):
        return redirect(url_for("auth.login"))

    dev_email = ADMIN_EMAIL
    session["user"] = {"email": dev_email, "name": "Dev User", "sub": "dev|local"}

    session.permanent = True

    try:
        sync_user_profile_service(dev_email, "Dev User", "dev|local")
    except Exception as e:
        auth_logger.warning(f"Falha ao sincronizar perfil dev {dev_email}: {e}")

    auth_logger.info(f"Dev login realizado: {dev_email}")
    flash("Logado em modo desenvolvimento com acesso de Administrador.", "success")
    return redirect(url_for("core.modules_selection"))


@auth_bp.route("/dev-login-as", methods=["GET", "POST"])
def dev_login_as():
    """Login de desenvolvimento com e-mail arbitrário (somente quando Auth0 está desativado).

    SEGURANÇA: Esta rota só funciona em ambiente de desenvolvimento.
    Em produção, retorna 404 para evitar acesso não autorizado.
    """

    import os

    flask_env = os.environ.get("FLASK_ENV", "production")
    flask_debug = current_app.config.get("DEBUG", False)
    use_sqlite = current_app.config.get("USE_SQLITE_LOCALLY", False)

    if flask_env == "production" or (not flask_debug and not use_sqlite):
        security_logger.warning("Tentativa de acesso a /dev-login-as em ambiente de produção")
        abort(404)

    if current_app.config.get("AUTH0_ENABLED", True):
        return redirect(url_for("auth.login"))

    if request.method == "GET":
        with contextlib.suppress(Exception):
            session.pop("_flashes", None)
        return render_template("auth/dev_login.html", auth0_enabled=False)

    email = (request.form.get("email") or "").strip()
    name = (request.form.get("name") or email).strip()

    if not email:
        flash("Informe um e-mail válido.", "error")
        return redirect(url_for("auth.dev_login_as"))

    try:
        from ..common.validation import validate_email

        email = validate_email(email)
    except Exception:
        flash("E-mail inválido.", "error")
        return redirect(url_for("auth.dev_login_as"))

    session["user"] = {"email": email, "name": name or email, "sub": "dev|manual"}
    session.permanent = True

    try:
        sync_user_profile_service(email, name or email, "dev|manual")

        if email != ADMIN_EMAIL:
            try:
                update_user_role_service(email, PERFIL_IMPLANTADOR)
            except Exception as role_err:
                auth_logger.warning(f"Não foi possível definir perfil Implantador para {email}: {role_err}")
    except Exception as e:
        auth_logger.warning(f"Falha ao sincronizar perfil dev para {email}: {e}")

    flash(f"Logado como {email} (desenvolvimento).", "success")
    return redirect(url_for("core.modules_selection"))
