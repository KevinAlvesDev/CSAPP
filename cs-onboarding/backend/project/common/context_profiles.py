from datetime import datetime

from flask import current_app, g

from ..db import db_connection, execute_db, query_db
from .context_navigation import normalize_context

VALID_CONTEXTS = ("onboarding", "grandes_contas", "ongoing")


def resolve_context(context=None):
    current_ctx = None
    try:
        current_ctx = getattr(g, "modulo_atual", None)
    except Exception:
        current_ctx = None
    ctx = normalize_context(context) or normalize_context(current_ctx)
    return ctx or "onboarding"


def ensure_context_profile_schema():
    """
    Garante tabelas de perfil/permissão por contexto e migra dados legados.
    Idempotente para SQLite e PostgreSQL.
    """
    conn = None
    try:
        with db_connection() as (conn, db_type):
            cursor = conn.cursor()
            if db_type == "sqlite":
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS perfil_usuario_contexto (
                        usuario TEXT NOT NULL,
                        contexto TEXT NOT NULL,
                        perfil_acesso TEXT,
                        atualizado_em DATETIME DEFAULT CURRENT_TIMESTAMP,
                        atualizado_por TEXT,
                        PRIMARY KEY (usuario, contexto),
                        FOREIGN KEY (usuario) REFERENCES usuarios(usuario) ON DELETE CASCADE
                    )
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS perfis_acesso_contexto (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        contexto TEXT NOT NULL,
                        nome VARCHAR(100) NOT NULL,
                        descricao TEXT,
                        sistema BOOLEAN DEFAULT 0,
                        ativo BOOLEAN DEFAULT 1,
                        cor VARCHAR(20) DEFAULT '#667eea',
                        icone VARCHAR(50) DEFAULT 'bi-person-badge',
                        criado_em DATETIME DEFAULT CURRENT_TIMESTAMP,
                        atualizado_em DATETIME DEFAULT CURRENT_TIMESTAMP,
                        criado_por VARCHAR(100),
                        UNIQUE(contexto, nome)
                    )
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS permissoes_contexto (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        perfil_ctx_id INTEGER NOT NULL REFERENCES perfis_acesso_contexto(id) ON DELETE CASCADE,
                        recurso_id INTEGER NOT NULL REFERENCES recursos(id) ON DELETE CASCADE,
                        concedida BOOLEAN DEFAULT 1,
                        criado_em DATETIME DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(perfil_ctx_id, recurso_id)
                    )
                    """
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_perfil_usuario_contexto_contexto ON perfil_usuario_contexto (contexto)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_perfis_acesso_contexto_contexto ON perfis_acesso_contexto (contexto)"
                )
            else:
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS perfil_usuario_contexto (
                        usuario TEXT NOT NULL REFERENCES usuarios(usuario) ON DELETE CASCADE,
                        contexto VARCHAR(50) NOT NULL,
                        perfil_acesso TEXT,
                        atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        atualizado_por TEXT,
                        PRIMARY KEY (usuario, contexto)
                    )
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS perfis_acesso_contexto (
                        id SERIAL PRIMARY KEY,
                        contexto VARCHAR(50) NOT NULL,
                        nome VARCHAR(100) NOT NULL,
                        descricao TEXT,
                        sistema BOOLEAN DEFAULT FALSE,
                        ativo BOOLEAN DEFAULT TRUE,
                        cor VARCHAR(20) DEFAULT '#667eea',
                        icone VARCHAR(50) DEFAULT 'bi-person-badge',
                        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        criado_por VARCHAR(100),
                        UNIQUE(contexto, nome)
                    )
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS permissoes_contexto (
                        id SERIAL PRIMARY KEY,
                        perfil_ctx_id INTEGER NOT NULL REFERENCES perfis_acesso_contexto(id) ON DELETE CASCADE,
                        recurso_id INTEGER NOT NULL REFERENCES recursos(id) ON DELETE CASCADE,
                        concedida BOOLEAN DEFAULT TRUE,
                        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(perfil_ctx_id, recurso_id)
                    )
                    """
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_perfil_usuario_contexto_contexto ON perfil_usuario_contexto (contexto)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_perfis_acesso_contexto_contexto ON perfis_acesso_contexto (contexto)"
                )

            # Migração: perfis por contexto
            if db_type == "sqlite":
                cursor.execute("SELECT nome, descricao, sistema, ativo, cor, icone, criado_por FROM perfis_acesso")
                perfis_base = cursor.fetchall() or []
                for perfil in perfis_base:
                    nome = perfil["nome"] if isinstance(perfil, dict) else perfil[0]
                    descricao = perfil["descricao"] if isinstance(perfil, dict) else perfil[1]
                    sistema = perfil["sistema"] if isinstance(perfil, dict) else perfil[2]
                    ativo = perfil["ativo"] if isinstance(perfil, dict) else perfil[3]
                    cor = perfil["cor"] if isinstance(perfil, dict) else perfil[4]
                    icone = perfil["icone"] if isinstance(perfil, dict) else perfil[5]
                    criado_por = perfil["criado_por"] if isinstance(perfil, dict) else perfil[6]
                    for ctx in VALID_CONTEXTS:
                        cursor.execute(
                            """
                            INSERT OR IGNORE INTO perfis_acesso_contexto
                            (contexto, nome, descricao, sistema, ativo, cor, icone, criado_por)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (ctx, nome, descricao, sistema, ativo, cor, icone, criado_por),
                        )

                cursor.execute(
                    """
                    INSERT OR IGNORE INTO permissoes_contexto (perfil_ctx_id, recurso_id, concedida, criado_em)
                    SELECT pc.id, p.recurso_id, p.concedida, CURRENT_TIMESTAMP
                    FROM permissoes p
                    JOIN perfis_acesso pa ON pa.id = p.perfil_id
                    JOIN perfis_acesso_contexto pc ON pc.nome = pa.nome
                    """
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO perfis_acesso_contexto
                    (contexto, nome, descricao, sistema, ativo, cor, icone, criado_por)
                    SELECT c.contexto, p.nome, p.descricao, p.sistema, p.ativo, p.cor, p.icone, p.criado_por
                    FROM perfis_acesso p
                    CROSS JOIN (VALUES ('onboarding'), ('grandes_contas'), ('ongoing')) AS c(contexto)
                    ON CONFLICT (contexto, nome) DO NOTHING
                    """
                )
                cursor.execute(
                    """
                    INSERT INTO permissoes_contexto (perfil_ctx_id, recurso_id, concedida, criado_em)
                    SELECT pc.id, p.recurso_id, p.concedida, CURRENT_TIMESTAMP
                    FROM permissoes p
                    JOIN perfis_acesso pa ON pa.id = p.perfil_id
                    JOIN perfis_acesso_contexto pc ON pc.nome = pa.nome
                    ON CONFLICT (perfil_ctx_id, recurso_id) DO NOTHING
                    """
                )

            # Migração: perfis de usuário por contexto
            cursor.execute("SELECT usuario, perfil_acesso FROM perfil_usuario")
            users = cursor.fetchall() or []
            for user in users:
                user_email = user["usuario"] if isinstance(user, dict) else user[0]
                role = user["perfil_acesso"] if isinstance(user, dict) else user[1]
                if not user_email or not role:
                    continue
                for ctx in VALID_CONTEXTS:
                    if db_type == "sqlite":
                        cursor.execute(
                            """
                            INSERT INTO perfil_usuario_contexto
                            (usuario, contexto, perfil_acesso, atualizado_em, atualizado_por)
                            VALUES (?, ?, ?, CURRENT_TIMESTAMP, 'migration')
                            ON CONFLICT (usuario, contexto)
                            DO UPDATE SET
                                perfil_acesso = excluded.perfil_acesso,
                                atualizado_em = CURRENT_TIMESTAMP,
                                atualizado_por = excluded.atualizado_por
                            """,
                            (user_email, ctx, role),
                        )
                    else:
                        cursor.execute(
                            """
                            INSERT INTO perfil_usuario_contexto
                            (usuario, contexto, perfil_acesso, atualizado_em, atualizado_por)
                            VALUES (%s, %s, %s, CURRENT_TIMESTAMP, 'migration')
                            ON CONFLICT (usuario, contexto)
                            DO UPDATE SET
                                perfil_acesso = EXCLUDED.perfil_acesso,
                                atualizado_em = CURRENT_TIMESTAMP,
                                atualizado_por = EXCLUDED.atualizado_por
                            """,
                            (user_email, ctx, role),
                        )
            conn.commit()
    except Exception as exc:
        if conn:
            conn.rollback()
        current_app.logger.warning(f"Falha ao garantir schema contextual de perfis: {exc}")


def _upsert_user_context_profile(user_email, contexto, perfil_acesso, updated_by="system"):
    now = datetime.now()
    execute_db(
        """
        INSERT INTO perfil_usuario_contexto (usuario, contexto, perfil_acesso, atualizado_em, atualizado_por)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (usuario, contexto)
        DO UPDATE SET
            perfil_acesso = EXCLUDED.perfil_acesso,
            atualizado_em = EXCLUDED.atualizado_em,
            atualizado_por = EXCLUDED.atualizado_por
        """,
        (user_email, contexto, perfil_acesso, now, updated_by),
    )


def set_user_role_for_context(user_email, role, context=None, updated_by="system"):
    ctx = resolve_context(context)
    _upsert_user_context_profile(user_email, ctx, role, updated_by=updated_by)


def set_user_role_for_all_contexts(user_email, role, updated_by="system"):
    for ctx in VALID_CONTEXTS:
        _upsert_user_context_profile(user_email, ctx, role, updated_by=updated_by)


def ensure_user_context_profiles(user_email, role, updated_by="system"):
    for ctx in VALID_CONTEXTS:
        execute_db(
            """
            INSERT INTO perfil_usuario_contexto (usuario, contexto, perfil_acesso, atualizado_em, atualizado_por)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (usuario, contexto) DO NOTHING
            """,
            (user_email, ctx, role, datetime.now(), updated_by),
        )


def get_contextual_profile(user_email, context=None):
    ctx = resolve_context(context)
    row = query_db(
        """
        SELECT
            pu.usuario,
            pu.nome,
            pu.foto_url,
            pu.cargo,
            puc.perfil_acesso AS perfil_contextual,
            COALESCE(puc.perfil_acesso, pu.perfil_acesso) AS perfil_acesso
        FROM perfil_usuario pu
        LEFT JOIN perfil_usuario_contexto puc
            ON puc.usuario = pu.usuario AND puc.contexto = %s
        WHERE pu.usuario = %s
        """,
        (ctx, user_email),
        one=True,
    )
    if not row:
        return None

    # Auto-heal: cria linha contextual quando vier apenas do legado.
    if row.get("perfil_acesso") and not row.get("perfil_contextual"):
        _upsert_user_context_profile(
            user_email=user_email,
            contexto=ctx,
            perfil_acesso=row.get("perfil_acesso"),
            updated_by="autoheal",
        )

    row.pop("perfil_contextual", None)
    row["contexto"] = ctx
    return row
