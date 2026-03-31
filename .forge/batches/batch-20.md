# Forge Batch 20

## Scope

Promote the repair worker registry from cosmetic routing to genuinely distinct worker
implementations for review deadlock and export misrouting.

## Goals

- Keep `RuntimeRepairWorkerRegistry` as the single routing surface.
- Resolve `review_deadlock_repair_agent` and `export_routing_repair_agent` to different worker
  classes instead of the same generic implementation.
- Make each specialized worker reject unsupported incident kinds so hint/version routing is
  semantically enforced.

## Acceptance

```bash
.venv/bin/python -m unittest \
  tests.test_runtime_repair_registry \
  tests.test_runtime_repair_planner \
  tests.test_export_controller \
  tests.test_incident_controller \
  tests.test_req_mx_01_review_deadlock_self_heal \
  tests.test_req_ex_02_export_misrouting_self_heal \
  tests.test_run_execution.RunExecutionServiceTests.test_ensure_repair_dispatch_work_item_seeds_claimable_repair_lane_once \
  tests.test_run_execution.RunExecutionServiceTests.test_executor_fails_repair_work_item_for_unknown_worker_hint
```

```bash
.venv/bin/python -m py_compile \
  src/book_agent/services/runtime_repair_registry.py \
  src/book_agent/services/runtime_repair_planner.py \
  src/book_agent/services/runtime_repair_worker.py \
  src/book_agent/services/run_execution.py \
  src/book_agent/app/runtime/controllers/incident_controller.py \
  src/book_agent/app/runtime/controllers/export_controller.py \
  src/book_agent/app/runtime/controllers/review_controller.py \
  src/book_agent/app/runtime/document_run_executor.py \
  src/book_agent/services/workflows.py \
  tests/test_runtime_repair_registry.py \
  tests/test_runtime_repair_planner.py \
  tests/test_export_controller.py \
  tests/test_incident_controller.py \
  tests/test_req_mx_01_review_deadlock_self_heal.py \
  tests/test_req_ex_02_export_misrouting_self_heal.py \
  tests/test_run_execution.py
```
