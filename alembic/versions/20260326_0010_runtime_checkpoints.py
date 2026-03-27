"""Add runtime_checkpoints table.

Revision ID: 20260326_0010
Revises: 20260326_0009
Create Date: 2026-03-26 22:51:38
"""

from alembic import op


revision = "20260326_0010"
down_revision = "20260326_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE runtime_checkpoints (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            run_id UUID NOT NULL REFERENCES document_runs(id) ON DELETE CASCADE,
            scope_type TEXT NOT NULL CHECK (scope_type IN ('document', 'chapter', 'packet', 'sentence')),
            scope_id UUID NOT NULL,
            checkpoint_key TEXT NOT NULL,
            generation INTEGER NOT NULL DEFAULT 1,
            checkpoint_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_runtime_checkpoints_scope_key UNIQUE (run_id, scope_type, scope_id, checkpoint_key)
        );
        """
    )
    op.execute(
        "CREATE INDEX idx_runtime_checkpoints_run_scope "
        "ON runtime_checkpoints(run_id, scope_type, scope_id);"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_runtime_checkpoints_run_scope;")
    op.execute("DROP TABLE IF EXISTS runtime_checkpoints;")

