"""drop cor_badge column from tags_sistema

Revision ID: 011
Revises: 010
Create Date: 2026-02-25
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "011"
down_revision = "010"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col["name"] for col in inspector.get_columns("tags_sistema")]
    if "cor_badge" in columns:
        with op.batch_alter_table("tags_sistema") as batch_op:
            batch_op.drop_column("cor_badge")


def downgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col["name"] for col in inspector.get_columns("tags_sistema")]
    if "cor_badge" not in columns:
        with op.batch_alter_table("tags_sistema") as batch_op:
            batch_op.add_column(sa.Column("cor_badge", sa.String(length=30), nullable=True))
