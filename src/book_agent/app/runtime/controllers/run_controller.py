from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from book_agent.domain.models import Chapter
from book_agent.domain.models.ops import DocumentRun
from book_agent.infra.repositories.runtime_resources import RuntimeResourcesRepository


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
