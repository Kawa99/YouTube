"""add asset rights compliance

Revision ID: 2c3d4e5f6071
Revises: 1b2c3d4e5f60
Create Date: 2026-05-10 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "2c3d4e5f6071"
down_revision = "1b2c3d4e5f60"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "assets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("asset_id", sa.String(), nullable=False),
        sa.Column("asset_type", sa.String(), nullable=False),
        sa.Column("source_url_path", sa.String(), nullable=False),
        sa.Column("creator_licensor", sa.String()),
        sa.Column("license_terms", sa.Text()),
        sa.Column("monetized_youtube_allowed", sa.String(), nullable=False),
        sa.Column("attribution_required", sa.Boolean(), nullable=False),
        sa.Column("proof_saved", sa.Boolean(), nullable=False),
        sa.Column("high_risk_flag", sa.Boolean(), nullable=False),
        sa.Column("high_risk_reason", sa.String()),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("asset_id"),
    )
    op.create_index(op.f("ix_assets_asset_id"), "assets", ["asset_id"], unique=False)

    op.create_table(
        "video_assets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("video_id", sa.Integer(), nullable=False),
        sa.Column("asset_id", sa.Integer(), nullable=False),
        sa.Column("intended_use", sa.Text()),
        sa.Column("attribution_text", sa.Text()),
        sa.Column("rights_decision", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"]),
        sa.ForeignKeyConstraint(["video_id"], ["videos.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "video_rights_checklists",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("video_id", sa.Integer(), nullable=False),
        sa.Column("every_asset_has_row", sa.Boolean(), nullable=False),
        sa.Column("unclear_assets_blocked", sa.Boolean(), nullable=False),
        sa.Column("attribution_captured", sa.Boolean(), nullable=False),
        sa.Column("synthetic_altered_status", sa.String(), nullable=False),
        sa.Column("no_terms_prohibit_monetization", sa.Boolean(), nullable=False),
        sa.Column("ready_for_upload", sa.Boolean(), nullable=False),
        sa.Column("reviewer", sa.String()),
        sa.Column("reviewed_at", sa.DateTime(), nullable=False),
        sa.Column("notes", sa.Text()),
        sa.ForeignKeyConstraint(["video_id"], ["videos.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "video_disclosures",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("video_id", sa.Integer(), nullable=False),
        sa.Column("sponsor_disclosure", sa.Text()),
        sa.Column("affiliate_disclosure", sa.Text()),
        sa.Column("altered_synthetic_disclosure", sa.Text()),
        sa.Column("music_license_attribution", sa.Text()),
        sa.Column("disclosure_notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["video_id"], ["videos.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade():
    op.drop_table("video_disclosures")
    op.drop_table("video_rights_checklists")
    op.drop_table("video_assets")
    op.drop_index(op.f("ix_assets_asset_id"), table_name="assets")
    op.drop_table("assets")
