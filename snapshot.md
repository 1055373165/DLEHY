# Translate Agent Readiness Snapshot

Last Updated: 2026-04-05 00:58 +0800
Workspace: `/Users/smy/project/book-agent`
Branch: `main`
Worktree Policy: single live worktree only

## Current Mainline

This snapshot is the authoritative human-readable handoff for the active translate-agent line.

The active mainline is:

`translate-agent high-fidelity whole-document translation readiness`
`+`
`benchmark-backed certification and expansion for PDF books / EPUB books / PDF papers`
`+`
`controlled slice-first rollout instead of blind full-document execution`

## Current Measured State

Current readiness verdict: `overall go`

Grounding artifacts:

- `/Users/smy/project/book-agent/artifacts/review/translate-agent-benchmark-execution-summary-current.json`
- `/Users/smy/project/book-agent/artifacts/review/translate-agent-benchmark-scorecard-current.json`
- `/Users/smy/project/book-agent/artifacts/review/translate-agent-lane-verdicts-current.json`
- `/Users/smy/project/book-agent/artifacts/review/translate-agent-readiness-certification-current.md`

Current certified lanes:

- `L1` `EPUB-reflowable-tech-book` -> `go`
- `L2` `PDF-text-tech-book` -> `go`
- `L3` `PDF-text-academic-paper` -> `go`
- `L6` `High-artifact-density-paper` -> `go`

Follow-on evidence already exists:

- certified-lane slice-first pilots completed cleanly through the product path
- expansion wave 1 is measured `overall go` for `L2` and `L5`
- the first `L4` OCR-heavy sample `pdf-man-solved-market-zh-001` is measured `go` through a bounded slice-scoped OCR probe
- the second `L4` OCR-heavy sample `pdf-self-observation-zh-001` is also measured `go` through the same bounded slice-scoped OCR path
- Forge v2 stop legality is now enforced at the Codex `Stop` hook layer for this repo, so `ready_for_dispatch` and similar active continuation states should no longer silently end the run and wait for another user `continue`
- the EPUB-family expansion sample `epub-agentic-theories-001` is now measured `go` through a chapter-scale parser/export wave
- the compact EPUB-family sample `epub-managing-memory-001` is now also measured `go` through a second chapter-scale parser/export wave
- hook stop legality now uses explicit allowlisted stop states, so active implementation steps that merely contain `review` no longer slip through as legal stops
- the first live chapter-scale pilot on `epub-managing-memory-001` is now correctly aligned to `OEBPS/ch05.html`
- that chapter is now fully translated at `31/31` packets with `0` review-required sentences
- chapter review completed with `0` issues and both review-package + bilingual exports were emitted
- chapter-scale reruns now advance to the next `BUILT` packet window instead of replaying the first translated window
- the default translation provider target has been switched from DeepSeek to OpenRouter's free Qwen route through the existing `openai_compatible` layer, with `qwen/qwen3.6-plus:free` as the active model string
- the new route has already passed a minimal live structured-output probe
- the first real chapter-scale pilot on that route is now running on `epub-agentic-theories-001` Chapter 12 and has already completed two bounded slices
- early measured result: usable and stable so far, but much slower than previous routes

## What This Means

The repo is already past “can it recognize structure at all?” and into “how do we widen the claim safely?”

That means:

- certified lanes can continue in `slice-first` mode
- new document families should be added through annotation plus small parser/export probes
- the next work should move on from this finished chapter checkpoint to the next live EPUB-family pilot, not back to annotation and not to more spend on the same finished chapter
- that next live EPUB-family pilot is now concretely `epub-agentic-theories-001` Chapter 12 on the OpenRouter free Qwen route
- test-stage translation validation is capped at chapter scale; whole-book tests are not the default validation unit
- the Codex home `Stop` hook should remain pointed at the Forge v2 stop guard while this mainline stays autonomous

## Immediate Forge-v2 Queue

Forge v2 is the default owner of this queue. Non-essential user confirmation is not required.

Top-of-stack next tasks:

1. `pdf-attention-single-column-002`
   - source: `/Users/smy/Downloads/NIPS-2017-attention-is-all-you-need-Paper (1).pdf`
   - intent: user-prioritized single-column paper-variance probe for `L3`
   - current result: measured `go`
2. `pdf-raft-atc14-001`
   - source: `/Users/smy/Downloads/raft-atc14.pdf`
   - intent: user-prioritized double-column systems-paper probe for `L3`
   - current result: measured `go`
   - key repair: proceedings-cover PDFs with title pages on page 2 now enter `academic_paper` recovery correctly
3. keep both samples recorded as widened `L3` paper-variance success cases
4. keep both `pdf-man-solved-market-zh-001` and `pdf-self-observation-zh-001` as measured `L4` success cases
5. keep `epub-agentic-theories-001` as widened `L1` evidence
6. default next slice: move to the next live EPUB-family chapter-scale pilot after recording `epub-managing-memory-001` chapter 5 as a clean checkpoint

## Important Boundaries

- Current certification is measured, but it is still bounded to the known sample families.
- High-risk text PDFs now enter the guarded bootstrap path through the normal product route.
- `L6` remains a `Tier C` lane: preserve content and artifacts first, degrade explicitly when necessary.
- Asset parity should reopen only when a future document exposes a true extractable-original miss.
- Benchmark-scoring truth now also treats `caption_for_source_anchor` plus block-level `source_anchor` as sufficient linkage evidence when block-id materialization is absent.
- Test-stage spend stays capped at one chapter or an equivalent chapter-sized slice until work explicitly moves into rollout pilot mode.
