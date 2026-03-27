# Forge Migration Plan

## Goal

After the current isolated Runtime V2 round finishes, migrate the repo's full-cycle execution flow
from the old `autopilot` framework to `forge`.

Current constraint:

- The active round in `/tmp/book-agent-agent-runtime-v2.pUOyOf` must continue on its own archived
  `autopilot/` copy until completion.
- Do not mix `forge` state into that in-flight round.

## Migration Trigger

Start the cutover only when the active round is complete, meaning:

1. the live state in the isolated workspace reaches its terminal completion state
2. no batch is left executing or awaiting verification
3. final delivery artifacts and logs are durable

## Cutover Steps

### Step 1 — Freeze the final autopilot round

- archive the completed `.autopilot` state in the isolated workspace
- preserve all delivery reports and session logs as historical evidence
- do not rewrite historical batch records into Forge format

### Step 2 — Bootstrap Forge live state

Create a fresh `.forge/` live state in the target workspace with:

- `STATE.md`
- `DECISIONS.md`
- `batches/`
- `reports/`
- `log.md`

Use Forge's single-truth model from the start. Do not reintroduce duplicated state ledgers.

### Step 3 — Port the operating loop

Replace the old execution flow with Forge equivalents:

- requirement lock -> `STATE.md`
- active constraints -> `.forge/DECISIONS.md`
- task envelope -> `.forge/batches/batch-{N}.md`
- delivery report -> `.forge/reports/batch-{N}-report.md`
- session/recovery record -> `.forge/log.md`

### Step 4 — Rebase recovery rules

Carry forward the useful hard-won protocols:

- liveness recovery
- stale execution detection
- batch-versioned recovery contracts
- master-side test verification
- framework self-evolution from real failure modes

Do not carry forward:

- phase ceremony that does not change decisions
- duplicated counters across multiple files
- passive waiting without file-truth checks

### Step 5 — Dry run on a small internal task

Before using Forge on the next major feature round:

1. run one small but real multi-file task on Forge
2. verify batch dispatch, report verification, and recovery behavior
3. tighten any weak protocol edges discovered in the dry run

### Step 6 — Default future rounds to Forge

After the dry run succeeds:

- new full-cycle autonomous runs default to `forge`
- old `autopilot` should be treated as historical only

## Success Criteria

The migration is complete when:

1. a new full round starts from `.forge/`
2. master verification uses Forge artifacts only
3. recovery no longer depends on any `autopilot` protocol files
4. the repo has one default autonomous development scaffold, not two competing live flows

## Explicit Non-Goal

This migration does not retroactively rewrite old archived `.autopilot` runs.
Those remain valid historical artifacts.
