# Batch 20 Report

## Outcome

Verified complete.

## Delivered

- Promoted the repair registry from metadata routing to distinct worker implementations.
- `review_deadlock_repair_agent` now resolves to a dedicated `ReviewDeadlockRepairWorker`.
- `export_routing_repair_agent` now resolves to a dedicated `ExportRoutingRepairWorker`.
- Specialized workers now reject unsupported incident kinds, so hint/version selection is enforced
  inside the repair lane instead of only at the registry lookup level.

## Verification

- `unittest`: 15 tests OK
- `py_compile`: passed

## Next Slice

Move from distinct in-process repair workers to genuinely independent repair-agent adapters or
executors, so the runtime can route a `REPAIR` work item to something other than local class
specialization.
