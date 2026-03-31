from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
import json
import subprocess
import sys
import tempfile
from typing import Any
from pathlib import Path

from sqlalchemy.orm import sessionmaker

from book_agent.services.run_execution import ClaimedRunWorkItem
from book_agent.services.runtime_repair_agent_adapter import RuntimeRepairAgentAdapter

RuntimeRepairExecutorFactory = Callable[[sessionmaker, RuntimeRepairAgentAdapter], "RuntimeRepairExecutor"]


@dataclass(frozen=True, slots=True)
class RuntimeRepairExecutorDescriptor:
    executor_name: str
    execution_mode: str
    executor_hint: str
    executor_contract_version: int


class UnsupportedRuntimeRepairExecutorError(RuntimeError):
    """Raised when a repair work item requests an unknown or unsupported repair executor contract."""


class RuntimeRepairExecutorInvocationError(RuntimeError):
    """Raised when a repair executor cannot successfully invoke its underlying execution backend."""


class RuntimeRepairExecutor:
    EXECUTOR_NAME = "default_in_process_repair_executor"
    EXECUTION_MODE = "in_process"
    EXECUTOR_HINT = "python_repair_executor"
    EXECUTOR_CONTRACT_VERSION = 1

    def __init__(
        self,
        *,
        session_factory: sessionmaker,
        repair_agent: RuntimeRepairAgentAdapter,
    ) -> None:
        self._session_factory = session_factory
        self._repair_agent = repair_agent

    def descriptor(self) -> RuntimeRepairExecutorDescriptor:
        return RuntimeRepairExecutorDescriptor(
            executor_name=self.EXECUTOR_NAME,
            execution_mode=self.EXECUTION_MODE,
            executor_hint=self.EXECUTOR_HINT,
            executor_contract_version=self.EXECUTOR_CONTRACT_VERSION,
        )

    def prepare_execution(
        self,
        *,
        claimed: ClaimedRunWorkItem,
        input_bundle: dict[str, Any],
    ) -> dict[str, Any]:
        payload = self._repair_agent.prepare_execution(
            claimed=claimed,
            input_bundle=input_bundle,
        )
        descriptor = self.descriptor()
        return {
            **payload,
            "repair_executor_name": descriptor.executor_name,
            "repair_executor_execution_mode": descriptor.execution_mode,
            "repair_executor_hint": descriptor.executor_hint,
            "repair_executor_contract_version": descriptor.executor_contract_version,
        }

    def complete_execution(
        self,
        *,
        run_id: str,
        payload: dict[str, Any],
        lease_token: str,
    ) -> None:
        self._repair_agent.complete_execution(
            run_id=run_id,
            payload=payload,
            lease_token=lease_token,
        )


class InProcessRuntimeRepairExecutor(RuntimeRepairExecutor):
    EXECUTOR_NAME = "python_in_process_repair_executor"
    EXECUTION_MODE = "in_process"
    EXECUTOR_HINT = "python_repair_executor"
    EXECUTOR_CONTRACT_VERSION = 1


class AgentBackedSubprocessRuntimeRepairExecutor(RuntimeRepairExecutor):
    EXECUTOR_NAME = "python_agent_backed_subprocess_repair_executor"
    EXECUTION_MODE = "agent_backed"
    EXECUTOR_HINT = "python_subprocess_repair_executor"
    EXECUTOR_CONTRACT_VERSION = 1

    def prepare_execution(
        self,
        *,
        claimed: ClaimedRunWorkItem,
        input_bundle: dict[str, Any],
    ) -> dict[str, Any]:
        database_url = self._resolve_database_url()
        runner_payload = {
            "database_url": database_url,
            "run_id": claimed.run_id,
            "lease_token": claimed.lease_token,
            "executor_descriptor": {
                "executor_name": self.EXECUTOR_NAME,
                "execution_mode": self.EXECUTION_MODE,
                "executor_hint": self.EXECUTOR_HINT,
                "executor_contract_version": self.EXECUTOR_CONTRACT_VERSION,
            },
            "claimed": {
                "run_id": claimed.run_id,
                "work_item_id": claimed.work_item_id,
                "stage": claimed.stage,
                "scope_type": claimed.scope_type,
                "scope_id": claimed.scope_id,
                "attempt": claimed.attempt,
                "priority": claimed.priority,
                "lease_token": claimed.lease_token,
                "worker_name": claimed.worker_name,
                "worker_instance_id": claimed.worker_instance_id,
                "lease_expires_at": claimed.lease_expires_at,
            },
            "input_bundle": dict(input_bundle),
        }
        payload_path = self._write_runner_payload(runner_payload)
        try:
            command = [
                sys.executable,
                "-m",
                "book_agent.tools.runtime_repair_runner",
                "--payload-file",
                str(payload_path),
            ]
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False,
            )
        finally:
            payload_path.unlink(missing_ok=True)
        if completed.returncode != 0:
            stderr = completed.stderr.strip()
            stdout = completed.stdout.strip()
            detail = stderr or stdout or "repair runner exited without output"
            raise RuntimeRepairExecutorInvocationError(
                "Agent-backed repair executor failed to invoke runtime repair runner: "
                f"{detail}"
            )
        stdout = completed.stdout.strip()
        if not stdout:
            raise RuntimeRepairExecutorInvocationError(
                "Agent-backed repair executor received no output from runtime repair runner."
            )
        try:
            payload = json.loads(stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeRepairExecutorInvocationError(
                "Agent-backed repair executor received invalid JSON from runtime repair runner."
            ) from exc
        descriptor = self.descriptor()
        return {
            **payload,
            "repair_executor_name": descriptor.executor_name,
            "repair_executor_execution_mode": descriptor.execution_mode,
            "repair_executor_hint": descriptor.executor_hint,
            "repair_executor_contract_version": descriptor.executor_contract_version,
        }

    def complete_execution(
        self,
        *,
        run_id: str,
        payload: dict[str, Any],
        lease_token: str,
    ) -> None:
        # The subprocess runner owns the success-path DB mutation and completes the work item.
        return None

    def _resolve_database_url(self) -> str:
        bind = self._session_factory.kw.get("bind")
        if bind is None or getattr(bind, "url", None) is None:
            raise RuntimeRepairExecutorInvocationError(
                "Agent-backed repair executor requires a bound database URL."
            )
        database_url = str(bind.url)
        if database_url.endswith("/:memory:") or database_url.endswith("://"):
            raise RuntimeRepairExecutorInvocationError(
                "Agent-backed repair executor requires a file-backed database URL; in-memory "
                "SQLite cannot be shared with a subprocess repair agent."
            )
        return database_url

    @staticmethod
    def _write_runner_payload(payload: dict[str, Any]) -> Path:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            suffix=".runtime-repair.json",
            delete=False,
        ) as handle:
            json.dump(payload, handle)
            handle.flush()
            return Path(handle.name)


class RuntimeRepairExecutorRegistry:
    DEFAULT_EXECUTION_MODE = "in_process"
    DEFAULT_EXECUTOR_HINT = "python_repair_executor"
    DEFAULT_EXECUTOR_CONTRACT_VERSION = 1

    def __init__(
        self,
        *,
        session_factory: sessionmaker,
        registrations: Mapping[tuple[str, str, int], RuntimeRepairExecutorFactory] | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._registrations = dict(registrations or self._default_registrations())

    def resolve_for_input_bundle(
        self,
        *,
        input_bundle: dict[str, Any],
        repair_agent: RuntimeRepairAgentAdapter,
    ) -> RuntimeRepairExecutor:
        execution_mode = str(input_bundle.get("execution_mode") or self.DEFAULT_EXECUTION_MODE).strip()
        executor_hint = str(input_bundle.get("executor_hint") or self.DEFAULT_EXECUTOR_HINT).strip()
        executor_contract_version = int(
            input_bundle.get("executor_contract_version") or self.DEFAULT_EXECUTOR_CONTRACT_VERSION
        )
        return self.resolve(
            execution_mode=execution_mode,
            executor_hint=executor_hint,
            executor_contract_version=executor_contract_version,
            repair_agent=repair_agent,
        )

    def resolve(
        self,
        *,
        execution_mode: str,
        executor_hint: str,
        executor_contract_version: int,
        repair_agent: RuntimeRepairAgentAdapter,
    ) -> RuntimeRepairExecutor:
        normalized_mode = str(execution_mode or self.DEFAULT_EXECUTION_MODE).strip()
        normalized_hint = str(executor_hint or self.DEFAULT_EXECUTOR_HINT).strip()
        normalized_version = int(
            executor_contract_version or self.DEFAULT_EXECUTOR_CONTRACT_VERSION
        )
        factory = self._registrations.get((normalized_mode, normalized_hint, normalized_version))
        if factory is not None:
            return factory(self._session_factory, repair_agent)

        supported_versions = sorted(
            version
            for mode, hint, version in self._registrations
            if mode == normalized_mode and hint == normalized_hint
        )
        if supported_versions:
            supported_text = ", ".join(str(version) for version in supported_versions)
            raise UnsupportedRuntimeRepairExecutorError(
                "Unsupported repair executor contract version "
                f"{normalized_version} for execution_mode={normalized_mode!r}, "
                f"executor_hint={normalized_hint!r}. Supported versions: {supported_text}."
            )

        supported_hints = sorted(
            hint
            for mode, hint, _version in self._registrations
            if mode == normalized_mode
        )
        if supported_hints:
            raise UnsupportedRuntimeRepairExecutorError(
                "Unknown repair executor hint "
                f"{normalized_hint!r} for execution_mode={normalized_mode!r}. "
                f"Supported hints: {', '.join(supported_hints)}."
            )

        supported_modes = sorted({mode for mode, _hint, _version in self._registrations})
        raise UnsupportedRuntimeRepairExecutorError(
            "Unknown repair executor mode "
            f"{normalized_mode!r}. Supported modes: {', '.join(supported_modes)}."
        )

    @classmethod
    def _default_registrations(cls) -> dict[tuple[str, str, int], RuntimeRepairExecutorFactory]:
        return {
            (
                cls.DEFAULT_EXECUTION_MODE,
                cls.DEFAULT_EXECUTOR_HINT,
                cls.DEFAULT_EXECUTOR_CONTRACT_VERSION,
            ): cls._in_process_executor_factory,
            (
                "agent_backed",
                "python_subprocess_repair_executor",
                1,
            ): cls._agent_backed_subprocess_executor_factory,
        }

    @staticmethod
    def _in_process_executor_factory(
        session_factory: sessionmaker,
        repair_agent: RuntimeRepairAgentAdapter,
    ) -> RuntimeRepairExecutor:
        return InProcessRuntimeRepairExecutor(
            session_factory=session_factory,
            repair_agent=repair_agent,
        )

    @staticmethod
    def _agent_backed_subprocess_executor_factory(
        session_factory: sessionmaker,
        repair_agent: RuntimeRepairAgentAdapter,
    ) -> RuntimeRepairExecutor:
        return AgentBackedSubprocessRuntimeRepairExecutor(
            session_factory=session_factory,
            repair_agent=repair_agent,
        )
