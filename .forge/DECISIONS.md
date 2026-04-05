# Forge Decisions

1. Workspace decision
- Stay in the single main repo checkout on `main`.
- Do not create a second live worktree or a second live ledger.

2. Mainline decision
- The current active mainline is `translate-agent whole-document readiness, benchmark-backed certification, and controlled slice-first rollout`.
- The older `runtime self-heal closure` line remains completed baseline capability, not the current owner of repo momentum.

3. Scope control decision
- Prioritize work that improves high-fidelity translation readiness for `PDF books`, `EPUB books`, and `PDF papers`.
- Prioritize parser/export fidelity, benchmark-backed confidence, and conservative rollout over unrelated product polish.
- Do not reopen runtime/governance work unless it directly blocks translate-agent execution or truth maintenance.

4. Current readiness decision
- The current measured readiness verdict is `go`, not merely “looks promising”.
- This approves `controlled, slice-first whole-document execution` on the currently certified lanes.
- This does not mean the project has universal support for every unseen PDF/EPUB layout.

5. Certified lane decision
- `L1` `EPUB-reflowable-tech-book`: `go`
- `L2` `PDF-text-tech-book`: `go`
- `L3` `PDF-text-academic-paper`: `go`
- `L6` `High-artifact-density-paper`: `go`
- `L6` remains a `Tier C` certification: preserve content and artifacts first, then degrade explicitly when inner artifact text cannot be recovered safely.

6. Post-certification decision
- Certified-lane pilots and expansion wave 1 are already complete enough to justify widening the benchmark corpus rather than reworking cleared lanes.
- The next default work is `paper-layout variance expansion`, not another generic hardening pass on already-cleared `L1 / L2 / L3 / L5 / L6`.

7. User-prioritized sample decision
- The next two benchmark tasks are explicitly user-prioritized:
  - `pdf-attention-single-column-002` from `/Users/smy/Downloads/NIPS-2017-attention-is-all-you-need-Paper (1).pdf`
  - `pdf-raft-atc14-001` from `/Users/smy/Downloads/raft-atc14.pdf`
- These two samples should be treated as the top of the expansion queue ahead of generic `L4` OCR-heavy exploration.
- The first is treated as a single-column paper-variance probe for `L3`.
- The second is treated as a double-column systems-paper probe for `L3`.
- The first probe is now measured `go`.
- The second probe is now measured `go` after profiler and benchmark-scoring hardening.
- Both measured-`go` paper probes remain part of widened `L3` paper-variance truth even as the default next slice moves on to other families.

8. Execution-order decision
- For both new paper samples, do the smallest dependency-closed work first:
  - create or refine gold-label truth
  - run parser/export benchmark probe
  - inspect measured blockers or measured `go`
- Do not spend new translation tokens on whole-document pilot expansion for those samples until the smallest probe is measured.
- With both paper probes now green, the next immediate work is `L4` OCR-heavy lane creation through annotation plus a minimal parser/export probe, not more `L3` variance hardening.
- The first `L4` OCR-heavy sample is now measured `go`; the default next slice is the second OCR-heavy sample, not another rerun of the first one.
- The second `L4` OCR-heavy sample is now also measured `go`; the default next slice shifts back to the EPUB-family queue rather than continuing to widen OCR-heavy books immediately.

9. Operating-mode decision
- Forge v2 is the default owner of next-step selection on this mainline.
- Non-essential user confirmation is not required.
- Only stop to ask when local file truth is insufficient to continue safely or a destructive action would be required.

10. Write-set decision
- Prefer staying inside:
  - `.forge/STATE.md`
  - `.forge/DECISIONS.md`
  - `.forge/log.md`
  - `.forge/spec/SPEC.md`
  - `.forge/spec/FEATURES.json`
  - `snapshot.md`
  - `progress.txt`
  - `docs/mainline-progress.md`
  - `artifacts/review/translate-agent-benchmark-corpus-expansion-draft.yaml`
  - `artifacts/review/gold-labels/*.json`
  - `artifacts/review/translate-agent-benchmark-*.json`
  - `artifacts/review/translate-agent-lane-verdicts-current.*`
  - `artifacts/review/translate-agent-pilot-summary-current.*`
- Expand only if blocked by a real dependency.

11. Verification decision
- Every planning-truth update must at minimum pass:
  - conflict-marker scan on `.forge` and handoff files
  - `python3 -m json.tool .forge/spec/FEATURES.json`
  - `python3 -m json.tool` on any touched benchmark JSON artifact
- Every future parser/export slice should additionally re-run the smallest targeted `unittest`, `py_compile`, and benchmark scripts that its write-set actually changes.

12. Handoff decision
- `.forge` truth, human-facing handoff docs, and expansion-draft truth must all agree on:
  - the current translate-agent mainline
  - the current measured readiness state
  - the next ordered task stack
- Future continuation should enter through this translate-agent ledger, not by reviving stale canonical-IR or runtime-self-heal narratives.

13. Test-unit budget decision
- During test and benchmark execution, the maximum translation-bearing test unit is one `chapter`
  or an equivalent chapter-sized slice.
- Do not run whole-book translation tests just to validate readiness or prompt quality; that spend
  is too large for the diagnostic value it provides.
- For OCR-heavy or irregular PDFs where chapter boundaries are not yet recoverable, use the
  smallest annotated page slice or parser/export probe that preserves the same decision quality.

14. Hook-enforced stop decision
- Forge v2 stop legality must now be enforced in the Codex `Stop` hook, not only in prompt text.
- The hook must read `.forge/STATE.md` and block stop whenever file truth still shows an active
  continuation state such as `ready_for_dispatch`.
- Post-stop automation such as auto-commit must run only after the hook confirms the stop is legal.
- If the active mainline changes its legal stop states later, the hook contract must be updated in
  the same slice as the `.forge` truth.

15. EPUB-family expansion decision
- The first post-OCR EPUB-family expansion sample is `epub-agentic-theories-001`.
- That sample is now measured `go` on a chapter-scale parser/export wave covering deeper heading
  nesting, archive-backed figures, and ordered-list-heavy content.
- The default next expansion slice therefore moves to `epub-managing-memory-001`, not back to OCR
  hardening and not to whole-book spend.

16. Chapter-scale pilot continuation decision
- Chapter-scale pilot reruns must select the next `BUILT` packet window, not the first N packet ids
  from the chapter regardless of status.
- A bounded chapter-scale pilot may advance through multiple packet windows on the same chapter as
  long as it remains inside the same chapter boundary and does not escalate to whole-book test spend.
- `epub-managing-memory-001` chapter 5 is now the active rollout proof point for this rule:
  `report.json` records the first 8 translated packets on `OEBPS/ch05.html`, and `report-slice2.json`
  records the next 8 translated packets on the same chapter without reopening bootstrap or replaying
  the first slice.
- `report-slice3.json` and `report-slice4.json` complete that same chapter to `31/31` translated
  packets, `0` review issues, and successful review-package + bilingual exports, proving the bounded
  continuation rule all the way through chapter closure rather than only through one follow-up slice.

17. Translation-model decision
- The default translation backend remains `openai_compatible`, but the active provider target is now
  OpenRouter's free Qwen route rather than DeepSeek.
- The default model string is `qwen/qwen3.6-plus:free`, and the base URL is the official OpenRouter
  endpoint `https://openrouter.ai/api/v1`.
- A minimal live structured-output probe has already succeeded on this route, so the provider switch
  is runtime-verified instead of configuration-only.
- Flat per-1M-token cost coefficients remain removed from `.env` because the active route is free
  while current reporting still labels estimated spend as `cost_usd`; incorrect synthetic pricing is
  worse than `null`.

18. OpenRouter-free rollout decision
- The OpenRouter free Qwen route is now proven usable on both a minimal structured probe and a real
  chapter-scale live pilot.
- That route should currently be treated as `usable but latency-heavy`, not yet as an unqualified
  replacement for faster paid routes.
- The first measured live evidence comes from `epub-agentic-theories-001` chapter 12, where the
  first two bounded slices translated `16` packets with `0` provider failures and `0`
  review-required sentences, but with roughly `70s` average and `123s` worst-case packet latency.


11. Stop legality decision
- Stop legality at the hook layer must use explicit allowlisted boundary states, not broad substring matches.
- Active implementation steps that merely contain words like `review` are still continuation states and must be blocked from stopping.
- The legacy Codex-home `Stop -> auto_commit.py` entry and the repo-owned Forge v2 wrapper must both enforce the same legality rule so cached sessions cannot bypass it.

12. EPUB-family widening decision
- `epub-agentic-theories-001` and `epub-managing-memory-001` now both count as widened `L1` evidence.
- `epub-managing-memory-001` is measured `go` on a chapter-scale parser/export wave covering repeated h1 sections, a heading-style figure caption, and an unordered list.
- The next default EPUB-family work is no longer annotation on this sample; it is a controlled chapter-scale pilot on the newly cleared sample.
