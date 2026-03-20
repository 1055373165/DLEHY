# 项目进度

## 项目信息
- 项目名称：PDF 高保真中译生产化
- 一句话目标：将当前项目的 PDF 英文书籍、英文论文翻译质量提升到生产级高保真交付水平，优先保证语义、结构、术语和段落连贯度。
- 创建时间：2026-03-20
- 最后更新：2026-03-20
- 协议版本：v2

## 全局指标
- 总阶段数：4
- 总 MDU 数：24
- 已完成 MDU：24
- 整体完成度：100%
- 最大拆解深度：3 层

## 阶段总览
| 阶段 | 状态 | MDU 数 | 已完成 | 完成度 |
|------|------|--------|--------|--------|
| 阶段 1：需求锁定与架构基线 | 已完成 | 2 | 2 | 100% |
| 阶段 2：翻译上下文与 prompt 强化 | 已完成 | 8 | 8 | 100% |
| 阶段 3：质量审查与回归闭环 | 已完成 | 3 | 3 | 100% |
| 阶段 4：真实样本验收与推广 | 已完成 | 11 | 11 | 100% |

## 详细任务清单
### 阶段 1：需求锁定与架构基线
#### 任务 1.1：锁定生产级高保真目标
- 状态：已完成
- 子任务：
  - [x] 明确质量目标优先于吞吐与 token 节省
  - [x] 明确 PDF 书籍与论文共用统一主链路
- 最小开发单元：
  - [x] MDU-1.1.1：读取 `auto-pilot.md` 并锁定执行框架 [依赖：无]
  - [x] MDU-1.1.2：将需求固化为“高保真 PDF 中译生产化”开发主线 [依赖：MDU-1.1.1]

### 阶段 2：翻译上下文与 prompt 强化
#### 任务 2.1：补 section/discourse 级运行时上下文
- 状态：已完成
- 子任务：
  - [x] 确认默认生产 prompt 继续使用 `role-style-v2`
  - [x] 为编译上下文增加 `section_brief`
  - [x] 为编译上下文增加 `discourse_bridge`
  - [x] 让默认 prompt 消费这些新信号
- 最小开发单元：
  - [x] MDU-2.1.1：确认“不直接替换默认 profile，而是增强默认上下文” [依赖：MDU-1.1.2]
  - [x] MDU-2.1.2：在运行时上下文中生成 `section_brief` [依赖：MDU-2.1.1]
  - [x] MDU-2.1.3：在运行时上下文中生成 `discourse_bridge` [依赖：MDU-2.1.2]
  - [x] MDU-2.1.4：将新上下文接入 `role-style-v2` / material-aware prompt [依赖：MDU-2.1.3]

#### 任务 2.2：保留可观测性与可实验性
- 状态：已完成
- 子任务：
  - [x] 保持 packet experiment 工位可观测
  - [x] 维持零 schema 迁移
- 最小开发单元：
  - [x] MDU-2.2.1：在实验工位暴露新增上下文来源 [依赖：MDU-2.1.4]

#### 任务 2.3：强化定向 rewrite / rerun guidance
- 状态：已完成
- 子任务：
  - [x] 让 `STYLE_DRIFT` issue 显式携带 `prompt_guidance`
  - [x] 让 rerun plan 注入更窄的 style guidance，而不只是一句 preferred hint
  - [x] 扩一条新的高信号 literalism 规则
- 最小开发单元：
  - [x] MDU-2.3.1：把 `style_drift.prompt_guidance` 写入 review issue evidence [依赖：MDU-3.1.1]
  - [x] MDU-2.3.2：把 `prompt_guidance` 桥接进 rerun hints [依赖：MDU-2.3.1]
  - [x] MDU-2.3.3：新增 `profound sense of responsibility` literalism rule [依赖：MDU-2.3.2]

### 阶段 3：质量审查与回归闭环
#### 任务 3.1：补测试与文档驾驶舱
- 状态：已完成
- 子任务：
  - [x] 回归测试覆盖新上下文编译
  - [x] 回归测试覆盖 prompt 消费
  - [x] 更新翻译质量驾驶舱
- 最小开发单元：
  - [x] MDU-3.1.1：新增 `context_compile` / `translator` 回归 [依赖：MDU-2.1.4]
  - [x] MDU-3.1.2：同步 `translation-quality-refactor-cockpit.md` [依赖：MDU-3.1.1]
  - [x] MDU-3.1.3：补充 root progress / ADR 更新 [依赖：MDU-3.1.2]

### 阶段 4：真实样本验收与推广
#### 任务 4.1：真实 packet 与小范围 rerun 验收
- 状态：已完成
- 子任务：
  - [x] 固定 packet dry-run 验证
  - [x] 必要时做单 packet execute / rerun
  - [x] 决定是否推广到正式默认链路
- 最小开发单元：
  - [x] MDU-4.1.1：对固定 packet 导出新 prompt 工件 [依赖：MDU-3.1.2]
  - [x] MDU-4.1.2：对高价值 packet 做小范围 execute 或 rerun 对照 [依赖：MDU-4.1.1]
  - [x] MDU-4.1.3：根据证据决定是否继续扩到更广样本 [依赖：MDU-4.1.2]

#### 任务 4.2：将 selective rollout 下沉到 chapter smoke 选样
- 状态：已完成
- 子任务：
  - [x] scan 工位暴露 unresolved packet issue 摘要
  - [x] chapter smoke 默认优先 mixed / non-style packet
  - [x] 保留 memory-first 回退开关，便于 A/B
- 最小开发单元：
  - [x] MDU-4.2.1：在 packet scan entries 中加入 issue priority 信号 [依赖：MDU-4.1.3]
  - [x] MDU-4.2.2：在 chapter smoke / CLI 中接入 selective rollout 选样策略 [依赖：MDU-4.2.1]

#### 任务 4.3：将 selective rollout 下沉到 workflow auto-followup 预算分配
- 状态：已完成
- 子任务：
  - [x] workflow auto-followup 候选排序暴露 packet issue priority 信号
  - [x] 在同 issue type 内优先 mixed / non-style packet
  - [x] 保持 `TERM_CONFLICT -> UNLOCKED_KEY_CONCEPT -> STYLE_DRIFT` 的原始语义顺序
- 最小开发单元：
  - [x] MDU-4.3.1：在 workflow candidate ranking 中接入 packet priority tier / non-style weight [依赖：MDU-4.2.2]
  - [x] MDU-4.3.2：补 workflow 级排序回归并同步驾驶舱 / ADR [依赖：MDU-4.3.1]

#### 任务 4.4：稳定 `UNLOCKED_KEY_CONCEPT` auto-lock 的 snapshot / session 行为
- 状态：已完成
- 子任务：
  - [x] 复现并隔离 mixed workflow 中的 `memory_snapshots` flush 冲突
  - [x] 修复 bootstrap/export repository 的 table probe 事务一致性
  - [x] 为 in-memory SQLite 补稳定连接池策略，并补 workflow/export 根因回归
- 最小开发单元：
  - [x] MDU-4.4.1：定位 `_document_images_table_available()` 绕开 session connection 导致的未提交状态漂移 [依赖：MDU-4.3.2]
  - [x] MDU-4.4.2：修复 bootstrap/export/session 层并恢复 `UNLOCKED_KEY_CONCEPT` workflow 回归 [依赖：MDU-4.4.1]

#### 任务 4.5：做真实章节 execute，验证最新 workflow/export 改动的实际收益
- 状态：已完成
- 子任务：
  - [x] 新增可复用的 real chapter followup smoke runner
  - [x] 在真实章节副本上完成 review auto-followup + chapter/document export 验收
- 最小开发单元：
  - [x] MDU-4.5.1：新增 `run_real_chapter_followup_smoke.py`，沉淀 cloned-DB 真实章节 followup/export 工位 [依赖：MDU-4.4.2]
  - [x] MDU-4.5.2：在真实章节 `d1ff...` 上执行 followup/export 并收集 before/after 证据 [依赖：MDU-4.5.1]

## 当前位置
- 当前阶段：已完成当前 autopilot slice
- 当前任务：等待下一轮真实章节 execute 扩样，优先补 `UNLOCKED_KEY_CONCEPT` 的 packet evidence / auto-followup 覆盖面
- 当前最小开发单元：无
- 整体完成度：100%

## 变更记录
| 时间 | 类型 | 描述 | 影响范围 |
|------|------|------|----------|
| 2026-03-20 | 初始化 | 建立 autopilot 进度面，锁定“PDF 高保真中译生产化”主线 | 根目录治理 |
| 2026-03-20 | 实现 | 运行时编译上下文已接入 `section_brief + discourse_bridge`，并正式进入 `role-style-v2` / material-aware prompt | 翻译主链路 |
| 2026-03-20 | 实现 | `STYLE_DRIFT` 已开始携带 `prompt_guidance`，rerun plan 会注入更窄的 style guidance，新增 `profound sense of responsibility` 直译腔规则 | review / rerun / prompt |
| 2026-03-20 | 验证 | 已完成 context/prompt/style-drift 定向回归与 lint，并同步驾驶舱与 ADR | 测试与项目治理 |
| 2026-03-20 | 验证 | 实验工位已支持 `review_issue_id -> rerun prompt` 还原，并在真实 packet `2e26...` 上完成 dry-run / execute 对照 | 实验工位与真实样本 |
| 2026-03-20 | 决策 | 已完成第二个真实 packet `b4c1...` 复验，收敛出“issue-driven rerun 继续保留，但只对 mixed/high-value packet 扩样，不做 blanket 推广” | 真实样本推广策略 |
| 2026-03-20 | 实现 | chapter smoke 默认已切到 selective rollout 选样：优先 mixed / non-style packet，同时保留 `--disable-issue-priority` 回退 | smoke 工位与推广策略 |
| 2026-03-20 | 实现 | workflow review auto-followup 预算已接入 selective rollout：保持 issue type 优先级不变，但在同类型内优先 mixed / non-style packet | workflow 级自动纠偏 |
| 2026-03-20 | 修复 | 已修复 `UNLOCKED_KEY_CONCEPT` auto-lock 的 snapshot 稳定性：bootstrap/export repository 的 document-image table probe 均改为走当前 session connection，并为 `:memory:` SQLite 补 `StaticPool` | workflow / export / bootstrap / 测试基础设施 |
| 2026-03-20 | 验证 | 已完成更广的 workflow/export 稳定性扩回归，确认事务内 schema probe 只剩 bootstrap/export 两处且均已切到 session connection；另发现 2 条 merged markdown 标题期望与当前标题翻译行为不一致的旁路失败 | workflow / export / merged markdown |
| 2026-03-20 | 验证 | 已在真实章节副本 `d1ff...` 上完成 review auto-followup + bilingual/review/merged export execute：open issues `12 -> 5`，`TERM_CONFLICT + STYLE_DRIFT` 已清空，导出成功，章节进入 `qa_checked` 且 `blocking_issue_count=0` | 真实章节验收 / workflow / export |
