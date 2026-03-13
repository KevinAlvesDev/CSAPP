import contextlib
import os
from functools import wraps
import logging
logger = logging.getLogger(__name__)

from flask import Blueprint, current_app, flash, g, redirect, render_template, request, session, url_for

from ..config.logging_config import auth_logger, security_logger
from ..constants import PERFIL_ADMIN, PERFIS_COM_GESTAO
from ..core.extensions import limiter
from ..modules.auth.application.auth_service import (
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
            try:
                auth_logger.info(f"Login required: anonymous access to {request.path}")
            except Exception as e:
                auth_logger.warning(
                    f"Falha ao registrar acesso anonimo em login_required: {e}", exc_info=True
                )

            if request.is_json or request.headers.get("Accept", "").startswith("application/json"):
                from flask import jsonify

                return jsonify({"error": "Não autenticado", "message": "Login necessário"}), 401

            try:
                if current_app.secret_key:
                    flash("Login necessário para acessar esta página.", "info")
            except Exception as e:
                auth_logger.warning(f"Falha ao exibir mensagem de flash (login necessário): {e}", exc_info=True)
            return redirect(url_for("auth.login"))

        if not g.perfil or g.perfil.get("perfil_acesso") is None:
            try:
                from ..common.context_profiles import get_contextual_profile

                sync_user_profile_service(g.user_email, g.user.get("name", g.user_email), g.user.get("sub"))
                g.perfil = get_contextual_profile(g.user_email, getattr(g, "modulo_atual", None))

                if not g.perfil:
                    g.perfil = {
                        "nome": g.user.get("name", g.user_email),
                        "usuario": g.user_email,
                        "foto_url": None,
                        "cargo": None,
                        "perfil_acesso": None,
                        "contexto": getattr(g, "modulo_atual", "onboarding"),
                    }

            except ValueError as ve:
                flash(str(ve), "error")
                session.clear()
                return redirect(url_for("auth.login"))
            except Exception as e:
                auth_logger.warning(f"Falha ao sincronizar perfil do usuário durante autenticação: {e}", exc_info=True)

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
                    except Exception as e:
                        auth_logger.warning(f"Falha ao exibir mensagem de flash (acesso negado - gestão): {e}", exc_info=True)
                else:
                    try:
                        if current_app.secret_key:
                            flash("Acesso negado. Você não tem permissão para esta funcionalidade.", "error")
                    except Exception as e:
                        auth_logger.warning(f"Falha ao exibir mensagem de flash (acesso negado): {e}", exc_info=True)

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
        except Exception as e:
            auth_logger.warning(f"Falha ao verificar configuração de rate limit: {e}", exc_info=True)
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
    login_bg_file = current_app.config.get("LOGIN_BG_FILE", "imagens/Meet_TimesSquare.png")
    try:
        static_folder = os.path.abspath(current_app.static_folder or "")
        candidate_path = os.path.join(static_folder, login_bg_file)
        if not (static_folder and os.path.isfile(candidate_path)):
            # Tentar fallback padrão
            fallback = os.path.join(static_folder, "imagens", "teladelogin.jpg")
            if os.path.isfile(fallback):
                login_bg_file = "imagens/Meet_TimesSquare.png"
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
                    login_bg_file = f"imagens/{chosen}" if chosen else "imagens/Meet_TimesSquare.png"
                except Exception as e:
                    auth_logger.warning(
                        f"Falha ao detectar imagem de login disponível: {e}", exc_info=True
                    )
                    login_bg_file = "imagens/Meet_TimesSquare.png"
    except Exception as e:
        auth_logger.warning(f"Falha ao resolver imagem de login: {e}", exc_info=True)
        login_bg_file = "imagens/Meet_TimesSquare.png"

    google_enabled = current_app.config.get("GOOGLE_OAUTH_ENABLED", False)

    return render_template(
        "auth/login.html", use_custom_auth=google_enabled, login_bg_file=login_bg_file
    )





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

    # Usar redirect URI configurada quando definida (evita mismatch com Google Console)
    configured_redirect = current_app.config.get("GOOGLE_REDIRECT_URI")
    if configured_redirect:
        redirect_uri = configured_redirect
        auth_logger.info(f"Usando GOOGLE_REDIRECT_URI configurada: {redirect_uri}")
    else:
        # Usar SEMPRE o host atual para evitar perda de sessão/state
        redirect_uri = url_for("auth.google_callback", _external=True)

    # CORREÇÃO CRÍTICA PARA REDIRECT_URI_MISMATCH:
    # Se não estivermos em debug, forçar HTTPS na URI de retorno.
    # Isso resolve problemas onde o servidor está atrás de um proxy HTTP mas o Google espera HTTPS.
    is_debug = current_app.config.get("DEBUG", False)
    preferred_scheme = current_app.config.get("PREFERRED_URL_SCHEME", "https")
    if configured_redirect:
        # Respeitar a URI configurada explicitamente
        pass
    elif preferred_scheme == "http":
        auth_logger.info(f"Usando HTTP na redirect_uri (dev): {redirect_uri}")
    elif not is_debug and redirect_uri.startswith("http://"):
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

        if not email.endswith("@pactosolucoes.com.br") and not is_admin_email:
            auth_logger.warning(f"Google Login blocked: Invalid domain {email}", exc_info=True)
            flash("Acesso restrito a contas @pactosolucoes.com.br", "error")
            return redirect(url_for("auth.login"))

        # Validação externa no OAMD removida por decisão do usuário.
        user_name_final = user_info.get("name", email)

        # Sincronizar usuário (Criará no banco local apenas agora que foi validado externamente)
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
            from datetime import datetime, timedelta, timezone

            from ..modules.dashboard.infra.google_oauth_service import save_user_google_token

            # Preparar token para salvar
            token_to_save = {
                "access_token": token.get("access_token"),
                "refresh_token": token.get("refresh_token"),
                "token_type": token.get("token_type", "Bearer"),
                "expires_at": datetime.now(timezone.utc) + timedelta(seconds=token.get("expires_in", 3600)),
                "scope": token.get("scope", "openid email profile"),
            }

            save_user_google_token(email, token_to_save)
            auth_logger.info(f"Token do Google salvo no banco para {email}")
        except Exception as token_err:
            auth_logger.warning(f"Falha ao salvar token do Google: {token_err}", exc_info=True)

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
