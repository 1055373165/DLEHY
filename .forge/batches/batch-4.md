# Forge Batch 4

objective:
- Move decisive `release-ready` route-first judgment closer to lane entry.
- Reduce the need to scan mid-page workbench detail before deciding whether to stay in the current release-ready lane.

owned_files:
- /Users/smy/project/book-agent/frontend/src/features/workspace/WorkspacePage.tsx
- /Users/smy/project/book-agent/frontend/src/features/workspace/WorkspacePage.test.tsx
- /Users/smy/project/book-agent/docs/mainline-progress.md

dependencies:
- Forge batch-3 is already verified complete.
- Existing release-ready surfaces already expose:
  - lane health
  - routing cue
  - collapsed supporting signals

acceptance_target:
- In decisive release-ready views, reviewer/operator sees route-first decisions before needing to scan mid-page supporting detail.
- Supporting detail still exists on demand.

verification_command:
- cd /Users/smy/project/book-agent/frontend && npx vitest run src/features/workspace/WorkspacePage.test.tsx src/app/App.test.tsx
- cd /Users/smy/project/book-agent/frontend && npm run build

stop_condition:
- Route-first entry judgment is clearer than before in release-ready lane entry.
- Tests and build pass.
- `docs/mainline-progress.md` is updated to reflect the new mainline state.

expected_report_path:
- /Users/smy/project/book-agent/.forge/reports/batch-4-report.md
