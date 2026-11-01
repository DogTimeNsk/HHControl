"""browser session storage

Revision ID: 0002_browser_credentials
Revises: 0001_initial
"""
from alembic import op
import sqlalchemy as sa

revision = "0002_browser_credentials"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("browser_credentials", sa.Column("id", sa.Integer(), primary_key=True),
                    sa.Column("storage_state_encrypted", sa.Text(), nullable=False),
                    sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False))


def downgrade() -> None:
    op.drop_table("browser_credentials")
