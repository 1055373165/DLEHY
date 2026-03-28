# ruff: noqa: E402

import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

from sqlalchemy import select

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
os.environ.setdefault("BOOK_AGENT_TRANSLATION_BACKEND", "echo")
os.environ.setdefault("BOOK_AGENT_TRANSLATION_MODEL", "echo-worker")
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from book_agent.domain.models.ops import DocumentRun
from book_agent.infra.db.session import build_engine, build_session_factory
from book_agent.infra.db.sqlite_schema_backfill import ensure_sqlite_schema_compat


class SQLiteSchemaBackfillTests(unittest.TestCase):
    def test_backfill_adds_runtime_bundle_revision_columns(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "legacy-runtime-runtime-bundle.sqlite"
            with sqlite3.connect(db_path) as connection:
                connection.execute(
                    """
                    CREATE TABLE documents (
                        id TEXT PRIMARY KEY,
                        title TEXT,
                        title_src TEXT,
                        title_tgt TEXT
                    )
                    """
                )
                connection.execute(
                    """
                    CREATE TABLE document_runs (
                        document_id TEXT,
                        run_type TEXT,
                        status TEXT,
                        backend TEXT,
                        model_name TEXT,
                        requested_by TEXT,
                        priority INTEGER,
                        resume_from_run_id TEXT,
                        stop_reason TEXT,
                        status_detail_json TEXT,
                        started_at TEXT,
                        finished_at TEXT,
                        id TEXT PRIMARY KEY,
                        updated_at TEXT,
                        created_at TEXT
                    )
                    """
                )
                connection.execute(
                    """
                    CREATE TABLE work_items (
                        run_id TEXT,
                        stage TEXT,
                        scope_type TEXT,
                        scope_id TEXT,
                        attempt INTEGER,
                        priority INTEGER,
                        status TEXT,
                        lease_owner TEXT,
                        lease_expires_at TEXT,
                        last_heartbeat_at TEXT,
                        started_at TEXT,
                        finished_at TEXT,
                        input_version_bundle_json TEXT,
                        output_artifact_refs_json TEXT,
                        error_class TEXT,
                        error_detail_json TEXT,
                        id TEXT PRIMARY KEY,
                        updated_at TEXT,
                        created_at TEXT
                    )
                    """
                )
                connection.execute(
                    """
                    CREATE TABLE run_budgets (
                        run_id TEXT,
                        max_wall_clock_seconds INTEGER,
                        max_total_cost_usd REAL,
                        max_total_token_in INTEGER,
                        max_total_token_out INTEGER,
                        max_retry_count_per_work_item INTEGER,
                        max_consecutive_failures INTEGER,
                        max_parallel_workers INTEGER,
                        max_parallel_requests_per_provider INTEGER,
                        max_auto_followup_attempts INTEGER,
                        id TEXT PRIMARY KEY,
                        updated_at TEXT,
                        created_at TEXT
                    )
                    """
                )
                connection.commit()

            added_column_count = ensure_sqlite_schema_compat(f"sqlite+pysqlite:///{db_path}")

            self.assertEqual(added_column_count, 3)
            with sqlite3.connect(db_path) as connection:
                document_run_columns = [str(row[1]) for row in connection.execute("PRAGMA table_info('document_runs')")]
                work_item_columns = [str(row[1]) for row in connection.execute("PRAGMA table_info('work_items')")]
                run_budget_columns = [str(row[1]) for row in connection.execute("PRAGMA table_info('run_budgets')")]
            self.assertIn("runtime_bundle_revision_id", document_run_columns)
            self.assertIn("runtime_bundle_revision_id", work_item_columns)
            self.assertIn("runtime_bundle_revision_id", run_budget_columns)

            engine = build_engine(database_url=f"sqlite+pysqlite:///{db_path}")
            session_factory = build_session_factory(engine=engine)
            with session_factory() as session:
                self.assertEqual(session.scalars(select(DocumentRun)).all(), [])
