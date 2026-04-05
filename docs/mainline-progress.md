# Mainline Progress

Last Updated: 2026-04-05 00:58 +0800
Status: translate-agent-readiness-mainline
Rule: 先用 benchmark 和最小 probe 扩大可信边界，再决定是否扩大整本运行范围。

## 1. 当前主线定义

当前真正的主线不是继续推进 runtime self-heal，也不是旧的 canonical-IR foundation 漂移线。

当前主线是：

1. 让 translate agent 在 `PDF 书籍 / EPUB 书籍 / PDF 论文` 上具备可证明的高保真翻译 readiness。
2. 用 benchmark 而不是主观感觉决定“是否可以开始更大范围的整本运行”。
3. 在整本运行阶段默认使用 `slice-first`，而不是直接 blind full-document rollout。
4. 在测试阶段把最大翻译测试单元锁定为“章节”或等价章节切片，不做整书测试。
5. 在 Codex hooks 可用时，用 `Stop` hook 强制执行 Forge v2 stop legality，而不是只靠 prompt 约束。

> 当前主线 = `translate-agent 高保真翻译 readiness` + `benchmark-backed whole-document go/no-go` + `保守扩圈`

## 2. 已完成的主线能力

### 2.1 Current certification

当前 benchmark 结论已经是：

- `L1` `EPUB-reflowable-tech-book` -> `go`
- `L2` `PDF-text-tech-book` -> `go`
- `L3` `PDF-text-academic-paper` -> `go`
- `L6` `High-artifact-density-paper` -> `go`
- `overall` -> `go`
- Forge v2 `Stop` hook guard -> `installed in repo and mirrored into the legacy Codex-home auto-commit Stop path`
- `epub-agentic-theories-001` -> `go`
- `epub-managing-memory-001` -> `go`

### 2.2 Pilot and expansion proof

当前主线已经不只停留在 readiness current set：

- certified-lane slice-first pilots 已跑过首轮真实产品路径
- expansion wave 1 已把 `L2` 和 `L5` widen 到 measured `go`

对应权威产物：

- `/Users/smy/project/book-agent/artifacts/review/translate-agent-benchmark-execution-summary-current.json`
- `/Users/smy/project/book-agent/artifacts/review/translate-agent-benchmark-scorecard-current.json`
- `/Users/smy/project/book-agent/artifacts/review/translate-agent-lane-verdicts-current.json`
- `/Users/smy/project/book-agent/artifacts/review/translate-agent-pilot-summary-current.json`
- `/Users/smy/project/book-agent/artifacts/review/translate-agent-benchmark-expansion-wave1-execution-summary.json`
- `/Users/smy/project/book-agent/artifacts/review/translate-agent-benchmark-expansion-wave1-lane-verdicts.json`

## 3. 当前最关键的重排

用户优先指定的两份论文样本已经都收成 widened `L3` evidence：

1. `pdf-attention-single-column-002`
   - `/Users/smy/Downloads/NIPS-2017-attention-is-all-you-need-Paper (1).pdf`
   - 结果：measured `go`
2. `pdf-raft-atc14-001`
   - `/Users/smy/Downloads/raft-atc14.pdf`
   - 结果：measured `go`
   - 关键修复：第二页 title-page 论文识别 + `9 Related work` heading 恢复 + caption linkage 评分口径修正

当前 top-of-stack 已经切到新的 EPUB family 样本：

1. `epub-agentic-theories-001`
   - 结果：measured `go`
2. `epub-managing-memory-001`
   - 结果：measured `go`
   - 覆盖：repeated `h1` sections、heading-style figure caption、archive-backed figure、unordered list

下一刀不再是 annotation，而是对 `epub-managing-memory-001` 做受控的章节级 slice-first pilot。
当前这个 pilot 已经对准 `OEBPS/ch05.html`，并且已经完整收口：
- `report.json`：第一刀，推进到 `8/31`
- `report-slice2.json`：第二刀，推进到 `16/31`
- `report-slice3.json`：第三刀，推进到 `24/31`
- `report-slice4.json`：最后一刀，收口到 `31/31`
- `review_required = 0`
- `review.total_issue_count = 0`
- review package 和 bilingual export 都已落地
- 章节 smoke 的控制面也已经修复成“续跑下一组 `BUILT` packets”，不会再出现第二刀只跳过第一刀窗口的假 continuation
- 底层翻译模型默认值也已从 DeepSeek 切换到 OpenRouter free Qwen：继续走 `openai_compatible` 适配层，但模型串改成 `qwen/qwen3.6-plus:free`
- 这条 OpenRouter free 路线已经通过一条极小的在线结构化探针，不是纯静态切换
- 当前 `.env` 里的旧单一 USD 成本系数继续保持移除状态，避免在 free 路线下继续产出错误的 `cost_usd` 估算
- 新 provider 的第一条真实章节级 live pilot 已经起在 `epub-agentic-theories-001` Chapter 12
- 前两刀合计 `16` 个 packets、`review_required = 0`
- 但 latency profile 明显偏大：平均约 `70s`，峰值约 `123s`
- 所以当前结论不是“OpenRouter free 不可用”，而是“可用但慢”，下一步继续观察连续 slice 是否仍然稳定

## 4. 下一阶段 Todo

### P0

- 保留两份用户指定论文都并入 widened `L3` paper-variance success truth
- 保留 `pdf-man-solved-market-zh-001` 和 `pdf-self-observation-zh-001` 作为 measured `L4` success truth
- 保留 `epub-agentic-theories-001` 和 `epub-managing-memory-001` 作为 widened `L1` evidence
- 把 `epub-managing-memory-001` chapter 5 记录为已完成的 chapter-scale live-pilot checkpoint
- 默认切到下一份 EPUB-family live pilot，而不是继续重复消耗同一已完成章节
- 测试阶段的 token spend 上限保持在章节级，不把整书跑测试当作默认验证手段
- 把最新 measured 结果继续写回 expansion draft 和 `.forge` truth
- 保持章节级 pilot 的续跑语义正确：同章 rerun 必须接下一组 `BUILT` packets
- 把 chapter-complete checkpoint 继续并回 pilot ledger，再决定下一个已清 lane 的 live pilot 目标

### 新增 measured 结果

- `pdf-man-solved-market-zh-001` 已经通过 bounded slice-scoped OCR/parser/export probe
- 当前结论不是“OCR runtime 不可用”，而是：
  - bounded OCR 可在限制时间内完成
  - scanned page image 会被保留成 `image/protect`
- asset probe 对 3/3 scoped full-page scans 命中 `pdf_original_image`
- 所以下一步不是再重跑第一个 `L4`，而是切到第二个 OCR-heavy 样本

### 再新增 measured 结果

- `pdf-self-observation-zh-001` 也已经通过 bounded slice-scoped OCR/parser/export probe
- 现在 `L4` 已经有两份 measured `go` 样本：
  - `pdf-man-solved-market-zh-001`
  - `pdf-self-observation-zh-001`
- 这意味着下一步默认不再继续堆 OCR-heavy，而是切回 EPUB family 扩圈
- 与此同时，非法停机控制已上移到 Hook 层，避免 tidy update 直接结束回合
- 第一份回到 EPUB family 的扩圈样本 `epub-agentic-theories-001` 已经测成 `go`，第二份紧随其后的 compact EPUB 样本 `epub-managing-memory-001` 也已经测成 `go`
- 所以下一步不再继续给 `epub-managing-memory-001` 做 annotation，而是切到它的章节级 slice-first pilot
- 与此同时，Hook 层 stop legality 已从“包含 review 子串即可停”收紧成显式白名单边界

### P1

- 如果 `L4` 首样本顺利，扩大 OCR-heavy lane 证据
- 如果出现 measured blocker，再转向 parser/export hardening
- 之后再回到 `L4` OCR-heavy 或更广的 EPUB family expansion
