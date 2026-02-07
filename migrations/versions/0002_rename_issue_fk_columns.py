"""Rename issue foreign key columns to match PDF naming.

Revision ID: 0002_rename_issue_fk_columns
Revises: 0001_init
Create Date: 2026-02-05
"""

from alembic import op
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = "0002_rename_issue_fk_columns"
down_revision = "0001_init"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    cols = {col["name"] for col in inspect(conn).get_columns("issues")}
    if "project_id" in cols and "project" not in cols:
        op.alter_column("issues", "project_id", new_column_name="project")
    if "reporter_id" in cols and "reporter" not in cols:
        op.alter_column("issues", "reporter_id", new_column_name="reporter")
    if "assignee_id" in cols and "assignee" not in cols:
        op.alter_column("issues", "assignee_id", new_column_name="assignee")


def downgrade():
    conn = op.get_bind()
    cols = {col["name"] for col in inspect(conn).get_columns("issues")}
    if "project" in cols and "project_id" not in cols:
        op.alter_column("issues", "project", new_column_name="project_id")
    if "reporter" in cols and "reporter_id" not in cols:
        op.alter_column("issues", "reporter", new_column_name="reporter_id")
    if "assignee" in cols and "assignee_id" not in cols:
        op.alter_column("issues", "assignee", new_column_name="assignee_id")
