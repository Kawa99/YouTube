"""add video label audit trail

Revision ID: c2f4c8d1e9a0
Revises: 9b7d2f4a6c31
Create Date: 2026-05-10 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "c2f4c8d1e9a0"
down_revision = "9b7d2f4a6c31"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("video_labels") as batch_op:
        batch_op.add_column(sa.Column("label_confidence", sa.Float()))

    op.create_table(
        "video_label_audits",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("video_label_id", sa.Integer()),
        sa.Column("video_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("reviewer", sa.String()),
        sa.Column("previous_values", sa.JSON(), nullable=False),
        sa.Column("new_values", sa.JSON(), nullable=False),
        sa.Column("label_confidence", sa.Float()),
        sa.Column("changed_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["video_id"], ["videos.id"]),
        sa.ForeignKeyConstraint(["video_label_id"], ["video_labels.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade():
    op.drop_table("video_label_audits")
    with op.batch_alter_table("video_labels") as batch_op:
        batch_op.drop_column("label_confidence")
