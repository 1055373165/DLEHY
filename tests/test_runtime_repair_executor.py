import unittest

from book_agent.infra.db.base import Base
from book_agent.infra.db.session import build_engine, build_session_factory
from book_agent.services.runtime_repair_agent_adapter import ReviewDeadlockRepairAgentAdapter
from book_agent.services.runtime_repair_executor import (
    AgentBackedSubprocessRuntimeRepairExecutor,
    InProcessRuntimeRepairExecutor,
    RuntimeRepairExecutorRegistry,
    UnsupportedRuntimeRepairExecutorError,
)


class RuntimeRepairExecutorRegistryTests(unittest.TestCase):
    def setUp(self) -> None:
        engine = build_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(engine)
        self.session_factory = build_session_factory(engine=engine)
        self.repair_agent = ReviewDeadlockRepairAgentAdapter(session_factory=self.session_factory)

    def test_resolves_in_process_executor_for_bundle(self) -> None:
        registry = RuntimeRepairExecutorRegistry(session_factory=self.session_factory)

        executor = registry.resolve_for_input_bundle(
            input_bundle={
                "execution_mode": "in_process",
                "executor_hint": "python_repair_executor",
                "executor_contract_version": 1,
            },
            repair_agent=self.repair_agent,
        )

        self.assertIsInstance(executor, InProcessRuntimeRepairExecutor)
        self.assertEqual(executor.descriptor().execution_mode, "in_process")
        self.assertEqual(executor.descriptor().executor_hint, "python_repair_executor")

    def test_resolves_agent_backed_subprocess_executor_for_bundle(self) -> None:
        registry = RuntimeRepairExecutorRegistry(session_factory=self.session_factory)

        executor = registry.resolve_for_input_bundle(
            input_bundle={
                "execution_mode": "agent_backed",
                "executor_hint": "python_subprocess_repair_executor",
                "executor_contract_version": 1,
            },
            repair_agent=self.repair_agent,
        )

        self.assertIsInstance(executor, AgentBackedSubprocessRuntimeRepairExecutor)
        self.assertEqual(executor.descriptor().execution_mode, "agent_backed")
        self.assertEqual(executor.descriptor().executor_hint, "python_subprocess_repair_executor")

    def test_rejects_unknown_executor_hint(self) -> None:
        registry = RuntimeRepairExecutorRegistry(session_factory=self.session_factory)

        with self.assertRaises(UnsupportedRuntimeRepairExecutorError) as exc_info:
            registry.resolve_for_input_bundle(
                input_bundle={
                    "execution_mode": "in_process",
                    "executor_hint": "unknown_repair_executor",
                    "executor_contract_version": 1,
                },
                repair_agent=self.repair_agent,
            )

        self.assertIn("Unknown repair executor hint", str(exc_info.exception))
        self.assertIn("python_repair_executor", str(exc_info.exception))

    def test_rejects_unsupported_executor_contract_version(self) -> None:
        registry = RuntimeRepairExecutorRegistry(session_factory=self.session_factory)

        with self.assertRaises(UnsupportedRuntimeRepairExecutorError) as exc_info:
            registry.resolve_for_input_bundle(
                input_bundle={
                    "execution_mode": "in_process",
                    "executor_hint": "python_repair_executor",
                    "executor_contract_version": 2,
                },
                repair_agent=self.repair_agent,
            )

        self.assertIn("Unsupported repair executor contract version", str(exc_info.exception))
        self.assertIn("Supported versions: 1", str(exc_info.exception))


if __name__ == "__main__":
    unittest.main()
