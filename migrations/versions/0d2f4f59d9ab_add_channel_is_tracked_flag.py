"""add channel is_tracked flag

Revision ID: 0d2f4f59d9ab
Revises: 6ef545e0e95d
Create Date: 2026-02-26 03:30:00.000000

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0d2f4f59d9ab"
down_revision = "6ef545e0e95d"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "channels",
        sa.Column(
            "is_tracked",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    with op.batch_alter_table("channels") as batch_op:
        batch_op.alter_column("is_tracked", server_default=None)


def downgrade():
    with op.batch_alter_table("channels") as batch_op:
        batch_op.drop_column("is_tracked")
