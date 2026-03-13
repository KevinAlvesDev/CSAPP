"""Tabela de participantes da gamificação por contexto.

Revision ID: 003
Revises: 002
Create Date: 2026-03-13
"""

from alembic import op
from sqlalchemy import text

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS gamificacao_participantes (
                id         SERIAL PRIMARY KEY,
                usuario_cs TEXT NOT NULL,
                contexto   TEXT NOT NULL DEFAULT 'onboarding',
                ativo      BOOLEAN NOT NULL DEFAULT TRUE,
                criado_em  TIMESTAMP DEFAULT NOW(),
                CONSTRAINT uq_gamificacao_participantes UNIQUE (usuario_cs, contexto)
            );
            """
        )
    )


def downgrade() -> None:
    op.execute(text("DROP TABLE IF EXISTS gamificacao_participantes CASCADE;"))
