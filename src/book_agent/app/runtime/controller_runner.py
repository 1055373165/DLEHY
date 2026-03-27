from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import sessionmaker


@dataclass(slots=True)
class ControllerRunner:
    """Best-effort controller reconcile scaffold for Phase A startup wiring.

    The runner is intentionally conservative here: it exists so the runtime can
    import and call a controller surface without changing V1 execution behavior
    before the controller plane is fully controllerized.
    """

    session_factory: sessionmaker

    def reconcile_run(self, *, run_id: str) -> None:
        """Reconcile a single run in mirror-only mode.

        Phase A startup integration keeps this as a no-op scaffold so the master
        loop can exercise the wiring path without widening execution scope.
        """

        _ = run_id
        return None
