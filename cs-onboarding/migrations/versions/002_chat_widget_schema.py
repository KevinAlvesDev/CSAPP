"""Chat widget schema and RBAC resources.

Revision ID: 002
Revises: 001
Create Date: 2026-03-13
"""

from alembic import op
from sqlalchemy import text

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def _create_index(indexname: str, tablename: str, columns: str) -> None:
    op.execute(
        text(
            f"""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_indexes WHERE indexname = '{indexname}'
                ) THEN
                    CREATE INDEX {indexname} ON {tablename}({columns});
                END IF;
            END
            $$;
            """
        )
    )


def upgrade() -> None:
    op.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS chat_conversations (
                id         SERIAL PRIMARY KEY,
                contexto   TEXT NOT NULL,
                kind       TEXT NOT NULL DEFAULT 'direct',
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            );
            """
        )
    )

    op.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS chat_participants (
                id              SERIAL PRIMARY KEY,
                conversation_id INT NOT NULL REFERENCES chat_conversations(id) ON DELETE CASCADE,
                user_email      TEXT NOT NULL,
                unread_count    INT NOT NULL DEFAULT 0,
                last_read_at    TIMESTAMP,
                created_at      TIMESTAMP DEFAULT NOW(),
                CONSTRAINT uq_chat_participants_conv_user UNIQUE (conversation_id, user_email)
            );
            """
        )
    )

    op.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS chat_messages (
                id              SERIAL PRIMARY KEY,
                conversation_id INT NOT NULL REFERENCES chat_conversations(id) ON DELETE CASCADE,
                sender_email    TEXT NOT NULL,
                content         TEXT NOT NULL,
                created_at      TIMESTAMP DEFAULT NOW()
            );
            """
        )
    )

    _create_index("idx_chat_conversations_contexto", "chat_conversations", "contexto")
    _create_index("idx_chat_conversations_updated_at", "chat_conversations", "updated_at")
    _create_index("idx_chat_participants_user_email", "chat_participants", "user_email")
    _create_index("idx_chat_messages_conv_created", "chat_messages", "conversation_id, created_at DESC")

    op.execute(
        text(
            """
            INSERT INTO recursos (codigo, nome, descricao, categoria, tipo, ordem)
            SELECT 'chat.view', 'Visualizar Chat', 'Acessar o chat interno', 'Comunicacao', 'pagina', 150
            WHERE NOT EXISTS (SELECT 1 FROM recursos WHERE codigo = 'chat.view');
            """
        )
    )

    op.execute(
        text(
            """
            INSERT INTO recursos (codigo, nome, descricao, categoria, tipo, ordem)
            SELECT 'chat.send', 'Enviar Mensagens no Chat', 'Enviar mensagens no chat interno', 'Comunicacao', 'acao', 151
            WHERE NOT EXISTS (SELECT 1 FROM recursos WHERE codigo = 'chat.send');
            """
        )
    )

    op.execute(
        text(
            """
            INSERT INTO permissoes_contexto (perfil_ctx_id, recurso_id, concedida, criado_em)
            SELECT pac.id, r.id, TRUE, NOW()
            FROM perfis_acesso_contexto pac
            JOIN recursos r ON r.codigo IN ('chat.view', 'chat.send')
            WHERE pac.nome IN ('Administrador', 'Gerente', 'Coordenador', 'Implantador')
              AND NOT EXISTS (
                SELECT 1 FROM permissoes_contexto pc
                WHERE pc.perfil_ctx_id = pac.id AND pc.recurso_id = r.id
              );
            """
        )
    )


def downgrade() -> None:
    op.execute(text("DELETE FROM permissoes_contexto WHERE recurso_id IN (SELECT id FROM recursos WHERE codigo IN ('chat.view', 'chat.send'));"))
    op.execute(text("DELETE FROM recursos WHERE codigo IN ('chat.view', 'chat.send');"))
    op.execute(text("DROP TABLE IF EXISTS chat_messages CASCADE;"))
    op.execute(text("DROP TABLE IF EXISTS chat_participants CASCADE;"))
    op.execute(text("DROP TABLE IF EXISTS chat_conversations CASCADE;"))
