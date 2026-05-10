"""add packaging lab schema

Revision ID: f8a9b0c1d2e3
Revises: e4f7a6c2d1b9
Create Date: 2026-05-10 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "f8a9b0c1d2e3"
down_revision = "e4f7a6c2d1b9"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("videos") as batch_op:
        batch_op.add_column(sa.Column("thumbnail_quality", sa.String()))
        batch_op.add_column(sa.Column("thumbnail_cached_path", sa.String()))
        batch_op.add_column(sa.Column("thumbnail_phash", sa.String()))

    with op.batch_alter_table("video_labels") as batch_op:
        batch_op.add_column(sa.Column("title_pattern", sa.String()))
        batch_op.add_column(sa.Column("thumbnail_pattern", sa.String()))
        batch_op.add_column(sa.Column("viewer_promise", sa.Text()))
        batch_op.add_column(sa.Column("curiosity_type", sa.String()))
        batch_op.add_column(sa.Column("clarity_score", sa.Integer()))
        batch_op.add_column(sa.Column("specificity_score", sa.Integer()))
        batch_op.add_column(sa.Column("honesty_score", sa.Integer()))
        batch_op.add_column(sa.Column("visual_readability_score", sa.Integer()))
        batch_op.add_column(sa.Column("differentiation_score", sa.Integer()))

    op.create_table(
        "packaging_experiments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("working_title", sa.String(), nullable=False),
        sa.Column("niche", sa.String()),
        sa.Column("format", sa.String()),
        sa.Column("title_candidates", sa.JSON(), nullable=False),
        sa.Column("thumbnail_concepts", sa.JSON(), nullable=False),
        sa.Column("experiment_log_url", sa.String()),
        sa.Column("final_title", sa.String()),
        sa.Column("final_thumbnail_concept", sa.Text()),
        sa.Column("final_choice_reason", sa.Text()),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade():
    op.drop_table("packaging_experiments")

    with op.batch_alter_table("video_labels") as batch_op:
        batch_op.drop_column("differentiation_score")
        batch_op.drop_column("visual_readability_score")
        batch_op.drop_column("honesty_score")
        batch_op.drop_column("specificity_score")
        batch_op.drop_column("clarity_score")
        batch_op.drop_column("curiosity_type")
        batch_op.drop_column("viewer_promise")
        batch_op.drop_column("thumbnail_pattern")
        batch_op.drop_column("title_pattern")

    with op.batch_alter_table("videos") as batch_op:
        batch_op.drop_column("thumbnail_phash")
        batch_op.drop_column("thumbnail_cached_path")
        batch_op.drop_column("thumbnail_quality")
