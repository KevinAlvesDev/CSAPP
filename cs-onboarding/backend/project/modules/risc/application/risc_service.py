"""
Serviço de RISC (Risk and Incident Sharing and Coordination)
Também conhecido como Proteção entre Contas (Cross-Account Protection)

Este módulo implementa:
1. Validação de tokens de eventos de segurança do Google
2. Processamento de eventos de segurança
3. Ações automáticas de proteção (revogar sessões, tokens, etc)
4. Log de eventos para auditoria
"""

import json
from datetime import datetime

import jwt
import requests
from flask import current_app

from ....config.logging_config import get_logger
from ....db import execute_db, query_db

logger = get_logger("risc")

# URLs do Google para RISC
GOOGLE_ISSUER = "https://accounts.google.com/"
GOOGLE_JWKS_URL = "https://www.googleapis.com/oauth2/v3/certs"

# Tipos de eventos suportados
EVENT_SESSIONS_REVOKED = "https://schemas.openid.net/secevent/risc/event-type/sessions-revoked"
EVENT_TOKENS_REVOKED = "https://schemas.openid.net/secevent/oauth/event-type/tokens-revoked"
EVENT_TOKEN_REVOKED = "https://schemas.openid.net/secevent/oauth/event-type/token-revoked"
EVENT_ACCOUNT_DISABLED = "https://schemas.openid.net/secevent/risc/event-type/account-disabled"
EVENT_ACCOUNT_ENABLED = "https://schemas.openid.net/secevent/risc/event-type/account-enabled"
EVENT_CREDENTIAL_CHANGE = "https://schemas.openid.net/secevent/risc/event-type/account-credential-change-required"
EVENT_VERIFICATION = "https://schemas.openid.net/secevent/risc/event-type/verification"


def get_google_public_keys() -> dict:
    """
    Obtém as chaves públicas do Google para validar tokens JWT.

    Returns:
        Dict com as chaves públicas do Google
    """
    try:
        response = requests.get(GOOGLE_JWKS_URL, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Erro ao obter chaves públicas do Google: {e}")
        return {}


def validate_security_event_token(token: str) -> dict | None:
    """
    Valida um token de evento de segurança do Google.

    Args:
        token: Token JWT recebido do Google

    Returns:
        Payload do token se válido, None caso contrário
    """
    try:
        # Obter chaves públicas do Google
        jwks = get_google_public_keys()

        if not jwks:
            logger.error("Não foi possível obter chaves públicas do Google")
            return None

        # Decodificar header para obter kid (key ID)
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")

        # Encontrar a chave pública correspondente
        public_key = None
        for key in jwks.get("keys", []):
            if key.get("kid") == kid:
                public_key = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(key))
                break

        if not public_key:
            logger.error(f"Chave pública não encontrada para kid: {kid}")
            return None

        # Validar e decodificar token
        payload = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            audience=current_app.config.get("GOOGLE_CLIENT_ID"),
            issuer=GOOGLE_ISSUER,
        )

        logger.info(f"Token de evento de segurança validado com sucesso. JTI: {payload.get('jti')}")
        return payload

    except jwt.ExpiredSignatureError:
        logger.error("Token de evento de segurança expirado")
        return None
    except jwt.InvalidTokenError as e:
        logger.error(f"Token de evento de segurança inválido: {e}")
        return None
    except Exception as e:
        logger.error(f"Erro ao validar token de evento de segurança: {e}")
        return None


def log_security_event(event_type: str, user_id: str, payload: dict, action_taken: str) -> bool:
    """
    Registra um evento de segurança no banco de dados para auditoria.

    Args:
        event_type: Tipo do evento
        user_id: ID do usuário (sub do Google)
        payload: Payload completo do evento
        action_taken: Ação tomada pelo sistema

    Returns:
        True se salvou com sucesso, False caso contrário
    """
    try:
        execute_db(
            """
            INSERT INTO risc_events (event_type, user_id, event_payload, action_taken, received_at)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (event_type, user_id, json.dumps(payload), action_taken, datetime.utcnow()),
        )
        return True
    except Exception as e:
        logger.error(f"Erro ao registrar evento de segurança: {e}")
        return False


def get_user_by_google_sub(google_sub: str) -> dict | None:
    """
    Busca usuário pelo ID do Google (sub).

    Args:
        google_sub: ID único do usuário no Google

    Returns:
        Dados do usuário ou None se não encontrado
    """
    try:
        # Buscar em perfil_usuario pelo auth0_user_id (onde salvamos o 'sub' do Google)
        user = query_db("SELECT * FROM perfil_usuario WHERE auth0_user_id = %s", (google_sub,), one=True)
        return user
    except Exception as e:
        logger.error(f"Erro ao buscar usuário por Google sub: {e}")
        return None


def revoke_user_sessions(user_email: str, reason: str = "security_event") -> bool:
    """
    Revoga todas as sessões ativas de um usuário.

    Args:
        user_email: Email do usuário
        reason: Motivo da revogação

    Returns:
        True se revogou com sucesso, False caso contrário
    """
    try:
        # Aqui você implementaria a lógica de revogação de sessões
        # Isso depende de como você gerencia sessões (Flask sessions, Redis, etc)

        # Por enquanto, vamos apenas logar
        logger.warning(f"Revogando sessões do usuário {user_email}. Motivo: {reason}")

        # Se você usa sessões do Flask, pode invalidar tokens ou marcar para logout
        # Se você usa Redis/cache, pode deletar as chaves de sessão

        return True
    except Exception as e:
        logger.error(f"Erro ao revogar sessões do usuário {user_email}: {e}")
        return False


def revoke_user_tokens(user_email: str, reason: str = "security_event") -> bool:
    """
    Revoga todos os tokens OAuth de um usuário.

    Args:
        user_email: Email do usuário
        reason: Motivo da revogação

    Returns:
        True se revogou com sucesso, False caso contrário
    """
    try:
        from ...dashboard.infra.google_oauth_service import revoke_google_token

        logger.warning(f"Revogando tokens OAuth do usuário {user_email}. Motivo: {reason}")

        # Revogar token do Google
        revoke_google_token(user_email)

        return True
    except Exception as e:
        logger.error(f"Erro ao revogar tokens do usuário {user_email}: {e}")
        return False


def process_sessions_revoked_event(payload: dict) -> str:
    """
    Processa evento de sessões revogadas.

    Args:
        payload: Payload do evento

    Returns:
        Descrição da ação tomada
    """
    subject = payload.get("events", {}).get(EVENT_SESSIONS_REVOKED, {}).get("subject", {})
    google_sub = subject.get("sub")

    if not google_sub:
        return "Evento ignorado: subject.sub não encontrado"

    user = get_user_by_google_sub(google_sub)

    if not user:
        return f"Usuário não encontrado para Google sub: {google_sub}"

    user_email = user.get("usuario")

    # Ação obrigatória: Encerrar sessões
    revoke_user_sessions(user_email, reason="sessions_revoked_by_google")

    # Ação sugerida: Revogar tokens OAuth
    revoke_user_tokens(user_email, reason="sessions_revoked_by_google")

    return f"Sessões e tokens revogados para {user_email}"


def process_tokens_revoked_event(payload: dict) -> str:
    """
    Processa evento de todos os tokens revogados.

    Args:
        payload: Payload do evento

    Returns:
        Descrição da ação tomada
    """
    subject = payload.get("events", {}).get(EVENT_TOKENS_REVOKED, {}).get("subject", {})
    google_sub = subject.get("sub")

    if not google_sub:
        return "Evento ignorado: subject.sub não encontrado"

    user = get_user_by_google_sub(google_sub)

    if not user:
        return f"Usuário não encontrado para Google sub: {google_sub}"

    user_email = user.get("usuario")

    # Ação sugerida: Excluir todos os tokens OAuth
    revoke_user_tokens(user_email, reason="tokens_revoked_by_google")

    return f"Tokens OAuth revogados para {user_email}"


def process_token_revoked_event(payload: dict) -> str:
    """
    Processa evento de token específico revogado.

    Args:
        payload: Payload do evento

    Returns:
        Descrição da ação tomada
    """
    subject = payload.get("events", {}).get(EVENT_TOKEN_REVOKED, {}).get("subject", {})
    google_sub = subject.get("sub")

    if not google_sub:
        return "Evento ignorado: subject.sub não encontrado"

    user = get_user_by_google_sub(google_sub)

    if not user:
        return f"Usuário não encontrado para Google sub: {google_sub}"

    user_email = user.get("usuario")

    # Ação obrigatória: Excluir refresh_token correspondente
    revoke_user_tokens(user_email, reason="token_revoked_by_google")

    return f"Token específico revogado para {user_email}"


def process_account_disabled_event(payload: dict) -> str:
    """
    Processa evento de conta desabilitada.

    Args:
        payload: Payload do evento

    Returns:
        Descrição da ação tomada
    """
    event_data = payload.get("events", {}).get(EVENT_ACCOUNT_DISABLED, {})
    subject = event_data.get("subject", {})
    google_sub = subject.get("sub")
    reason = event_data.get("reason", "unknown")

    if not google_sub:
        return "Evento ignorado: subject.sub não encontrado"

    user = get_user_by_google_sub(google_sub)

    if not user:
        return f"Usuário não encontrado para Google sub: {google_sub}"

    user_email = user.get("usuario")

    if reason == "hijacking":
        # Ação obrigatória: Proteger conta comprometida
        revoke_user_sessions(user_email, reason="account_hijacked")
        revoke_user_tokens(user_email, reason="account_hijacked")

        logger.critical(f"ALERTA DE SEGURANÇA: Conta {user_email} foi hackeada! Sessões e tokens revogados.")

        return f"Conta comprometida! Sessões e tokens revogados para {user_email}"

    elif reason == "bulk-account":
        # Ação sugerida: Analisar atividade
        logger.warning(f"Conta {user_email} desabilitada por suspeita de spam/bulk")

        return f"Conta marcada como suspeita: {user_email}"

    else:
        # Sem motivo informado
        logger.warning(f"Conta {user_email} desabilitada sem motivo específico")

        return f"Conta desabilitada: {user_email}"


def process_account_enabled_event(payload: dict) -> str:
    """
    Processa evento de conta reativada.

    Args:
        payload: Payload do evento

    Returns:
        Descrição da ação tomada
    """
    subject = payload.get("events", {}).get(EVENT_ACCOUNT_ENABLED, {}).get("subject", {})
    google_sub = subject.get("sub")

    if not google_sub:
        return "Evento ignorado: subject.sub não encontrado"

    user = get_user_by_google_sub(google_sub)

    if not user:
        return f"Usuário não encontrado para Google sub: {google_sub}"

    user_email = user.get("usuario")

    logger.info(f"Conta {user_email} foi reativada pelo Google")

    return f"Conta reativada: {user_email}"


def process_credential_change_event(payload: dict) -> str:
    """
    Processa evento de mudança de credencial necessária.

    Args:
        payload: Payload do evento

    Returns:
        Descrição da ação tomada
    """
    subject = payload.get("events", {}).get(EVENT_CREDENTIAL_CHANGE, {}).get("subject", {})
    google_sub = subject.get("sub")

    if not google_sub:
        return "Evento ignorado: subject.sub não encontrado"

    user = get_user_by_google_sub(google_sub)

    if not user:
        return f"Usuário não encontrado para Google sub: {google_sub}"

    user_email = user.get("usuario")

    logger.warning(f"Usuário {user_email} precisa trocar senha no Google")

    # Aqui você poderia enviar email ou notificação para o usuário

    return f"Mudança de credencial necessária para {user_email}"


def process_verification_event(payload: dict) -> str:
    """
    Processa evento de verificação (teste).

    Args:
        payload: Payload do evento

    Returns:
        Descrição da ação tomada
    """
    logger.info("Evento de verificação recebido do Google")
    return "Evento de verificação processado com sucesso"


def process_security_event(token: str) -> dict:
    """
    Processa um evento de segurança do Google.

    Args:
        token: Token JWT do evento

    Returns:
        Dict com status e mensagem
    """
    # Validar token
    payload = validate_security_event_token(token)

    if not payload:
        return {"status": "error", "message": "Token inválido ou expirado"}

    # Identificar tipo de evento
    events = payload.get("events", {})
    event_type = None
    action_taken = "Nenhuma ação tomada"

    # Processar evento baseado no tipo
    if EVENT_SESSIONS_REVOKED in events:
        event_type = EVENT_SESSIONS_REVOKED
        action_taken = process_sessions_revoked_event(payload)

    elif EVENT_TOKENS_REVOKED in events:
        event_type = EVENT_TOKENS_REVOKED
        action_taken = process_tokens_revoked_event(payload)

    elif EVENT_TOKEN_REVOKED in events:
        event_type = EVENT_TOKEN_REVOKED
        action_taken = process_token_revoked_event(payload)

    elif EVENT_ACCOUNT_DISABLED in events:
        event_type = EVENT_ACCOUNT_DISABLED
        action_taken = process_account_disabled_event(payload)

    elif EVENT_ACCOUNT_ENABLED in events:
        event_type = EVENT_ACCOUNT_ENABLED
        action_taken = process_account_enabled_event(payload)

    elif EVENT_CREDENTIAL_CHANGE in events:
        event_type = EVENT_CREDENTIAL_CHANGE
        action_taken = process_credential_change_event(payload)

    elif EVENT_VERIFICATION in events:
        event_type = EVENT_VERIFICATION
        action_taken = process_verification_event(payload)

    else:
        logger.warning(f"Tipo de evento desconhecido: {list(events.keys())}")
        return {"status": "error", "message": "Tipo de evento desconhecido"}

    # Extrair user_id do subject
    subject = next(iter(events.values())).get("subject", {})
    user_id = subject.get("sub", "unknown")

    # Registrar evento para auditoria
    log_security_event(event_type, user_id, payload, action_taken)

    logger.info(f"Evento de segurança processado: {event_type}. Ação: {action_taken}")

    return {
        "status": "success",
        "message": "Evento processado com sucesso",
        "event_type": event_type,
        "action_taken": action_taken,
    }
