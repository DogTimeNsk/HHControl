"""make vacancy matches unique per resume

Revision ID: 0008_vacancy_match_per_resume
Revises: 0007_resume_vacancy_response_limit
"""
from alembic import op
import sqlalchemy as sa


revision = "0008_vacancy_match_per_resume"
down_revision = "0007_resume_vacancy_response_limit"
branch_labels = None
depends_on = None


_COLUMNS = (
    "id, resume_id, hh_vacancy_id, title, vacancy_url, employer_name, employer_url, "
    "salary_from, salary_to, salary_currency, salary_gross, city, responses_count, "
    "total_responses_count, online_users_count, user_test_present, user_test_id, "
    "accept_temporary, work_formats, company_negative_attributes, vacancy_properties, "
    "parsed_at, last_seen_at"
)


def _create_replacement_table(table_name: str, *, global_vacancy_id: bool) -> None:
    unique_columns = ("hh_vacancy_id",) if global_vacancy_id else ("resume_id", "hh_vacancy_id")
    op.create_table(
        table_name,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("resume_id", sa.Integer(), sa.ForeignKey("resumes.id"), nullable=False),
        sa.Column("hh_vacancy_id", sa.String(32), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("vacancy_url", sa.String(1000), nullable=False),
        sa.Column("employer_name", sa.String(500), nullable=True),
        sa.Column("employer_url", sa.String(1000), nullable=True),
        sa.Column("salary_from", sa.Integer(), nullable=True),
        sa.Column("salary_to", sa.Integer(), nullable=True),
        sa.Column("salary_currency", sa.String(8), nullable=True),
        sa.Column("salary_gross", sa.Boolean(), nullable=True),
        sa.Column("city", sa.String(255), nullable=True),
        sa.Column("responses_count", sa.Integer(), nullable=True),
        sa.Column("total_responses_count", sa.Integer(), nullable=True),
        sa.Column("online_users_count", sa.Integer(), nullable=True),
        sa.Column("user_test_present", sa.Boolean(), nullable=True),
        sa.Column("user_test_id", sa.String(64), nullable=True),
        sa.Column("accept_temporary", sa.Boolean(), nullable=True),
        sa.Column("work_formats", sa.JSON(), nullable=True),
        sa.Column("company_negative_attributes", sa.JSON(), nullable=True),
        sa.Column("vacancy_properties", sa.JSON(), nullable=True),
        sa.Column("parsed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint(*unique_columns, name="uq_vacancy_matches_resume_hh" if not global_vacancy_id else "uq_vacancy_matches_hh"),
    )


def _rebuild(*, global_vacancy_id: bool) -> None:
    replacement = "vacancy_matches_replacement"
    _create_replacement_table(replacement, global_vacancy_id=global_vacancy_id)
    op.execute(sa.text(f"INSERT INTO {replacement} ({_COLUMNS}) SELECT {_COLUMNS} FROM vacancy_matches"))
    op.drop_table("vacancy_matches")
    op.rename_table(replacement, "vacancy_matches")
    op.create_index("ix_vacancy_matches_resume_id", "vacancy_matches", ["resume_id"])
    op.create_index("ix_vacancy_matches_hh_vacancy_id", "vacancy_matches", ["hh_vacancy_id"])
    op.create_index("ix_vacancy_matches_parsed_at", "vacancy_matches", ["parsed_at"])
    op.create_index("ix_vacancy_matches_last_seen_at", "vacancy_matches", ["last_seen_at"])


def upgrade() -> None:
    _rebuild(global_vacancy_id=False)


def downgrade() -> None:
    duplicate = op.get_bind().execute(sa.text(
        "SELECT 1 FROM vacancy_matches GROUP BY hh_vacancy_id HAVING COUNT(*) > 1 LIMIT 1"
    )).scalar()
    if duplicate:
        raise RuntimeError("Нельзя откатить миграцию: одна вакансия уже привязана к нескольким резюме")
    _rebuild(global_vacancy_id=True)
