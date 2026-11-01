"""initial schema

Revision ID: 0001_initial
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("admin_users", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("username", sa.String(100), nullable=False, unique=True), sa.Column("password_hash", sa.String(255), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_table("resumes", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("hh_resume_id", sa.String(64), nullable=False, unique=True), sa.Column("title", sa.String(500), nullable=False), sa.Column("enabled", sa.Boolean(), nullable=False), sa.Column("managed", sa.Boolean(), nullable=False), sa.Column("status", sa.String(100)), sa.Column("published_at", sa.DateTime(timezone=True)), sa.Column("next_publish_at", sa.DateTime(timezone=True)), sa.Column("last_checked_at", sa.DateTime(timezone=True)), sa.Column("last_publish_attempt_at", sa.DateTime(timezone=True)), sa.Column("last_success_at", sa.DateTime(timezone=True)), sa.Column("last_error", sa.Text()), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_resumes_hh_resume_id", "resumes", ["hh_resume_id"])
    op.create_table("publish_events", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("resume_id", sa.Integer(), sa.ForeignKey("resumes.id"), nullable=False), sa.Column("started_at", sa.DateTime(timezone=True), nullable=False), sa.Column("finished_at", sa.DateTime(timezone=True)), sa.Column("operation", sa.String(32), nullable=False), sa.Column("result", sa.String(16), nullable=False), sa.Column("http_status", sa.Integer()), sa.Column("message", sa.Text(), nullable=False))
    op.create_index("ix_publish_events_resume_id", "publish_events", ["resume_id"])
    op.create_table("app_settings", sa.Column("key", sa.String(100), primary_key=True), sa.Column("value", sa.Text(), nullable=False))
    op.create_table("oauth_credentials", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("access_token_encrypted", sa.Text(), nullable=False), sa.Column("refresh_token_encrypted", sa.Text()), sa.Column("expires_at", sa.DateTime(timezone=True)), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False))
    op.create_table("oauth_states", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("state", sa.String(128), nullable=False, unique=True), sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False))


def downgrade() -> None:
    op.drop_table("oauth_states"); op.drop_table("oauth_credentials"); op.drop_table("app_settings"); op.drop_index("ix_publish_events_resume_id", "publish_events"); op.drop_table("publish_events"); op.drop_index("ix_resumes_hh_resume_id", "resumes"); op.drop_table("resumes"); op.drop_table("admin_users")
