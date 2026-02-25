"""drop icone column from tags_sistema

Revision ID: 012
Revises: 011
Create Date: 2026-02-25
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "012"
down_revision = "011"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col["name"] for col in inspector.get_columns("tags_sistema")]
    if "icone" in columns:
        with op.batch_alter_table("tags_sistema") as batch_op:
            batch_op.drop_column("icone")


def downgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col["name"] for col in inspector.get_columns("tags_sistema")]
    if "icone" not in columns:
        with op.batch_alter_table("tags_sistema") as batch_op:
            batch_op.add_column(sa.Column("icone", sa.String(length=50), nullable=True))
