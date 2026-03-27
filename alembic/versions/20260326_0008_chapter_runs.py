"""Add ChapterRun runtime resource table.

Revision ID: 20260326_0008
Revises: 20260321_0007
Create Date: 2026-03-26 22:41:02
"""

from alembic import op


revision = "20260326_0008"
down_revision = "20260321_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE chapter_runs (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            run_id UUID NOT NULL REFERENCES document_runs(id) ON DELETE CASCADE,
            document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
            chapter_id UUID NOT NULL REFERENCES chapters(id) ON DELETE CASCADE,
            desired_phase TEXT NOT NULL CHECK (desired_phase IN (
                'packetize', 'translate', 'review', 'export', 'complete'
            )),
            observed_phase TEXT NOT NULL CHECK (observed_phase IN (
                'packetize', 'translate', 'review', 'export', 'complete'
            )),
            status TEXT NOT NULL CHECK (status IN (
                'active', 'paused', 'succeeded', 'failed', 'cancelled'
            )),
            generation INTEGER NOT NULL DEFAULT 1,
            observed_generation INTEGER NOT NULL DEFAULT 1,
            conditions_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            status_detail_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            pause_reason TEXT,
            last_reconciled_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_chapter_runs_run_chapter UNIQUE (run_id, chapter_id)
        );
        """
    )
    op.execute("CREATE INDEX idx_chapter_runs_run_status ON chapter_runs(run_id, status);")
    op.execute("CREATE INDEX idx_chapter_runs_document ON chapter_runs(document_id, chapter_id);")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_chapter_runs_document;")
    op.execute("DROP INDEX IF EXISTS idx_chapter_runs_run_status;")
    op.execute("DROP TABLE IF EXISTS chapter_runs;")

