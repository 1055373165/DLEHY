from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from book_agent.domain.enums import JobScopeType
from book_agent.domain.models import Chapter
from book_agent.domain.models.ops import DocumentRun
from book_agent.infra.repositories.runtime_resources import RuntimeResourcesRepository


@dataclass(slots=True)
class RunHealthProjectionResult:
    updated_chapter_runs: int
    unhealthy_packet_tasks: int
    unhealthy_review_sessions: int


class RunController:
    """
    Run-scoped controller (Phase A mirror-only).

    Responsibility:
    - ensure a ChapterRun exists for each chapter under the document run
    - do not seed attempt work or infer higher-level health yet
    """

    def __init__(self, *, session: Session):
        self._session = session
        self._runtime_repo = RuntimeResourcesRepository(session)

    def ensure_chapter_runs(self, *, run_id: str) -> int:
        run = self._session.get(DocumentRun, run_id)
        if run is None:
            raise ValueError(f"DocumentRun not found: {run_id}")

        chapter_ids = list(
            self._session.scalars(select(Chapter.id).where(Chapter.document_id == run.document_id)).all()
        )
        created = 0
        for chapter_id in chapter_ids:
            existing = self._runtime_repo.get_chapter_run_by_run_and_chapter(run_id=run_id, chapter_id=chapter_id)
            if existing is not None:
                continue
            self._runtime_repo.ensure_chapter_run(run_id=run_id, document_id=run.document_id, chapter_id=chapter_id)
            created += 1
        return created

    def project_run_health(self, *, run_id: str) -> RunHealthProjectionResult:
        run = self._session.get(DocumentRun, run_id)
        if run is None:
            raise ValueError(f"DocumentRun not found: {run_id}")

        updated_chapters = 0
        unhealthy_packets = 0
        unhealthy_reviews = 0

        for chapter_run in self._runtime_repo.list_chapter_runs_for_run(run_id=run_id):
            packet_tasks = self._runtime_repo.list_packet_tasks_for_chapter_run(chapter_run_id=chapter_run.id)
            review_sessions = self._runtime_repo.list_review_sessions_for_chapter_run(chapter_run_id=chapter_run.id)
            packet_states = [
                task.conditions_json.get("lane_health", {}).get("state")
                for task in packet_tasks
                if isinstance(task.conditions_json, dict) and task.conditions_json.get("lane_health")
            ]
            review_states = [
                review.conditions_json.get("lane_health", {}).get("state")
                for review in review_sessions
                if isinstance(review.conditions_json, dict) and review.conditions_json.get("lane_health")
            ]
            chapter_unhealthy_packets = sum(
                1
                for task in packet_tasks
                if task.conditions_json.get("lane_health", {}).get("healthy") is False
            )
            chapter_unhealthy_reviews = sum(
                1
                for review in review_sessions
                if review.conditions_json.get("lane_health", {}).get("healthy") is False
            )
            unhealthy_packets += chapter_unhealthy_packets
            unhealthy_reviews += chapter_unhealthy_reviews
            self._runtime_repo.merge_chapter_run_conditions(
                chapter_run.id,
                {
                    "lane_health_summary": {
                        "packet_states": packet_states,
                        "review_states": review_states,
                        "unhealthy_packet_count": chapter_unhealthy_packets,
                        "unhealthy_review_count": chapter_unhealthy_reviews,
                    }
                },
            )
            updated_chapters += 1

        self._runtime_repo.upsert_checkpoint(
            run_id=run_id,
            scope_type=JobScopeType.DOCUMENT,
            scope_id=run.document_id,
            checkpoint_key="run_controller.phase2.health",
            checkpoint_json={
                "updated_chapter_runs": updated_chapters,
                "unhealthy_packet_tasks": unhealthy_packets,
                "unhealthy_review_sessions": unhealthy_reviews,
            },
            generation=1,
        )
        return RunHealthProjectionResult(
            updated_chapter_runs=updated_chapters,
            unhealthy_packet_tasks=unhealthy_packets,
            unhealthy_review_sessions=unhealthy_reviews,
        )
