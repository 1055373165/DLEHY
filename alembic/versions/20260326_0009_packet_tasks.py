"""Add PacketTask runtime resource table.

Revision ID: 20260326_0009
Revises: 20260326_0008
Create Date: 2026-03-26 22:41:02
"""

from alembic import op


revision = "20260326_0009"
down_revision = "20260326_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE packet_tasks (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            chapter_run_id UUID NOT NULL REFERENCES chapter_runs(id) ON DELETE CASCADE,
            packet_id UUID NOT NULL REFERENCES translation_packets(id) ON DELETE CASCADE,
            packet_generation INTEGER NOT NULL DEFAULT 1,
            desired_action TEXT NOT NULL CHECK (desired_action IN (
                'translate', 'retranslate'
            )),
            status TEXT NOT NULL CHECK (status IN (
                'pending', 'running', 'succeeded', 'failed', 'cancelled'
            )),
            input_version_bundle_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            context_snapshot_id UUID,
            runtime_bundle_revision_id UUID,
            attempt_count INTEGER NOT NULL DEFAULT 0,
            last_translation_run_id UUID REFERENCES translation_runs(id) ON DELETE SET NULL,
            last_work_item_id UUID REFERENCES work_items(id) ON DELETE SET NULL,
            last_error_class TEXT,
            conditions_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            status_detail_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            invalidated_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_packet_tasks_chapter_packet_generation UNIQUE (chapter_run_id, packet_id, packet_generation)
        );
        """
    )
    op.execute("CREATE INDEX idx_packet_tasks_chapter_status ON packet_tasks(chapter_run_id, status);")
    op.execute("CREATE INDEX idx_packet_tasks_packet_status ON packet_tasks(packet_id, status);")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_packet_tasks_packet_status;")
    op.execute("DROP INDEX IF EXISTS idx_packet_tasks_chapter_status;")
    op.execute("DROP TABLE IF EXISTS packet_tasks;")

