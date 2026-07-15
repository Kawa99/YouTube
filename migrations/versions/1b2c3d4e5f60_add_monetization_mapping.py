"""add monetization mapping

Revision ID: 1b2c3d4e5f60
Revises: 0a1b2c3d4e5f
Create Date: 2026-05-10 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "1b2c3d4e5f60"
down_revision = "0a1b2c3d4e5f"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "thesis_monetization_maps",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("thesis_id", sa.Integer(), nullable=False),
        sa.Column("revenue_paths", sa.JSON(), nullable=False),
        sa.Column("primary_revenue_path", sa.String()),
        sa.Column("secondary_revenue_path", sa.String()),
        sa.Column("conservative_ad_rpm", sa.Float()),
        sa.Column("base_ad_rpm", sa.Float()),
        sa.Column("upside_ad_rpm", sa.Float()),
        sa.Column("sponsor_rpm_equivalent", sa.Float()),
        sa.Column("affiliate_rpm_equivalent", sa.Float()),
        sa.Column("membership_rpm_equivalent", sa.Float()),
        sa.Column("product_rpm_equivalent", sa.Float()),
        sa.Column("break_even_view_count", sa.Integer()),
        sa.Column("meaningful_income_view_count", sa.Integer()),
        sa.Column("assumptions", sa.Text()),
        sa.Column("main_monetization_risk", sa.Text()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["thesis_id"], ["content_theses.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "sponsor_evidence",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("thesis_id", sa.Integer(), nullable=False),
        sa.Column("sponsor_category", sa.String(), nullable=False),
        sa.Column("observed_sponsor", sa.String()),
        sa.Column("competitor_channel_id", sa.Integer()),
        sa.Column("video_url", sa.String()),
        sa.Column("date_observed", sa.DateTime()),
        sa.Column("niche_fit", sa.String()),
        sa.Column("brand_safety_notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["competitor_channel_id"], ["channels.id"]),
        sa.ForeignKeyConstraint(["thesis_id"], ["content_theses.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "affiliate_product_evidence",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("thesis_id", sa.Integer(), nullable=False),
        sa.Column("product_category", sa.String(), nullable=False),
        sa.Column("program_source", sa.String()),
        sa.Column("estimated_fit", sa.String()),
        sa.Column("audience_intent", sa.String()),
        sa.Column("compliance_disclosure_concerns", sa.Text()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["thesis_id"], ["content_theses.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade():
    op.drop_table("affiliate_product_evidence")
    op.drop_table("sponsor_evidence")
    op.drop_table("thesis_monetization_maps")
