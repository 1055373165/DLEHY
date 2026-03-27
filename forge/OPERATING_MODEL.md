# Codex Forge — Operating Model

## Why This Exists

The old `autopilot/` framework proved that persistent state, batched delivery, and master-side
verification are useful. It also proved that too much phase ritual and too many state transitions
can slow real work down.

Forge keeps the discipline and drops the drag.

## What Forge Keeps

- locked requirement
- explicit constraints
- file-backed run state
- batch contracts
- delivery reports
- master verification
- recovery protocol
- framework evolution from real failures

## What Forge Drops

- phase-heavy choreography for every task
- spikes by default
- duplicate state ledgers
- “executing” states without launch evidence
- passive waiting when file truth shows no progress

## The Practical Loop

### 1. Lock

Create a requirement that is narrow enough to execute and strong enough to protect scope.

### 2. Freeze

Write only the decisions needed to prevent thrash:

- architecture
- testing
- rollback / safety
- major boundary choices

### 3. Batch

Take the next dependency-closed slice.

Good batch:

- changes a coherent surface
- is independently verifiable
- has a bounded write set
- can be recovered or replayed cleanly

Bad batch:

- exists only to preserve a planning aesthetic
- mixes unrelated write surfaces
- cannot be validated without finishing three later batches

### 4. Execute

Workers execute the batch contract. They do not own global truth.

Dispatch is only half of execution.
Master must keep an active harvest path for the worker it just launched.

### 5. Verify

Master verifies:

- the report exists
- the owned files landed
- representative tests pass
- the state ledger matches reality

If worker status says complete before the report exists, verification does not wait passively.
Master immediately harvests or recovers that batch.

### 6. Adapt

If the plan is wrong, the plan changes immediately.

## Recovery Philosophy

Forge treats stale execution as a framework problem first, not an operator problem first.

When a batch stalls:

1. inspect file truth
2. identify whether work actually started
3. version the batch contract if recovery is needed
4. dispatch one authoritative replacement path

When a batch "finishes" at the worker level but no report lands:

1. treat the worker status as a trigger, not as success
2. inspect report + owned-file truth immediately
3. if truth is missing, recover immediately instead of idling in executing state

## State Philosophy

Forge prefers one live state surface and append-only logs over several partially overlapping
progress trackers.

That means:

- one state file
- one decisions file
- one batch directory
- one reports directory
- one append-only log

## Human Checkpoints

Humans should only be pulled in for:

- requirement ambiguity with structural consequences
- architecture decisions with real tradeoffs
- large re-scope or backtrack
- unresolved safety boundary

Everything else should keep moving.
