# Forge Batch 17 Report

Timestamp: 2026-03-31 14:56:54 +0800
Result: verified

Delivered:
- repair execution ownership now sits in the executor-owned `REPAIR` lane instead of the controller sync path
- scheduled review deadlock and export misrouting repairs are now claimed and executed after commit, matching real runtime visibility
- repair work-items now complete successfully only after validate/publish/finalize finish, avoiding false-positive success when the repair chain fails midway
- `REQ-EX-02` still closes the loop through the API surface after the repair lane executes and replays the failed export scope

Verification:
- `.venv/bin/python -m unittest tests.test_runtime_repair_planner tests.test_export_controller tests.test_incident_controller tests.test_req_mx_01_review_deadlock_self_heal tests.test_req_ex_02_export_misrouting_self_heal tests.test_run_execution.RunExecutionServiceTests.test_ensure_repair_dispatch_work_item_seeds_claimable_repair_lane_once` -> `Ran 11 tests, OK`
- `.venv/bin/python -m py_compile src/book_agent/services/runtime_repair_planner.py src/book_agent/services/run_execution.py src/book_agent/app/runtime/controllers/incident_controller.py src/book_agent/app/runtime/controllers/export_controller.py src/book_agent/app/runtime/controllers/review_controller.py src/book_agent/app/runtime/document_run_executor.py src/book_agent/services/workflows.py tests/test_export_controller.py tests/test_incident_controller.py tests/test_req_mx_01_review_deadlock_self_heal.py tests/test_req_ex_02_export_misrouting_self_heal.py tests/test_run_execution.py` -> `passed`

Notes:
- `uv sync --extra dev` was needed once to restore `httpx` and re-enable API acceptance coverage
- a workflow dashboard call site needed `chapter_memory_proposal_map` wired back in before `REQ-EX-02` could prove the post-repair export dashboard path
- no extra worktree and no commit created
- the next dependency-closed slice is to harden a dedicated repair-agent contract on top of this executor-owned repair lane
