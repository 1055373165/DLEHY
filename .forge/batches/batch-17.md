# Forge Batch 17

Timestamp: 2026-03-31 14:56:54 +0800
Status: verified

Scope:
- move repair execution ownership into the executor-owned `REPAIR` lane
- ensure scheduled review/export self-heal is claimed and executed only after commit
- make repair work-items succeed only after validate/publish/finalize complete
- keep `REQ-MX-01` and `REQ-EX-02` green while extending repair-lane lineage

Write set:
- /Users/smy/project/book-agent/src/book_agent/app/runtime/controllers/export_controller.py
- /Users/smy/project/book-agent/src/book_agent/app/runtime/controllers/incident_controller.py
- /Users/smy/project/book-agent/src/book_agent/app/runtime/controllers/review_controller.py
- /Users/smy/project/book-agent/src/book_agent/app/runtime/document_run_executor.py
- /Users/smy/project/book-agent/src/book_agent/services/workflows.py
- /Users/smy/project/book-agent/tests/test_export_controller.py
- /Users/smy/project/book-agent/tests/test_incident_controller.py
- /Users/smy/project/book-agent/tests/test_req_ex_02_export_misrouting_self_heal.py
- /Users/smy/project/book-agent/tests/test_req_mx_01_review_deadlock_self_heal.py
- /Users/smy/project/book-agent/tests/test_run_execution.py
- /Users/smy/project/book-agent/docs/mainline-progress.md
- /Users/smy/project/book-agent/progress.txt

Acceptance:
- `.venv/bin/python -m unittest tests.test_runtime_repair_planner tests.test_export_controller tests.test_incident_controller tests.test_req_mx_01_review_deadlock_self_heal tests.test_req_ex_02_export_misrouting_self_heal tests.test_run_execution.RunExecutionServiceTests.test_ensure_repair_dispatch_work_item_seeds_claimable_repair_lane_once`
- `.venv/bin/python -m py_compile src/book_agent/services/runtime_repair_planner.py src/book_agent/services/run_execution.py src/book_agent/app/runtime/controllers/incident_controller.py src/book_agent/app/runtime/controllers/export_controller.py src/book_agent/app/runtime/controllers/review_controller.py src/book_agent/app/runtime/document_run_executor.py src/book_agent/services/workflows.py tests/test_export_controller.py tests/test_incident_controller.py tests/test_req_mx_01_review_deadlock_self_heal.py tests/test_req_ex_02_export_misrouting_self_heal.py tests/test_run_execution.py`
