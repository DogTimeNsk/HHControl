"""add per-resume vacancy response limit

Revision ID: 0007_resume_vacancy_response_limit
Revises: 0006_vacancy_match_details
"""
from alembic import op
import sqlalchemy as sa


revision = "0007_resume_vacancy_response_limit"
down_revision = "0006_vacancy_match_details"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "resumes",
        sa.Column("vacancy_response_limit_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "resumes",
        sa.Column("vacancy_response_limit", sa.Integer(), nullable=False, server_default="30"),
    )


def downgrade() -> None:
    op.drop_column("resumes", "vacancy_response_limit")
    op.drop_column("resumes", "vacancy_response_limit_enabled")
