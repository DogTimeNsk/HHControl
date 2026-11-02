"""store the observed employer-view achievements marker

Revision ID: 0004_ats_achievements
Revises: 0003_publish_availability
"""
from alembic import op
import sqlalchemy as sa


revision = "0004_ats_achievements"
down_revision = "0003_publish_availability"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("resumes", sa.Column("ats_achievements", sa.Boolean(), nullable=True))
    op.add_column("resumes", sa.Column("ats_checked_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("resumes", "ats_checked_at")
    op.drop_column("resumes", "ats_achievements")
