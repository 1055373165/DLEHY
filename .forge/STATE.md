# Forge State

last_update_time: 2026-04-05 01:09:00 +0800
mode: resume
current_step: paused
active_batch: none
authoritative_batch_contract: none
expected_report_path: none
active_feature_ids:
- F017
- F018
- F019
- F020
- F021

active_worker_slot:
- none

completed_items:
- Previous `runtime self-heal closure` and Forge v2 governance hardening remain completed and reusable, but they are no longer the active mainline.
- The active product mainline is `translate-agent whole-document readiness, benchmark-backed certification, and controlled slice-first rollout`.
- The current readiness corpus is measured `overall = go` for the certified lanes `L1 / L2 / L3 / L6`.
- Certified-lane slice-first pilots have completed through the normal product path and stopped only at `pilot.slice_target_reached`, not because of bootstrap, parser, or provider failure.
- Expansion wave 1 is now measured `overall = go` for `L2` and `L5`, so the repo has already widened beyond the original nine-sample certification set.
- High-risk text PDFs now use the guarded bootstrap path rather than a direct parser-probe bypass.
- PDF asset provenance now distinguishes true original-image opportunities from vector-only, non-extractable, and fragmented-composite cases on the current benchmark set.
- The user-prioritized single-column paper probe `pdf-attention-single-column-002` is now measured `go` on its minimal parser/export wave.
- The user-prioritized double-column systems-paper probe `pdf-raft-atc14-001` is now also measured `go`, so both requested paper-variance probes widen the measured `L3` evidence set.
- The RAFT repair was structural rather than ad hoc: proceedings-cover PDFs with the real title on page 2 now enter the `academic_paper` lane, and caption linkage scoring now honors block-level `source_anchor` fallback.
- Test-stage token policy is now explicit: the maximum translation-bearing test unit is one `chapter` or an equivalent chapter-sized slice, never a whole book.
- The first `L4` OCR-heavy sample `pdf-man-solved-market-zh-001` is now measured `go` through a bounded slice-scoped OCR probe, and scanned-page image artifacts are preserved as `protect` + `pdf_original_image` rather than collapsing into plain prose.
- The second `L4` OCR-heavy sample `pdf-self-observation-zh-001` is also measured `go`, so the current OCR-heavy lane claim now rests on two scanned-book successes rather than one.
- Forge v2 stop legality is now also enforced at the Codex `Stop` hook layer, so active execution states such as `ready_for_dispatch` are blocked before any stop-time auto-commit can run.
- The EPUB-family expansion sample `epub-agentic-theories-001` is now annotated and measured `go`, widening `L1` with a denser-image, deeper-heading EPUB chapter slice.
- The compact EPUB-family sample `epub-managing-memory-001` is now annotated and measured `go`, adding a second post-certification widened `L1` evidence point beyond `epub-agentic-theories-001`.
- The repo-owned Forge v2 stop hook now emits Codex-compatible `Stop` JSON (`continue` at the top level plus `decision/reason`), so illegal-stop interception no longer fails with `hook returned invalid stop hook JSON output`.
- Stop legality now uses explicit allowlisted pause/review/framework states instead of substring matching, so active implementation steps like `review_stop_hook_protocol_fix` no longer slip through as legal stop boundaries.
- File truth has been resynced after the stop-hook protocol repair so both user-prioritized paper probes remain explicitly recorded as widened `L3` paper-variance success cases while the default next slice stays on the EPUB-family queue.
- The `epub-managing-memory-001` live pilot is now aligned to the intended gold-label chapter `OEBPS/ch05.html` (`ordinal 8`, `Looking Forward: The Feedback Loop`) instead of the earlier mis-targeted ordinal.
- The `epub-managing-memory-001` chapter-5 live pilot is now chapter-complete: all `31/31` packets are translated, review completed with `0` issues, and both review-package + bilingual exports were emitted from the same bounded chapter-scale run chain.
- Chapter-scale smoke continuation now selects the next `BUILT` packet window on rerun instead of replaying the first packet window and skipping already translated work.
- The default translation runtime has been switched from DeepSeek to OpenRouter's free Qwen route through the existing `openai_compatible` adapter, using `https://openrouter.ai/api/v1` and `qwen/qwen3.6-plus:free` as the active target.
- The OpenRouter free route has already passed a live structured-output probe in the project runtime, so this is no longer just a static config change.
- Flat token cost coefficients remain intentionally unset in `.env` after the switch because the active route is a free model and the current reporting field still assumes a single flat `cost_usd` rate.
- The first live chapter-scale pilot on the OpenRouter free Qwen route is now underway on `epub-agentic-theories-001` chapter 12 (`ordinal 13`, `OEBPS/html/636829_1_En_12_Chapter.xhtml`).
- The first two bounded slices on that chapter have translated `16` packets with `0` review-required sentences and no provider failures, but the measured latency profile is much slower than prior routes (about `70s` average, `123s` max per packet).
- A repo-reading, code-first interview-analysis pack for the project owner has been completed in chat and can be resumed later without reopening discovery from scratch.

failed_items:
- none


next_items:
- Keep both `pdf-attention-single-column-002` and `pdf-raft-atc14-001` recorded as widened `L3` paper-variance success cases.
- Keep `pdf-man-solved-market-zh-001` recorded as the first measured-`go` `L4` OCR-heavy success case.
- Keep `pdf-self-observation-zh-001` recorded as the second measured-`go` `L4` OCR-heavy success case.
- Keep all test-stage translation validation capped at chapter scale; do not promote any new sample to whole-book test spend.
- Keep both `epub-agentic-theories-001` and `epub-managing-memory-001` recorded as widened `L1` EPUB-family evidence.
- Keep `epub-managing-memory-001` chapter 5 recorded as a clean chapter-complete live-pilot checkpoint for widened `L1`.
- Fold the `epub-managing-memory-001` chapter-complete pilot evidence into the broader pilot ledger and handoff truth.
- Keep the OpenRouter free Qwen route recorded as runtime-usable but latency-heavy based on the first live `epub-agentic-theories-001` chapter-12 slices.
- Continue the `epub-agentic-theories-001` chapter-12 live pilot through more bounded windows before deciding whether the free route is acceptable for broader rollout.
- Use the OpenRouter free Qwen route as the default translation model for subsequent probes and pilots unless a future measured blocker forces another backend change.
- Keep Stop legality pinned to explicit allowlisted boundary states; active implementation steps must continue automatically.
- Only return to additional OCR-heavy hardening if a future scanned-book probe exposes a measured blocker.
working_tree_scope:
- /Users/smy/project/book-agent/.forge/STATE.md
- /Users/smy/project/book-agent/.forge/DECISIONS.md
- /Users/smy/project/book-agent/.forge/log.md
- /Users/smy/project/book-agent/.forge/spec/SPEC.md
- /Users/smy/project/book-agent/.forge/spec/FEATURES.json
- /Users/smy/project/book-agent/progress.txt
- /Users/smy/project/book-agent/snapshot.md
- /Users/smy/project/book-agent/docs/mainline-progress.md
- /Users/smy/project/book-agent/artifacts/review/translate-agent-benchmark-corpus-expansion-draft.yaml
- /Users/smy/project/book-agent/artifacts/review/gold-labels/pdf-attention-single-column-002.json
- /Users/smy/project/book-agent/artifacts/review/gold-labels/pdf-raft-atc14-001.json
- /Users/smy/project/book-agent/artifacts/review/translate-agent-benchmark-paper-variance-wave1.yaml
- /Users/smy/project/book-agent/artifacts/review/translate-agent-benchmark-paper-variance-wave1-execution-summary.json
- /Users/smy/project/book-agent/artifacts/review/translate-agent-benchmark-paper-variance-wave1-lane-verdicts.json
- /Users/smy/project/book-agent/artifacts/review/translate-agent-benchmark-paper-variance-wave2.yaml
- /Users/smy/project/book-agent/artifacts/review/translate-agent-benchmark-paper-variance-wave2-execution-summary.json
- /Users/smy/project/book-agent/artifacts/review/translate-agent-benchmark-paper-variance-wave2-lane-verdicts.json
- /Users/smy/project/book-agent/artifacts/review/translate-agent-benchmark-execution-summary-current.json
- /Users/smy/project/book-agent/artifacts/review/translate-agent-benchmark-scorecard-current.json
- /Users/smy/project/book-agent/artifacts/review/translate-agent-lane-verdicts-current.json
- /Users/smy/project/book-agent/artifacts/review/translate-agent-pilot-summary-current.json
- /Users/smy/project/book-agent/artifacts/review/translate-agent-benchmark-expansion-wave1-execution-summary.json
- /Users/smy/project/book-agent/artifacts/review/translate-agent-benchmark-expansion-wave1-scorecard.json
- /Users/smy/project/book-agent/artifacts/review/translate-agent-benchmark-expansion-wave1-lane-verdicts.json
- /Users/smy/project/book-agent/artifacts/review/gold-labels/pdf-man-solved-market-zh-001.json
- /Users/smy/project/book-agent/artifacts/review/translate-agent-benchmark-l4-wave1.yaml
- /Users/smy/project/book-agent/artifacts/review/translate-agent-benchmark-l4-wave1-bounded-v2-execution-summary.json
- /Users/smy/project/book-agent/artifacts/review/translate-agent-benchmark-l4-wave1-bounded-v2-scorecard.json
- /Users/smy/project/book-agent/artifacts/review/translate-agent-benchmark-l4-wave1-bounded-v2-lane-verdicts.json
- /Users/smy/project/book-agent/artifacts/review/gold-labels/pdf-self-observation-zh-001.json
- /Users/smy/project/book-agent/artifacts/review/translate-agent-benchmark-l4-wave2.yaml
- /Users/smy/project/book-agent/artifacts/review/translate-agent-benchmark-l4-wave2-bounded-execution-summary.json
- /Users/smy/project/book-agent/artifacts/review/translate-agent-benchmark-l4-wave2-bounded-scorecard.json
- /Users/smy/project/book-agent/artifacts/review/translate-agent-benchmark-l4-wave2-bounded-lane-verdicts.json
- /Users/smy/project/book-agent/src/book_agent/forge_v2_stop_guard.py
- /Users/smy/project/book-agent/.forge/scripts/forge_v2_stop_hook.py
- /Users/smy/project/book-agent/tests/test_forge_v2_stop_guard.py
- /Users/smy/project/book-agent/forge-v2/SKILL.md
- /Users/smy/project/book-agent/forge-v2/references/long-running-hardening.md
- /Users/smy/project/book-agent/artifacts/review/gold-labels/epub-agentic-theories-001.json
- /Users/smy/project/book-agent/artifacts/review/translate-agent-benchmark-epub-family-wave1.yaml
- /Users/smy/project/book-agent/artifacts/review/translate-agent-benchmark-epub-family-wave1-execution-summary.json
- /Users/smy/project/book-agent/artifacts/review/translate-agent-benchmark-epub-family-wave1-scorecard.json
- /Users/smy/project/book-agent/artifacts/review/translate-agent-benchmark-epub-family-wave1-lane-verdicts.json
- /Users/smy/project/book-agent/artifacts/review/gold-labels/epub-managing-memory-001.json
- /Users/smy/project/book-agent/artifacts/review/translate-agent-benchmark-epub-family-wave2.yaml
- /Users/smy/project/book-agent/artifacts/review/translate-agent-benchmark-epub-family-wave2-execution-summary.json
- /Users/smy/project/book-agent/artifacts/review/translate-agent-benchmark-epub-family-wave2-scorecard.json
- /Users/smy/project/book-agent/artifacts/review/translate-agent-benchmark-epub-family-wave2-lane-verdicts.json
- /Users/smy/project/book-agent/artifacts/real-book-live/translate-agent-pilot-epub-managing-memory-001-ch05/report.json
- /Users/smy/project/book-agent/artifacts/real-book-live/translate-agent-pilot-epub-managing-memory-001-ch05/report-slice2.json
- /Users/smy/project/book-agent/artifacts/real-book-live/translate-agent-pilot-epub-managing-memory-001-ch05/report-slice3.json
- /Users/smy/project/book-agent/artifacts/real-book-live/translate-agent-pilot-epub-managing-memory-001-ch05/report-slice4.json
- /Users/smy/project/book-agent/scripts/run_pdf_chapter_smoke.py
- /Users/smy/project/book-agent/tests/test_run_pdf_chapter_smoke.py
- /Users/smy/project/book-agent/.env
- /Users/smy/project/book-agent/artifacts/real-book-live/translate-agent-pilot-epub-agentic-theories-001-ch12/report.json
- /Users/smy/project/book-agent/artifacts/real-book-live/translate-agent-pilot-epub-agentic-theories-001-ch12/report-slice2.json
