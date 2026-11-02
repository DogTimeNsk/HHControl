"""store detailed vacancy-search state

Revision ID: 0006_vacancy_match_details
Revises: 0005_vacancy_monitoring
"""
from alembic import op
import sqlalchemy as sa


revision = "0006_vacancy_match_details"
down_revision = "0005_vacancy_monitoring"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("vacancy_matches", sa.Column("salary_gross", sa.Boolean(), nullable=True))
    op.add_column("vacancy_matches", sa.Column("responses_count", sa.Integer(), nullable=True))
    op.add_column("vacancy_matches", sa.Column("total_responses_count", sa.Integer(), nullable=True))
    op.add_column("vacancy_matches", sa.Column("online_users_count", sa.Integer(), nullable=True))
    op.add_column("vacancy_matches", sa.Column("user_test_present", sa.Boolean(), nullable=True))
    op.add_column("vacancy_matches", sa.Column("user_test_id", sa.String(64), nullable=True))
    op.add_column("vacancy_matches", sa.Column("accept_temporary", sa.Boolean(), nullable=True))
    op.add_column("vacancy_matches", sa.Column("work_formats", sa.JSON(), nullable=True))
    op.add_column("vacancy_matches", sa.Column("company_negative_attributes", sa.JSON(), nullable=True))
    op.add_column("vacancy_matches", sa.Column("vacancy_properties", sa.JSON(), nullable=True))
    op.add_column("vacancy_matches", sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True))
    op.execute("UPDATE vacancy_matches SET last_seen_at = parsed_at")
    op.execute("UPDATE vacancy_matches SET work_formats = '[]', vacancy_properties = '[]'")


def downgrade() -> None:
    for column in ("last_seen_at", "vacancy_properties", "company_negative_attributes", "work_formats",
                   "accept_temporary", "user_test_id", "user_test_present", "online_users_count",
                   "total_responses_count", "responses_count", "salary_gross"):
        op.drop_column("vacancy_matches", column)
