from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from book_agent.domain.enums import WorkItemScopeType, WorkItemStage
from book_agent.domain.models.ops import ChapterRun, PacketTask, WorkItem
from book_agent.infra.repositories.runtime_resources import RuntimeResourcesRepository


class PacketController:
    """
    Packet-scoped controller (Phase A mirror-only).

    Responsibility:
    - mirror-bind PacketTask rows to already-existing WorkItem attempts
    - do not create new work items or infer health/state yet
    """

    def __init__(self, *, session: Session):
        self._session = session
        self._runtime_repo = RuntimeResourcesRepository(session)

    def mirror_bind_work_items(self, *, run_id: str) -> int:
        packet_tasks = self._session.scalars(
            select(PacketTask)
            .join(ChapterRun, ChapterRun.id == PacketTask.chapter_run_id)
            .where(ChapterRun.run_id == run_id)
            .order_by(PacketTask.created_at.asc(), PacketTask.id.asc())
        ).all()

        updated = 0
        for task in packet_tasks:
            work_item = self._session.scalar(
                select(WorkItem)
                .where(
                    WorkItem.run_id == run_id,
                    WorkItem.stage == WorkItemStage.TRANSLATE,
                    WorkItem.scope_type == WorkItemScopeType.PACKET,
                    WorkItem.scope_id == task.packet_id,
                )
                .order_by(WorkItem.attempt.desc(), WorkItem.updated_at.desc(), WorkItem.id.desc())
            )
            if work_item is None:
                continue

            if task.last_work_item_id != work_item.id:
                task.last_work_item_id = work_item.id
                updated += 1
            task.attempt_count = max(int(task.attempt_count or 0), int(work_item.attempt or 0))
            task.last_error_class = work_item.error_class
            task.runtime_bundle_revision_id = work_item.runtime_bundle_revision_id

        self._session.flush()
        return updated
