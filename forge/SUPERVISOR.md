# Forge Supervisor

`forge supervisor` is the real background control loop for Forge.

It is not a prompt convention.
It is a repo-local process that watches `.forge/STATE.md`, `.forge/batches/`, and `.forge/reports/`,
then uses `codex exec` to wake the master back up when file truth says the run should continue.
Spawned child runs use `--full-auto` plus a safe reasoning-effort override so the resumed master can
actually edit the workspace instead of stopping in read-only diagnosis mode.

## Commands

One-shot tick:

```bash
book-agent forge-supervisor --workspace /path/to/workspace once
```

Continuous loop:

```bash
book-agent forge-supervisor --workspace /path/to/workspace loop --poll-interval-seconds 5
```

Optional launcher override:

```bash
book-agent forge-supervisor \
  --workspace /path/to/workspace \
  --codex-command codex \
  --codex-command exec \
  once
```

## Required `.forge/STATE.md` Fields

The supervisor expects these fields to exist in `.forge/STATE.md`:

- `current_step`
- `active_batch`
- `active_batch_contract`
- `expected_report`

Recommended execution-tracking fields:

- `active_worker_pid`
- `supervisor_child_pid`
- `supervisor_last_reason`
- `supervisor_last_spawn_at`
- `last_supervisor_poll_at`

## What The Supervisor Actually Does

It evaluates file truth and chooses one of three paths:

1. `harvest-report-ready`
   - expected report already exists
   - wake Codex to harvest/verify/continue
2. `recover-stale-worker-completion`
   - worker pid is no longer alive
   - expected report is still missing
   - wake Codex to recover the batch
3. `continue-*`
   - state says planning / dispatching / verifying / checkpoint / recovery
   - wake Codex to continue the run

If the same reason fired very recently, the supervisor respects a cooldown so it does not spawn
duplicate `codex exec` resumptions.

## Important Boundary

The supervisor does not replace master verification.

It only guarantees that:

- completion signals become harvest triggers
- stale execution becomes recovery triggers
- Forge no longer depends on a human sending another “Yes” just to keep the run moving
