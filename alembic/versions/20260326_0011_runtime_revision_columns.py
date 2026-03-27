"""Add runtime bundle revision binding columns.

Revision ID: 20260326_0011
Revises: 20260326_0010
Create Date: 2026-03-26 22:51:38
"""

from alembic import op


revision = "20260326_0011"
down_revision = "20260326_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE document_runs ADD COLUMN IF NOT EXISTS runtime_bundle_revision_id UUID;")
    op.execute("ALTER TABLE work_items ADD COLUMN IF NOT EXISTS runtime_bundle_revision_id UUID;")
    op.execute("ALTER TABLE run_budgets ADD COLUMN IF NOT EXISTS runtime_bundle_revision_id UUID;")

    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_document_runs_runtime_bundle_revision "
        "ON document_runs(runtime_bundle_revision_id);"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_work_items_runtime_bundle_revision "
        "ON work_items(runtime_bundle_revision_id);"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_run_budgets_runtime_bundle_revision "
        "ON run_budgets(runtime_bundle_revision_id);"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_run_budgets_runtime_bundle_revision;")
    op.execute("DROP INDEX IF EXISTS idx_work_items_runtime_bundle_revision;")
    op.execute("DROP INDEX IF EXISTS idx_document_runs_runtime_bundle_revision;")

    op.execute("ALTER TABLE run_budgets DROP COLUMN IF EXISTS runtime_bundle_revision_id;")
    op.execute("ALTER TABLE work_items DROP COLUMN IF EXISTS runtime_bundle_revision_id;")
    op.execute("ALTER TABLE document_runs DROP COLUMN IF EXISTS runtime_bundle_revision_id;")

