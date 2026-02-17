"""add data_parada column to implantacoes

Revision ID: 009
Revises: 008
Create Date: 2026-02-17
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade():
    """Cria coluna dedicada à data de início da parada e faz backfill."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col["name"] for col in inspector.get_columns("implantacoes")]

    if "data_parada" not in columns:
        op.add_column("implantacoes", sa.Column("data_parada", sa.DateTime(), nullable=True))

    # Índice para filtros por data de parada
    with op.batch_alter_table("implantacoes") as batch_op:
        try:
            batch_op.create_index("idx_implantacoes_data_parada", ["data_parada"])
        except Exception:
            pass

    # Backfill: aproveita registros onde data_finalizacao marcou início da parada
    try:
        op.execute(
            """
            UPDATE implantacoes
               SET data_parada = data_finalizacao
             WHERE data_parada IS NULL
               AND data_finalizacao IS NOT NULL
               AND status = 'parada'
            """
        )
    except Exception:
        pass


def downgrade():
    with op.batch_alter_table("implantacoes") as batch_op:
        try:
            batch_op.drop_index("idx_implantacoes_data_parada")
        except Exception:
            pass
        batch_op.drop_column("data_parada")
