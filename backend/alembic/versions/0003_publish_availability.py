"""store the last observed manual publication availability

Revision ID: 0003_publish_availability
Revises: 0002_browser_credentials
"""
from alembic import op
import sqlalchemy as sa


revision = "0003_publish_availability"
down_revision = "0002_browser_credentials"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("resumes", sa.Column("publish_available", sa.Boolean(), nullable=True))


def downgrade() -> None:
    op.drop_column("resumes", "publish_available")
