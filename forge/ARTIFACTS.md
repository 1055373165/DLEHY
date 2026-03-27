# Codex Forge — Runtime Artifacts

Forge separates framework docs from live run state.

Framework docs live in:

- `forge/`

Live run state lives in:

- `.forge/`

## Live State Layout

### `.forge/STATE.md`

Authoritative run state.

Must contain at least:

- mode
- current step
- active batch
- authoritative batch contract
- expected report path
- active worker slot
- completed items
- failed items
- last verified test baseline
- last update time

The active worker slot should include, when available:

- worker id
- worker nickname
- model
- reasoning setting
- dispatch time
- last harvest check

### `.forge/DECISIONS.md`

Only active decisions and constraints.

Do not turn this into a historical essay.

### `.forge/batches/batch-{N}.md`

Batch contract.

Must define:

- objective
- owned files
- verification command
- dependencies
- stop condition

If a batch is recovered, version it:

- `batch-{N}-v2.md`
- `batch-{N}-v3.md`

Only one version is authoritative at a time.

### `.forge/reports/batch-{N}-report.md`

Worker delivery report.

Must include:

- completed items
- files changed
- exact test commands
- output evidence
- scope deviations
- blockers or discovered work

### `.forge/log.md`

Append-only operational log.

Every recovery, checkpoint, verification, and plan adjustment must land here.

## Minimal State Rule

If a value can be derived cheaply from repo truth and a delivery report, do not duplicate it into
three files.

## Verification Rule

A batch is not done because a worker said so.

A batch is done only when:

1. the report exists
2. master verifies file truth
3. master reruns representative validation
4. `.forge/STATE.md` is updated to reflect the verified result

Worker completion status alone never satisfies the done condition.

## Recovery Rule

If execution stalls:

- preserve the original batch report path
- issue a new batch contract version
- record the recovery in `.forge/log.md`
- never leave two equally valid execution paths active at once
