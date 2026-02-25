"""add Visita and Live tags to tags_sistema

Revision ID: 010
Revises: 009
Create Date: 2026-02-25
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None


def _insert_if_missing(nome: str, ordem: int, tipo: str) -> None:
    op.execute(
        f"""
        INSERT INTO tags_sistema (nome, ordem, tipo, ativo)
        SELECT '{nome}', {ordem}, '{tipo}', 1
        WHERE NOT EXISTS (
            SELECT 1 FROM tags_sistema WHERE nome = '{nome}'
        )
        """
    )
    # Se já existir, garante que permaneça ativa
    op.execute(f"UPDATE tags_sistema SET ativo = 1 WHERE nome = '{nome}'")


def upgrade():
    _insert_if_missing("Visita", 7, "comentario")
    _insert_if_missing("Live", 8, "comentario")


def downgrade():
    op.execute("DELETE FROM tags_sistema WHERE nome IN ('Visita', 'Live')")
