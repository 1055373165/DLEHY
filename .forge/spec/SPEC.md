# Translate Agent Whole-Document Readiness Spec

## North Star

Book Agent should behave like a high-fidelity translation system that can safely translate whole
books and papers only after it has proven readiness on representative document families.

For `PDF books`, `EPUB books`, and `PDF papers`, the system should:

- preserve protected artifacts such as code, equations, tables, figures, captions, and inline code
- recover usable heading hierarchy even when the source layout is irregular
- keep reading order stable enough for technical and academic documents
- prefer original assets whenever they exist, and fall back to high-resolution rendering when they
  do not
- degrade explicitly when full layout fidelity is unsafe, instead of silently corrupting content
- use benchmark-backed evidence rather than impression-based confidence to decide whether a whole
  document may proceed

## Explicit Requirements

1. The active readiness corpus must cover the currently certified lanes:
   - `L1` `EPUB-reflowable-tech-book`
   - `L2` `PDF-text-tech-book`
   - `L3` `PDF-text-academic-paper`
   - `L6` `High-artifact-density-paper`
2. Gold labels must exist for benchmark slices so parser/export quality is measured against explicit
   truth rather than subjective inspection.
3. The parser/export stack must preserve protected artifacts instead of routing them through normal
   prose translation paths.
4. The parser/export stack must recover heading hierarchy and reading order well enough for
   benchmarked technical and academic documents.
5. The parser/export stack must preserve or explicitly link figure/table/equation captions.
6. PDF and EPUB image handling must prefer original assets when available and use high-resolution
   fallback rendering when they are not.
7. Readiness decisions must be grounded in executable benchmark outputs:
   - execution summary
   - scorecard
   - lane verdicts
   - certification report
8. High-risk text PDFs must be allowed through the guarded bootstrap path when they are parser-ready
   text PDFs; explicit risk metadata should remain visible instead of being hidden behind entry rejection.
9. Whole-document execution must default to `slice-first` on certified lanes.
10. The current readiness claim must remain bounded to measured samples; it must not be restated as
    universal cross-format support.
11. Expansion beyond the current certified set must happen via new annotated samples and small
    parser/export probes before any fresh whole-document token spend.
12. Future continuation must enter through explicit `change_request` work against the same single
    `.forge/` ledger.
13. During testing, prompt validation, and readiness probing, the maximum translation-bearing unit
    is one `chapter` or an equivalent chapter-sized slice, never an entire book.
14. Forge v2 stop legality must be enforceable at the hook layer: when Codex `Stop` hooks are
    active, the stop hook must read `.forge/STATE.md` and block stops from active continuation
    states such as `ready_for_dispatch`; post-stop side effects like auto-commit may run only
    after stop legality passes.
15. Hook-layer stop legality must use explicit allowlisted stop states rather than substring heuristics,
    so active implementation steps like `review_stop_hook_protocol_fix` cannot be mistaken for legal
    pause/review boundaries.
16. Chapter-scale pilot execution must be resume-capable: rerunning the same chapter smoke should
    consume the next window of `BUILT` packets for that chapter rather than reselecting the same
    already translated leading packet ids.

## Hidden Requirements

- Code blocks, commands, equations, tables, and figure-internal artifacts must not be translated as
  ordinary prose.
- Asset fidelity is not just about images existing; the system must preserve original-resolution
  assets whenever the source format actually provides them.
- High-artifact-density papers may require controlled degradation; that downgrade must be explicit,
  not silent.
- Parser success alone is insufficient; readiness depends on structure, artifact protection,
  reading order, caption linkage, and asset legibility together.
- Resume sessions must not depend on chat memory to know which document families are currently safe
  to run or which new samples are queued next.
- Stop legality must not depend on the model remembering to continue; the workspace should enforce
  it from `.forge` truth when hook support exists.
- Chapter-scale rollout is not just a budget cap; the control path must also support bounded
  continuation across multiple slices inside the same chapter.

## Constraints

- Work in the single shared checkout.
- Do not open a second live ledger.
- Keep benchmark execution cheap enough that readiness can be rechecked without wasting large
  translation token budgets.
- Prefer targeted parser/export hardening and benchmark probes over large blind reruns.
- Do not use whole-book translation tests as a validation mechanism when a chapter-sized slice can
  answer the same question.
- Keep whole-document rollout conservative: `slice-first` before `full-rollout`.

## Chosen Problem Framing

The active mainline problem is no longer runtime self-heal closure.

The current repo is primarily solving:

- whether the translate agent can faithfully preserve technical document structure and artifacts
- whether that claim is measured strongly enough to justify whole-document execution
- how to widen that claim from the current certified set to new document families without wasting
  translation tokens

## Chosen Solution Topology

The chosen topology is:

1. classify the document into a benchmarked or candidate lane
2. parse structure and protected artifacts
3. preserve assets using original-first extraction plus fallback rendering
4. compare benchmark slices against gold labels
5. derive execution summary, scorecard, and lane verdicts
6. certify or block whole-document execution
7. on certified lanes, run whole documents in `slice-first` mode
8. for new samples, widen the corpus through annotation plus the smallest parser/export probe first
9. enforce stop legality through the Codex `Stop` hook before any post-stop automation runs
10. advance chapter-scale pilots through successive built-packet windows until the chapter closes or
    a measured blocker appears

## User And Operator Flows

### Certified Lane Flow

1. A document matches a certified lane.
2. Parser/export stack preserves structure and artifacts.
3. The lane remains backed by current benchmark evidence.
4. Whole-document translation proceeds in `slice-first` mode.
5. Translation-bearing tests stay capped at `chapter` scale unless the work has already moved out
   of test mode and into an approved rollout step.

### New Sample Expansion Flow

1. A new document family or layout-variance sample appears.
2. It does not inherit certification by default.
3. It receives gold-label truth plus a parser/export benchmark probe.
4. Only then may it join or widen the certified claim.

### Controlled Degradation Flow

1. A high-artifact-density slice cannot safely recover inner artifact text.
2. The system preserves the artifact and degrades explicitly.
3. It does not pretend the output is full visual and textual fidelity when it is not.

## Edge Cases And Failure Modes

- heading and body text arrive in a single PDF block
- first-page academic frontmatter embeds `ABSTRACT` inside author text
- appendix-style headings use lettered numbering rather than numeric numbering
- figure and caption appear across page or block boundaries
- PDF exposes vector drawings instead of embedded bitmap images
- one paper family is single-column while another is double-column and both must remain inside the same academic lane claim

## Non-Goals

- claiming universal support for every PDF/EPUB/paper format
- blind full-document rollout by default
- reopening older runtime self-heal work as the active narrative
- spending large translation token budgets just to rediscover already-measured parser issues

## Success Criteria

The active mainline is considered healthy when:

- the current benchmark corpus remains executable
- certified lanes remain `go`
- current benchmark execution still shows no parse failures on the active certification set
- current benchmark execution still shows no catastrophic protected-artifact corruption on the
  certified set
- pilot evidence continues to support `slice-first` rollout on certified lanes
- expansion-wave probes add new document families without requiring ad hoc chat memory

## Current Delivery Strategy

1. Preserve the current certified readiness baseline.
2. Keep the user-prioritized paper-variance probes as measured widening evidence for `L3`:
   - `/Users/smy/Downloads/NIPS-2017-attention-is-all-you-need-Paper (1).pdf`
   - `/Users/smy/Downloads/raft-atc14.pdf`
3. Use those two measured `go` probes to justify wider paper-layout variance claims without
   spending whole-document translation tokens on them yet.
4. Continue expansion via `L4` OCR-heavy or broader EPUB family coverage, starting with the
   smallest dependency-closed `L4` sample.
5. Reopen parser/export hardening only if new expansion probes expose measured blockers.
6. Keep test-stage token spend capped at chapter scale; use full-document runs only after a lane is
   already certified and the work is explicitly a rollout pilot rather than a test.
7. Treat the first measured-`go` OCR-heavy sample as lane-seeding evidence, then move immediately to
   a second OCR-heavy sample before broadening the lane claim.
8. After a second OCR-heavy sample also lands on measured `go`, move the default expansion queue
   back to another family rather than continuing to overfit the OCR-heavy lane.
9. Keep the Codex `Stop` hook aligned with `.forge` truth so active continuation states cannot end
   the run just because the assistant wrote a tidy update.
10. Keep chapter-scale pilot control aligned with packet status so later bounded reruns continue the
    active chapter instead of replaying already translated packet windows.
11. Treat a chapter-complete, review-clean, exported chapter pilot as a stronger rollout checkpoint
    than a partial `slice_target_reached` stop, and use that checkpoint to choose the next sample
    rather than repeatedly spending test tokens on the same finished chapter.
