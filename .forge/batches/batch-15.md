# Forge Batch 15

Timestamp: 2026-03-30 21:37:13 +0800
Status: verified

Scope:
- keep the structured runtime repair plan
- seed a runtime-owned `repair_dispatch` on runtime patch proposals and incidents
- make the existing review deadlock and export misrouting self-heal flows explicitly claim and execute that dispatch before validation / publish

Write set:
- /Users/smy/project/book-agent/src/book_agent/services/runtime_repair_planner.py
- /Users/smy/project/book-agent/src/book_agent/app/runtime/controllers/incident_controller.py
- /Users/smy/project/book-agent/src/book_agent/app/runtime/controllers/export_controller.py
- /Users/smy/project/book-agent/src/book_agent/app/runtime/controllers/review_controller.py
- /Users/smy/project/book-agent/tests/test_runtime_repair_planner.py
- /Users/smy/project/book-agent/tests/test_export_controller.py
- /Users/smy/project/book-agent/tests/test_incident_controller.py
- /Users/smy/project/book-agent/docs/mainline-progress.md
- /Users/smy/project/book-agent/progress.txt

Acceptance:
- `.venv/bin/python -m unittest tests.test_runtime_repair_planner tests.test_export_controller tests.test_incident_controller tests.test_req_mx_01_review_deadlock_self_heal`
- `.venv/bin/python -m py_compile src/book_agent/services/runtime_repair_planner.py src/book_agent/app/runtime/controllers/incident_controller.py src/book_agent/app/runtime/controllers/export_controller.py src/book_agent/app/runtime/controllers/review_controller.py tests/test_runtime_repair_planner.py tests/test_export_controller.py tests/test_incident_controller.py`
