"""
Serviço de gerenciamento de OAuth do Google com autorização incremental.

Este módulo implementa:
1. Autorização incremental (solicitar escopos conforme necessário)
2. Refresh automático de tokens
3. Armazenamento persistente de tokens no banco de dados
4. Gestão de múltiplos escopos por usuário
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional

from flask import current_app, session

from ..config.logging_config import get_logger
from ..db import execute_db, query_db

logger = get_logger("google_oauth")


# Escopos disponíveis
SCOPE_BASIC = "openid email profile"
SCOPE_CALENDAR = "https://www.googleapis.com/auth/calendar"
SCOPE_DRIVE_FILE = "https://www.googleapis.com/auth/drive.file"
SCOPE_DRIVE_READONLY = "https://www.googleapis.com/auth/drive.readonly"

# Mapeamento de funcionalidades para escopos
FEATURE_SCOPES = {
    "basic": SCOPE_BASIC,
    "calendar": SCOPE_CALENDAR,
    "drive_file": SCOPE_DRIVE_FILE,
    "drive_readonly": SCOPE_DRIVE_READONLY,
}


def get_user_google_token(user_email: str) -> Optional[Dict]:
    """
    Recupera o token do Google armazenado para um usuário.

    Args:
        user_email: Email do usuário

    Returns:
        Dict com token ou None se não existir
    """
    try:
        token_data = query_db(
            """
            SELECT access_token, refresh_token, token_type, expires_at, scopes
            FROM google_tokens
            WHERE usuario = %s
            """,
            (user_email,),
            one=True,
        )

        if not token_data:
            return None

        return {
            "access_token": token_data["access_token"],
            "refresh_token": token_data["refresh_token"],
            "token_type": token_data.get("token_type", "Bearer"),
            "expires_at": token_data.get("expires_at"),
            "scopes": token_data.get("scopes", "").split(" ") if token_data.get("scopes") else [],
        }
    except Exception as e:
        logger.error(f"Erro ao recuperar token do Google para {user_email}: {e}")
        return None


def save_user_google_token(user_email: str, token: Dict) -> bool:
    """
    Salva ou atualiza o token do Google para um usuário.

    Args:
        user_email: Email do usuário
        token: Dict contendo access_token, refresh_token, expires_at, etc.

    Returns:
        True se salvou com sucesso, False caso contrário
    """
    try:
        # Extrair escopos do token
        scopes = token.get("scope", "")
        if isinstance(scopes, list):
            scopes = " ".join(scopes)

        execute_db(
            """
            INSERT INTO google_tokens (usuario, access_token, refresh_token, token_type, expires_at, scopes, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (usuario) DO UPDATE SET
                access_token = EXCLUDED.access_token,
                refresh_token = COALESCE(EXCLUDED.refresh_token, google_tokens.refresh_token),
                token_type = EXCLUDED.token_type,
                expires_at = EXCLUDED.expires_at,
                scopes = EXCLUDED.scopes,
                updated_at = EXCLUDED.updated_at
            """,
            (
                user_email,
                token.get("access_token"),
                token.get("refresh_token"),
                token.get("token_type", "Bearer"),
                token.get("expires_at"),
                scopes,
                datetime.utcnow(),
            ),
        )
        logger.info(f"Token do Google salvo para {user_email}")
        return True
    except Exception as e:
        logger.error(f"Erro ao salvar token do Google para {user_email}: {e}")
        return False


def token_is_expired(token: Dict) -> bool:
    """
    Verifica se um token está expirado.

    Args:
        token: Dict contendo expires_at

    Returns:
        True se expirado, False caso contrário
    """
    if not token or "expires_at" not in token:
        return True

    expires_at = token["expires_at"]
    if isinstance(expires_at, str):
        try:
            expires_at = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
        except:
            return True

    # Considerar expirado se faltar menos de 5 minutos
    return datetime.utcnow() >= expires_at - timedelta(minutes=5)


def refresh_google_token(user_email: str, refresh_token: str) -> Optional[Dict]:
    """
    Atualiza um token do Google usando o refresh_token.

    Args:
        user_email: Email do usuário
        refresh_token: Refresh token do Google

    Returns:
        Novo token ou None se falhar
    """
    try:
        import requests

        response = requests.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": current_app.config["GOOGLE_CLIENT_ID"],
                "client_secret": current_app.config["GOOGLE_CLIENT_SECRET"],
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
            timeout=10,
        )

        if response.status_code != 200:
            logger.error(f"Erro ao atualizar token do Google: {response.text}")
            return None

        new_token = response.json()

        # Calcular expires_at
        expires_in = new_token.get("expires_in", 3600)
        new_token["expires_at"] = datetime.utcnow() + timedelta(seconds=expires_in)

        # Manter o refresh_token original se não vier um novo
        if "refresh_token" not in new_token:
            new_token["refresh_token"] = refresh_token

        # Salvar novo token
        save_user_google_token(user_email, new_token)

        logger.info(f"Token do Google atualizado para {user_email}")
        return new_token

    except Exception as e:
        logger.error(f"Erro ao atualizar token do Google para {user_email}: {e}")
        return None


def get_valid_token(user_email: str) -> Optional[Dict]:
    """
    Obtém um token válido do Google, atualizando se necessário.

    Args:
        user_email: Email do usuário

    Returns:
        Token válido ou None se não conseguir obter
    """
    # Tentar pegar da sessão primeiro
    token = session.get("google_token")

    # Se não estiver na sessão, tentar do banco
    if not token:
        token = get_user_google_token(user_email)

    if not token:
        return None

    # Se estiver expirado, tentar atualizar
    if token_is_expired(token):
        refresh_token = token.get("refresh_token")
        if not refresh_token:
            logger.warning(f"Token expirado sem refresh_token para {user_email}")
            return None

        token = refresh_google_token(user_email, refresh_token)

        if token:
            # Atualizar sessão
            session["google_token"] = token
            session.permanent = True

    return token


def user_has_scope(user_email: str, required_scope: str) -> bool:
    """
    Verifica se o usuário já concedeu um escopo específico.

    Args:
        user_email: Email do usuário
        required_scope: Escopo necessário

    Returns:
        True se o usuário tem o escopo, False caso contrário
    """
    token = get_user_google_token(user_email)

    if not token:
        return False

    scopes = token.get("scopes", [])
    if isinstance(scopes, str):
        scopes = scopes.split(" ")

    return required_scope in scopes


def get_authorization_url_with_scopes(scopes: List[str], user_email: str = None) -> str:
    """
    Gera URL de autorização do Google com escopos específicos.
    Implementa autorização incremental se o usuário já tiver alguns escopos.

    Args:
        scopes: Lista de escopos a solicitar
        user_email: Email do usuário (opcional, para autorização incremental)

    Returns:
        URL de autorização
    """
    from flask import url_for

    from ..core.extensions import oauth

    # Preparar parâmetros
    params = {
        "access_type": "offline",  # Para obter refresh_token
        "prompt": "consent",  # Forçar tela de consentimento
        "include_granted_scopes": "true",  # AUTORIZAÇÃO INCREMENTAL
    }

    # Se for para agenda, usar callback específico
    if SCOPE_CALENDAR in scopes:
        redirect_uri = url_for("agenda.agenda_callback", _external=True)
    else:
        redirect_uri = url_for("auth.google_callback", _external=True)

    # Forçar HTTPS em produção
    is_local = current_app.config.get("USE_SQLITE_LOCALLY", False) or current_app.config.get("DEBUG", False)
    if not is_local and redirect_uri.startswith("http://"):
        redirect_uri = redirect_uri.replace("http://", "https://", 1)

    logger.info(f"Gerando URL de autorização com escopos: {scopes}")
    logger.info(f"Redirect URI: {redirect_uri}")

    # Gerar URL
    return oauth.google.create_authorization_url(redirect_uri, scope=" ".join(scopes), **params)[0]


def revoke_google_token(user_email: str) -> bool:
    """
    Revoga o token do Google de um usuário.

    Args:
        user_email: Email do usuário

    Returns:
        True se revogou com sucesso, False caso contrário
    """
    try:
        import requests

        token = get_user_google_token(user_email)
        if not token:
            return False

        access_token = token.get("access_token")
        if not access_token:
            return False

        # Revogar no Google
        response = requests.post(
            "https://oauth2.googleapis.com/revoke",
            params={"token": access_token},
            headers={"content-type": "application/x-www-form-urlencoded"},
            timeout=10,
        )

        # Remover do banco
        execute_db("DELETE FROM google_tokens WHERE usuario = %s", (user_email,))

        # Remover da sessão
        session.pop("google_token", None)

        logger.info(f"Token do Google revogado para {user_email}")
        return True

    except Exception as e:
        logger.error(f"Erro ao revogar token do Google para {user_email}: {e}")
        return False
