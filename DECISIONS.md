# 架构决策记录

## ADR-001：生产级高保真优先于吞吐和 token 节省
- 状态：已决定
- 日期：2026-03-20
- 背景：当前项目已经具备 PDF 解析、翻译、review、rerun、export 主链路，但用户目标不是“能翻”，而是“生产级高保真交付”。
- 候选方案：
  - 保持当前策略，优先控制 prompt 长度和吞吐
  - 以交付质量为第一优先，允许适度增加上下文与提示复杂度
- 最终决定：质量优先。默认以语义保真、段落连贯、术语一致和结构可交付为第一目标，吞吐与 token 成本作为次级约束。
- 代价与妥协：prompt 与上下文编译可能更复杂，局部请求成本上升。
- 推翻条件：若新增上下文未带来可验证的真实 packet 改善，或明显损害稳定性/可重跑性。
- 影响范围：translation prompt、context compile、review 策略、packet experiment。
- 探针验证：已通过（来自现有驾驶舱证据与当前需求锁定）。

## ADR-002：默认生产 profile 继续保持 `role-style-v2`
- 状态：已决定
- 日期：2026-03-20
- 背景：代码库中已经存在 `role-style-v2`、`role-style-brief-v3`、`material-aware-v1` 等 profile，且历史实验已将 `role-style-v2` 提升为正式默认。
- 候选方案：
  - 直接切换默认 profile
  - 保持默认 profile 不变，先增强其可消费的上下文能力
- 最终决定：不直接切换默认 profile；先增强默认 `role-style-v2` 能消费的 section/discourse 上下文。
- 代价与妥协：改进速度更稳，但不会一次性吃到更激进 prompt profile 的潜在收益。
- 推翻条件：若固定 packet execute 证据证明其他 profile 在真实样本上稳定优于 `role-style-v2`。
- 影响范围：workers/translator、services/context_compile、packet experiment。
- 探针验证：已通过（现有驾驶舱明确 `role-style-v2` 是正式默认生产基线）。

## ADR-003：优先做 runtime-only 的 `section_brief + discourse_bridge`
- 状态：已验证（探针通过）
- 日期：2026-03-20
- 背景：当前 paragraph-led prompt 已能改善句序与局部术语问题，但仍缺 section-level 和 paragraph-to-paragraph 的显式桥梁，译文容易“句子都对，整段还不够顺”。
- 候选方案：
  - 直接引入数据库 schema 级新 memory 结构
  - 先在运行时编译阶段补最小 `section_brief + discourse_bridge`
- 最终决定：先做 runtime-only 版本，不改数据库 schema，把新增信号限制在 `context_compile -> prompt` 路径。
- 代价与妥协：第一版不会持久化完整 discourse state，仍以启发式为主。
- 推翻条件：若仅靠 runtime scaffolding 无法带来可验证改善，再评估持久化的 section/discourse memory。
- 影响范围：workers/contracts、services/context_compile、workers/translator、tests。
- 探针验证：已通过（`context_compile / prompt / packet experiment` 定向回归已补齐）。

## ADR-004：继续用共享窄规则增强 rerun，而不是膨胀默认 prompt
- 状态：已验证（探针通过）
- 日期：2026-03-20
- 背景：当前剩余质量问题越来越集中在少数高信号“翻译腔”表达，不适合继续把默认 prompt 越堆越长；更适合走 `STYLE_DRIFT -> review issue -> rerun hint` 的窄闭环。
- 候选方案：
  - 继续往默认 prompt 添加更通用、更长的风格约束
  - 把 `STYLE_DRIFT` 规则的 `prompt_guidance` 直接写入 issue evidence 与 rerun hints，只扩高命中规则
- 最终决定：默认 prompt 只保留高信号基础约束；更细的 rewrite 指令沿共享 `STYLE_DRIFT` 规则进入 review 和 rerun。新增规则时优先选择误报低、收益高的 literalism pattern。
- 代价与妥协：review/rerun 逻辑会更依赖规则质量，需要持续控制规则面和误报率。
- 推翻条件：若共享窄规则无法稳定改善真实 packet 输出，或者误报率明显升高，再重新评估是否要把更多 guidance 升回默认 prompt。
- 影响范围：services/style_drift、services/review、orchestrator/rerun、rerun workflow、tests。
- 探针验证：已通过（style-drift review/rerun 定向回归与 rule-engine 回归已通过）。

## ADR-005：真实 rerun 验收以 review issue 还原的实验 prompt 为准
- 状态：已验证（探针通过）
- 日期：2026-03-20
- 背景：过去 packet experiment 虽支持手工传 `rerun_hints`，但 operator 需要自己抄 issue 里的 hint，难以保证实验 prompt 与真实 rerun 状态机一致。
- 候选方案：
  - 继续手工拼 `rerun_hints`
  - 让实验工位直接接收 `review_issue_id`，自动解析 style hints 和 concept overrides
- 最终决定：以 review issue 作为 experiment workbench 的真实入口。`run_packet_experiment.py` 和 `PacketExperimentService` 现在都支持 `review_issue_id`，实验 prompt 会自动还原 review/rerun 闭环里的实际输入。
- 代价与妥协：实验工位与 review issue schema 的耦合更强，后续改 evidence 字段时要同步回归。
- 推翻条件：若 review issue schema 经常变化、导致实验工位维护成本过高，再考虑回退到更弱的手工 hint 模式。
- 影响范围：services/packet_experiment、scripts/run_packet_experiment.py、tests、真实 packet 验收流程。
- 探针验证：已通过（真实 packet `2e26...` 的 dry-run / execute 工件已能基于 5 个 live issues 还原 8 条 rerun hints 和 1 个 concept override）。

## ADR-006：issue-driven rerun 先做 selective rollout，不做 blanket 扩样
- 状态：已验证（探针通过）
- 日期：2026-03-20
- 背景：`2e26...` 这类 mixed issue packet 上，issue-driven rerun prompt 能更接近真实工作流，并带来明显更规整的输出；但在 `b4c1...` 这类轻量 style-only packet 上，当前默认链路本身已经能产出无 style-drift 命中的可接受结果。
- 候选方案：
  - 立刻把 issue-driven rerun 扩到所有存在 review issue 的 packet
  - 只对 mixed issue / high-value / 当前默认输出仍不稳定的 packet 继续扩样
- 最终决定：selective rollout。保留 issue-driven rerun workbench，并继续用于高价值 packet；但不对所有轻量 style-only packet 做 blanket rerun 或 blanket execute 扩样。
- 代价与妥协：推广速度更慢，需要 operator 先判断 packet 是否值得进入 issue-driven execute。
- 推翻条件：若后续更多样本显示轻量 style-only packet 同样能稳定从 issue-driven rerun 获得明显收益，再重新评估是否扩大默认适用面。
- 影响范围：真实 packet 验收策略、chapter smoke 选样策略、后续 workflow 自动纠偏边界。
- 探针验证：已通过（`2e26...` 与 `b4c1...` 两个真实 packet 的 dry-run / execute 对照已形成清晰分界）。

## ADR-007：chapter smoke 默认采用 issue-priority 选样，但保留 memory-first 回退
- 状态：已验证（探针通过）
- 日期：2026-03-20
- 背景：如果 selective rollout 只停留在人工挑 packet，chapter smoke 仍会优先选 memory signal 最高的 packet，无法把 mixed/high-value packet 提前拉进验收闭环。
- 候选方案：
  - chapter smoke 继续沿用 scan 的 memory-first 顺序
  - chapter smoke 默认按 issue priority 重排，但允许显式关闭
- 最终决定：默认按 issue priority 重排 chapter smoke 选样。排序优先级为 mixed/non-style unresolved issues，其次 unresolved issue count，再回落到 memory/concept signal。CLI 保留 `--disable-issue-priority`，方便 A/B 和回退。
- 代价与妥协：默认 smoke 不再等价于纯 memory-first 扫描结果，分析时需要区分 `scan top_candidate` 与 `selected_packet_ids`。
- 推翻条件：若真实章节里 issue-priority 频繁把 smoke 预算浪费在低收益 packet 上，再重新评估默认排序。
- 影响范围：services/packet_experiment_scan、services/translation_chapter_smoke、scripts/run_translation_chapter_smoke.py、chapter smoke 验收策略。
- 探针验证：已通过（真实章节 `d1ff...` 上，默认 issue-priority smoke 选中 `2e26...`，关闭后回到 memory-first 的 `21bc...`）。

## ADR-008：workflow auto-followup 先保留 issue type 语义，再在同类型内按 packet 价值分配预算
- 状态：已验证（探针通过）
- 日期：2026-03-20
- 背景：chapter smoke 已默认优先 mixed/non-style packet，但 workflow auto-followup 仍主要按 issue type 和 packet 命中数排序。这样会出现 style-only packet 仅因 issue 数更多，就抢走本该留给 mixed/high-value packet 的有限预算。
- 候选方案：
  - 直接把 workflow 排序改成 packet priority 优先，压过原来的 issue type 语义
  - 保留 `TERM_CONFLICT -> UNLOCKED_KEY_CONCEPT -> STYLE_DRIFT` 的 issue type 顺序，只在同类型内部再按 mixed/non-style packet 优先
- 最终决定：采用“issue type first, packet value second”。workflow auto-followup 继续先看 blocking 和 issue type；当候选属于同一 issue type 时，再优先 mixed/non-style packet，并参考 non-style issue weight / total issue weight 分配预算。
- 代价与妥协：排序逻辑更复杂，workflow 和 smoke 不再是完全同一套 key，但可以避免 `UNLOCKED_KEY_CONCEPT` 或 `STYLE_DRIFT` 因 packet 信号过强而越级抢到 `TERM_CONFLICT` 前面。
- 推翻条件：若后续真实章节 execute 表明 workflow 预算仍频繁花在低收益 packet 上，或者 mixed packet 的修复顺序仍不理想，再重新评估是否把 packet priority 提前到 issue type 之前。
- 影响范围：services/workflows.py、review auto-followup 回归、workflow 级预算分配策略。
- 探针验证：已通过（workflow 定向回归证明：同类型 `STYLE_DRIFT` 候选里，mixed packet 会先于 style-only 大包；同时真实 mixed review 工件仍保持 `TERM_CONFLICT` 候选排在 `STYLE_DRIFT` 前面）。

## ADR-009：workflow/export 事务内的能力探测必须统一走当前 session connection
- 状态：已验证（探针通过）
- 日期：2026-03-20
- 背景：`UNLOCKED_KEY_CONCEPT` auto-lock 在 mixed workflow 里出现 `memory_snapshots` 的 `StaleDataError`。根因不是 lock/rerun 逻辑本身，而是 workflow/export 事务中的 document-image table probe 使用 engine 级 `inspect(bind).has_table(...)`，在未提交事务中绕开了当前 session connection，导致 chapter memory snapshot 与 term lock 视图漂移。
- 候选方案：
  - 保持 engine 级 table probe，用更多 `flush/expire` 去补救 identity / transaction 状态
  - 把能力探测改成走当前 `session.connection()`，让 schema probe 与 review/lock/rerun/export 共用同一事务视图；同时为 `:memory:` SQLite 补 `StaticPool`
- 最终决定：走 session-scoped connection。bootstrap/export repository 的 table probe 现在都直接 inspect 当前 session connection；测试环境的 `:memory:` SQLite 额外使用 `StaticPool`，避免连接漂移放大事务不一致。仍保留 API backfill 路由中的 `session.get_bind()`，因为那里只是提取 database URL 后关闭 session，不参与事务内读写。
- 代价与妥协：repository 的 schema probe 会更早地绑定事务连接；如果未来需要在无事务上下文里做懒探测，要继续沿 session connection 语义实现。
- 推翻条件：若未来切到完全不同的数据库后端并发现 session-level inspect 带来新的兼容问题，再评估是否抽象单独的 schema capability layer。
- 影响范围：infra/repositories/bootstrap.py、infra/repositories/export.py、infra/db/session.py、workflow/review/export 集成回归、测试基础设施。
- 探针验证：已通过（document-image table probe 不再冲掉未提交的 concept lock；`UNLOCKED_KEY_CONCEPT` 与 mixed workflow 回归恢复通过；export 侧同类 probe 也已补根因回归；更广 workflow/export 检索确认剩余 `session.get_bind()` 仅在 API history backfill 路由中用于提取 database URL，不参与事务内读写）。

## ADR-010：真实章节 followup 验收默认在克隆 DB 上做 same-session review/export smoke
- 状态：已验证（探针通过）
- 日期：2026-03-20
- 背景：仅靠 packet experiment 能验证 prompt 和 rerun 局部收益，但不足以证明最新 workflow/export 修复在真实章节上真正可交付。直接在主数据库上做 live followup 虽然最快，却会污染现有基线，增加后续比对成本。
- 候选方案：
  - 继续只做 packet execute，不验证 review/export 同 session 链路
  - 直接在主数据库上跑真实章节 review auto-followup + export
  - 每次先复制当前 DB，再在副本上执行同一 session 内的 review auto-followup、chapter export 和 merged export
- 最终决定：采用 cloned-DB smoke。新增 `scripts/run_real_chapter_followup_smoke.py`，默认在数据库副本上跑真实章节 followup/export，并把 before/after issue 计数、auto-followup executions、rerun 样本译文和 export 路径固化成 JSON 报告。
- 代价与妥协：需要维护额外脚本和 artifact 目录；报告反映的是“副本世界”的真实结果，而不是主数据库即时状态。
- 推翻条件：若后续接入更正式的 durable run-control 工位，能够对主库操作自动快照/回放，再评估是否收敛到统一 runner。
- 影响范围：scripts/run_real_chapter_followup_smoke.py、artifacts/real-book-live/* followup smoke、真实章节验收流程。
- 探针验证：已通过（真实章节 `d1ff...` 在副本上完成 `review auto-followup + review package + bilingual_html + merged_markdown`；open issues 从 `12` 降到 `5`，`TERM_CONFLICT` 与 `STYLE_DRIFT` 清零，`blocking_issue_count=0`）。
