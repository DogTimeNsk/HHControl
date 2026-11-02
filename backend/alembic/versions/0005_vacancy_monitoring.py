"""store monitored vacancy matches

Revision ID: 0005_vacancy_monitoring
Revises: 0004_ats_achievements
"""
from alembic import op
import sqlalchemy as sa


revision = "0005_vacancy_monitoring"
down_revision = "0004_ats_achievements"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("resumes", sa.Column("vacancy_monitoring_enabled", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("resumes", sa.Column("last_vacancy_check_at", sa.DateTime(timezone=True), nullable=True))
    op.create_table(
        "vacancy_matches",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("resume_id", sa.Integer(), sa.ForeignKey("resumes.id"), nullable=False),
        sa.Column("hh_vacancy_id", sa.String(32), nullable=False, unique=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("vacancy_url", sa.String(1000), nullable=False),
        sa.Column("employer_name", sa.String(500), nullable=True),
        sa.Column("employer_url", sa.String(1000), nullable=True),
        sa.Column("salary_from", sa.Integer(), nullable=True),
        sa.Column("salary_to", sa.Integer(), nullable=True),
        sa.Column("salary_currency", sa.String(8), nullable=True),
        sa.Column("city", sa.String(255), nullable=True),
        sa.Column("parsed_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_vacancy_matches_resume_id", "vacancy_matches", ["resume_id"])
    op.create_index("ix_vacancy_matches_hh_vacancy_id", "vacancy_matches", ["hh_vacancy_id"])
    op.create_index("ix_vacancy_matches_parsed_at", "vacancy_matches", ["parsed_at"])


def downgrade() -> None:
    op.drop_table("vacancy_matches")
    op.drop_column("resumes", "last_vacancy_check_at")
    op.drop_column("resumes", "vacancy_monitoring_enabled")
