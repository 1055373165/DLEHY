# Forge Batch 16

Timestamp: 2026-03-31 14:34:12 +0800
Status: verified

Scope:
- bind proposal-level `repair_dispatch` lineage to a claimable `REPAIR` work-item surface
- keep proposal/incident repair lineage deterministic while using the existing work-item lifecycle
- preserve bounded replay semantics for review deadlock while making repair execution explicitly claimable

Write set:
- /Users/smy/project/book-agent/src/book_agent/app/runtime/controllers/incident_controller.py
- /Users/smy/project/book-agent/src/book_agent/services/run_execution.py
- /Users/smy/project/book-agent/tests/test_export_controller.py
- /Users/smy/project/book-agent/tests/test_incident_controller.py
- /Users/smy/project/book-agent/tests/test_req_mx_01_review_deadlock_self_heal.py
- /Users/smy/project/book-agent/tests/test_run_execution.py
- /Users/smy/project/book-agent/docs/mainline-progress.md
- /Users/smy/project/book-agent/progress.txt

Acceptance:
- `.venv/bin/python -m unittest tests.test_runtime_repair_planner tests.test_export_controller tests.test_incident_controller tests.test_req_mx_01_review_deadlock_self_heal tests.test_run_execution.RunExecutionServiceTests.test_ensure_repair_dispatch_work_item_seeds_claimable_repair_lane_once`
- `.venv/bin/python -m py_compile src/book_agent/services/runtime_repair_planner.py src/book_agent/services/run_execution.py src/book_agent/app/runtime/controllers/incident_controller.py src/book_agent/app/runtime/controllers/export_controller.py src/book_agent/app/runtime/controllers/review_controller.py tests/test_runtime_repair_planner.py tests/test_export_controller.py tests/test_incident_controller.py tests/test_run_execution.py tests/test_req_mx_01_review_deadlock_self_heal.py`
