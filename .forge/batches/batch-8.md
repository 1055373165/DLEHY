# Forge Batch 8

objective:
- Lift decisive `release-ready` route-first judgment from `Lens 选择预判` into higher-level `Active Scope / Session Digest` summaries.
- Let reviewer/operator judge whether a lane is worth entering before reaching the Operator Lens controls.

owned_files:
- /Users/smy/project/book-agent/progress.txt
- /Users/smy/project/book-agent/frontend/src/features/workspace/WorkspacePage.tsx
- /Users/smy/project/book-agent/frontend/src/features/workspace/WorkspacePage.test.tsx
- /Users/smy/project/book-agent/docs/mainline-progress.md

dependencies:
- Forge batch-7 is already verified complete.
- Existing release-ready surfaces already expose:
  - `Lens 选择预判`
  - `子队列入口预判`
  - Operator Lens entry routing

acceptance_target:
- In release-ready flow, reviewer/operator gets the same route-first guidance in high-level Active Scope / Session Digest summaries.
- The cue should appear before the user reaches the Operator Lens controls.

verification_command:
- cd /Users/smy/project/book-agent/frontend && npx vitest run src/features/workspace/WorkspacePage.test.tsx src/app/App.test.tsx
- cd /Users/smy/project/book-agent/frontend && npm run build

stop_condition:
- Route-first release-ready judgment appears in high-level summary surfaces before Operator Lens controls.
- Tests and build pass.
- `docs/mainline-progress.md` and `progress.txt` are updated to reflect the new mainline state.

expected_report_path:
- /Users/smy/project/book-agent/.forge/reports/batch-8-report.md
