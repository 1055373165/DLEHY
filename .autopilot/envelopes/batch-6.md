# Task Envelope — Batch 6

## Metadata
- batch_id: 6
- phase: 2: Controller Runner Scaffold (No Behavior Change First)
- milestone: 2.2 Wire Runner Into Runtime Startup (best-effort)
- created: 2026-03-26T23:16:00+0800
- agent_role: sub-agent
- mdu_count: 1
- context_budget: 2

## MDU List

### MDU-2.2.1: Integrate ControllerRunner Into DocumentRunExecutor
- description: Integrate controller runner reconcile into runtime startup (alongside existing `DocumentRunExecutor`), keeping Phase A mirror-only behavior and avoiding any new work-item seeding.
- priority: critical path
- depends: MDU-2.1.5
- estimated_lines: 120
- verify: `.venv/bin/python -m pytest tests/test_run_execution.py tests/test_run_control_api.py tests/test_runtime_v2_enums.py tests/test_runtime_resources_repository.py tests/test_runtime_resources.py`
- files:
  - src/book_agent/app/runtime/document_run_executor.py — existing, modify

## ADR Summary

```
ADR-0002: controller reconcile loop; runner must be deterministic and DB-backed
ADR-0003: Phase A mirror-only (resources/checkpoints) must not change artifact semantics
ADR-0004: attempts remain work_items; this batch must NOT seed new work_items via controllers
ADR-LANG: typed signatures; specific exceptions; keep scaffolding safe
ADR-TEST: narrowed Phase-5 gate (runtime/control-plane + REQ-EX-02 aligned subset)
```

## Scope Locks

```
[SCOPE LOCK] MDU-2.2.1: Wire ControllerRunner reconcile into DocumentRunExecutor startup/loop (best-effort)
Parent: Phase 2 → Milestone 2.2
Allowed files: src/book_agent/app/runtime/document_run_executor.py
Self-approve threshold: ≤2 extra files (must record in delivery report)
```

## Test Context

```
framework: pytest
run_command: .venv/bin/python -m pytest tests/test_run_execution.py tests/test_run_control_api.py tests/test_runtime_v2_enums.py tests/test_runtime_resources_repository.py tests/test_runtime_resources.py
min_new_tests: at least 1 for non-trivial wiring (may be in existing tests/test_run_execution.py)
```

