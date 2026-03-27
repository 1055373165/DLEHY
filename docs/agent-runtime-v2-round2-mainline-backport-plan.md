# AI Agent Runtime V2 Round 2 回迁主仓库清单与提交计划

Last Updated: 2026-03-27
Source Workspace: `/tmp/book-agent-agent-runtime-v2.pUOyOf`
Source Runtime State: `.forge/STATE.md` => `current_step: complete`, `completed_items: 18/18`
Scope: round-2 only

## 1. 目的

这份文档只回答一件事：

如何把隔离副本里 round-2 的有效产出，安全迁回主仓库，而不把 `.forge` 运行状态、开发框架改造、隔离副本噪音或其他实验性漂移一起带回来。

关键原则：

1. 只回迁 round-2 已验收通过的 Runtime V2 自愈矩阵增量。
2. 不按整个 worktree 全量迁移，不按 `git status` 粗暴复制。
3. 只信任 `.forge/reports/batch-*.md`、`.forge/log.md` 和最终 `.forge/STATE.md`。
4. 热点文件一律按 hunk 回迁，不整文件覆盖主仓库。
5. 本文默认 round-1 已按源工作区里的 [agent-runtime-v2-mainline-backport-plan.md](/tmp/book-agent-agent-runtime-v2.pUOyOf/docs/agent-runtime-v2-mainline-backport-plan.md) 回迁；如果 round-1 还没落主线，先做 round-1。

## 2. 本轮已验证范围

round-2 已完成并验收通过的范围：

1. `ReviewSession` 资源化与 controller scaffold 补强
2. packet/review `lane health` 与统一 `recovery matrix`
3. review deadlock incidentization 与 bounded replay
4. packet repeated failure -> `chapter_hold` 边界
5. runtime bundle rollback governance
6. executor / run-control 上的 stable revision rebinding
7. `REQ-MX-01` ~ `REQ-MX-04` acceptance coverage

最终完成态证据：

- source state: `/tmp/book-agent-agent-runtime-v2.pUOyOf/.forge/STATE.md`
- source log: `/tmp/book-agent-agent-runtime-v2.pUOyOf/.forge/log.md`
- batch reports: `/tmp/book-agent-agent-runtime-v2.pUOyOf/.forge/reports/batch-1-report.md` 到 `/tmp/book-agent-agent-runtime-v2.pUOyOf/.forge/reports/batch-12-report.md`

关键结果：

1. Phase 2 checkpoint regression 已修复，`tests/test_app_runtime.py` 不再假设 chapter scope 只有单一 checkpoint。
2. `REQ-MX-01` review deadlock self-heal 已绿。
3. `REQ-MX-02` chapter-hold escalation boundary 已绿。
4. `REQ-MX-03` bad bundle rollout auto-rollback 已绿。
5. `REQ-MX-04` unified recovery matrix contract coverage 已绿。
6. 旧竖切 `REQ-EX-02` 仍保持绿色，没有被 round-2 打坏。

## 3. 回迁策略

推荐迁移方式不是直接 cherry-pick 整个隔离副本，而是按下面 6 组 commit 做“白名单回迁”：

1. `ReviewSession` runtime resource 与 checkpoint/test repair
2. `lane health + recovery matrix`
3. review-deadlock incident + minimal replay
4. chapter-level hold / escalation
5. bundle governance + rollback rebinding
6. acceptance closure

这样切分的原因：

1. 资源层、策略层、controller 语义层、bundle 治理层是天然边界。
2. 主仓库 review 时可以逐组确认，不需要一次吃下整个 round-2。
3. 任一组冲突或行为回归时，更容易局部回滚。

## 4. 必须回迁的文件

### 4.1 Safe full-file add

这些文件是 round-2 新引入的能力面，建议整文件迁移：

- `alembic/versions/20260327_0013_review_sessions.py`
- `alembic/versions/20260327_0014_runtime_bundle_rollback_lineage.py`
- `src/book_agent/app/runtime/controllers/review_controller.py`
- `src/book_agent/services/runtime_lane_health.py`
- `src/book_agent/services/recovery_matrix.py`
- `src/book_agent/services/bundle_guard.py`
- `tests/test_runtime_lane_health.py`
- `tests/test_recovery_matrix.py`
- `tests/test_bundle_guard.py`
- `tests/test_req_mx_01_review_deadlock_self_heal.py`
- `tests/test_req_mx_02_chapter_hold_escalation.py`
- `tests/test_req_mx_03_bundle_rollback.py`
- `tests/test_req_mx_04_recovery_matrix.py`

### 4.2 Selective hunk port

这些文件是主线热点文件，或者本身已经承接了 round-1 语义。回迁时只迁 round-2 相关 hunk：

- `src/book_agent/domain/enums.py`
- `src/book_agent/domain/models/ops.py`
- `src/book_agent/infra/repositories/runtime_resources.py`
- `src/book_agent/app/runtime/controller_runner.py`
- `src/book_agent/app/runtime/controllers/chapter_controller.py`
- `src/book_agent/app/runtime/controllers/packet_controller.py`
- `src/book_agent/app/runtime/controllers/run_controller.py`
- `src/book_agent/app/runtime/controllers/incident_controller.py`
- `src/book_agent/app/runtime/document_run_executor.py`
- `src/book_agent/services/run_execution.py`
- `src/book_agent/services/run_control.py`
- `src/book_agent/services/incident_triage.py`
- `src/book_agent/services/runtime_bundle.py`
- `src/book_agent/services/runtime_patch_validation.py`
- `tests/test_review_sessions.py`
- `tests/test_runtime_resources.py`
- `tests/test_runtime_resources_repository.py`
- `tests/test_app_runtime.py`
- `tests/test_incident_triage.py`
- `tests/test_runtime_v2_enums.py`
- `tests/test_incident_controller.py`
- `tests/test_runtime_bundle.py`
- `tests/test_runtime_incidents_bundles.py`
- `tests/test_run_execution.py`
- `tests/test_run_control_api.py`

### 4.3 Verification-only dependencies

这些文件不一定有新的 round-2 代码 diff，但回迁验证必须纳入：

- `tests/test_req_ex_02_export_misrouting_self_heal.py`

### 4.4 文档类建议回迁

建议顺手回迁的文档：

- `docs/agent-runtime-v2-round2-mainline-backport-plan.md`
- 如需保留隔离副本上下文，可额外参考：
  - `/tmp/book-agent-agent-runtime-v2.pUOyOf/docs/agent-runtime-v2-round2-autopilot-handoff.md`
  - `/tmp/book-agent-agent-runtime-v2.pUOyOf/docs/agent-runtime-v2-round2-requirement-seed.md`

## 5. 明确不要回迁的内容

以下内容不要从隔离副本带回主仓库：

1. `.forge/**`
2. `.autopilot/**`
3. `forge/**` 或旧 `autopilot/**` 在隔离副本里的运行快照
4. `.forge/reports/*.md`、`.forge/batches/*.md`、`.forge/log.md`、`.forge/imports/**`
5. 这轮开发框架自己的监督逻辑与状态文件
6. 隔离副本里所有与 round-2 Runtime V2 无关的 parser/pdf/ocr 漂移

如果主仓库准备单独采纳 `forge supervisor` 框架，那是另一条开发主线，不要和本次 Runtime V2 回迁混在一起。

## 6. 推荐 commit 切分

### Commit 1

标题：

`feat(runtime-v2): add review session runtime resource and generation-bound reconciliation`

包含：

- `alembic/versions/20260327_0013_review_sessions.py`
- `src/book_agent/domain/enums.py`
- `src/book_agent/domain/models/ops.py`
- `src/book_agent/infra/repositories/runtime_resources.py`
- `src/book_agent/app/runtime/controllers/review_controller.py`
- `src/book_agent/app/runtime/controllers/chapter_controller.py`
- `src/book_agent/app/runtime/controller_runner.py`
- `tests/test_review_sessions.py`
- `tests/test_runtime_resources.py`
- `tests/test_runtime_resources_repository.py`
- `tests/test_app_runtime.py`

目标：

1. 把 `ReviewSession` 作为一等 runtime resource 落回主仓库。
2. 让 `ChapterController` / `controller_runner` 保证每个 chapter generation 只有一个 active review session。
3. 一并回迁 checkpoint multiplicity 的测试修复：
   - `tests/test_app_runtime.py` 不再使用“chapter scope 只有一条 checkpoint”的过时假设。

### Commit 2

标题：

`feat(runtime-v2): add lane health and unified recovery matrix`

包含：

- `src/book_agent/services/runtime_lane_health.py`
- `src/book_agent/services/recovery_matrix.py`
- `src/book_agent/app/runtime/controllers/packet_controller.py`
- `src/book_agent/app/runtime/controllers/review_controller.py`
- `src/book_agent/app/runtime/controllers/run_controller.py`
- `src/book_agent/infra/repositories/runtime_resources.py`
- `tests/test_runtime_lane_health.py`
- `tests/test_recovery_matrix.py`
- `tests/test_runtime_resources.py`
- `tests/test_runtime_resources_repository.py`
- `tests/test_review_sessions.py`

目标：

1. 把 packet/review 的 starvation / deadlock / healthy terminal closure 统一成显式策略输出。
2. 把 `translate/review/export/ops` 的 default action、retry cap、incident threshold、scope boundary 固化成 `RecoveryMatrixService`。
3. 让 controller 只投影和持久化结构化结果，不继续堆 ad-hoc heuristics。

### Commit 3

标题：

`feat(runtime-v2): add review-deadlock incident classification and bounded replay`

包含：

- `src/book_agent/domain/enums.py`
- `src/book_agent/services/incident_triage.py`
- `src/book_agent/app/runtime/controllers/incident_controller.py`
- `src/book_agent/app/runtime/controllers/review_controller.py`
- `src/book_agent/app/runtime/document_run_executor.py`
- `src/book_agent/services/run_execution.py`
- `tests/test_incident_triage.py`
- `tests/test_runtime_v2_enums.py`
- `tests/test_incident_controller.py`
- `tests/test_req_mx_01_review_deadlock_self_heal.py`

目标：

1. 把 review deadlock 与 packet runtime fingerprint 纳入统一 incident family。
2. 让 review deadlock 走 incident -> bounded repair -> minimal replay，而不是无限等待 review 终态。
3. 锁住 `REQ-MX-01` acceptance。

### Commit 4

标题：

`feat(runtime-v2): add chapter-boundary escalation after packet repair exhaustion`

包含：

- `src/book_agent/domain/models/ops.py`
- `src/book_agent/services/recovery_matrix.py`
- `src/book_agent/app/runtime/controllers/chapter_controller.py`
- `src/book_agent/app/runtime/controllers/packet_controller.py`
- `tests/test_req_mx_02_chapter_hold_escalation.py`

目标：

1. 当 packet-level repair exhaustion 达上限时，升级到显式 `chapter_hold`。
2. 记录 `repair_exhausted`、`scope_boundary`、`affected_packet_ids`、`fingerprint_occurrences` 等控制面事实。
3. 明确拒绝自动扩大到 document 级。
4. 锁住 `REQ-MX-02` acceptance。

### Commit 5

标题：

`feat(runtime-v2): add bundle rollback governance and stable revision rebinding`

包含：

- `alembic/versions/20260327_0014_runtime_bundle_rollback_lineage.py`
- `src/book_agent/domain/models/ops.py`
- `src/book_agent/services/runtime_bundle.py`
- `src/book_agent/services/bundle_guard.py`
- `src/book_agent/services/runtime_patch_validation.py`
- `src/book_agent/app/runtime/controllers/incident_controller.py`
- `src/book_agent/app/runtime/document_run_executor.py`
- `src/book_agent/services/run_control.py`
- `tests/test_runtime_bundle.py`
- `tests/test_runtime_incidents_bundles.py`
- `tests/test_bundle_guard.py`
- `tests/test_runtime_patch_validation.py`
- `tests/test_incident_controller.py`
- `tests/test_run_execution.py`
- `tests/test_run_control_api.py`

目标：

1. 在 `runtime_bundle_revisions` 上补 `canary_verdict`、`freeze_reason`、`rollback_target_revision_id`、`rolled_back_at` 等治理字段。
2. 引入 `BundleGuardService`，把 failed canary 的 freeze / rollback / stable rebind 做成 controller-owned 逻辑。
3. 在 executor / run-control 上显式区分：
   - `published_bundle_revision_id`
   - `active_runtime_bundle_revision_id`
   - `recovered_lineage`
4. 保证回滚之后 replay scope 真的绑定回稳定 revision，而不是只在 incident 层口头说回滚。

### Commit 6

标题：

`test(runtime-v2): close acceptance coverage for bundle rollback and recovery matrix`

包含：

- `tests/test_req_mx_03_bundle_rollback.py`
- `tests/test_req_mx_04_recovery_matrix.py`
- `tests/test_req_ex_02_export_misrouting_self_heal.py`

目标：

1. 锁住 `REQ-MX-03`：
   - bad bundle publish
   - canary fail
   - freeze
   - rollback
   - stable rebind
   - lineage auditable
2. 锁住 `REQ-MX-04`：
   - translation content
   - review verdict
   - review deadlock
   - export defect
   - ops failure
   - unknown-family rejection
3. 复验旧竖切 `REQ-EX-02` 没被 round-2 回归打坏。

## 7. 推荐验证顺序

### Verify 1: ReviewSession / checkpoint repair

```bash
.venv/bin/python -m pytest \
  tests/test_review_sessions.py \
  tests/test_runtime_resources.py \
  tests/test_runtime_resources_repository.py \
  tests/test_app_runtime.py
```

期望：

- `ReviewSession` schema / repository / controller 绿色
- `test_app_runtime.py` 不再因 chapter checkpoint multiplicity 假设失败

### Verify 2: lane health + recovery matrix

```bash
.venv/bin/python -m pytest \
  tests/test_runtime_lane_health.py \
  tests/test_recovery_matrix.py \
  tests/test_runtime_resources.py \
  tests/test_runtime_resources_repository.py \
  tests/test_review_sessions.py
```

### Verify 3: review-deadlock self-heal + chapter hold

```bash
.venv/bin/python -m pytest \
  tests/test_incident_triage.py \
  tests/test_incident_controller.py \
  tests/test_runtime_v2_enums.py \
  tests/test_run_execution.py \
  tests/test_req_mx_01_review_deadlock_self_heal.py \
  tests/test_req_mx_02_chapter_hold_escalation.py
```

### Verify 4: bundle governance + stable rebinding

```bash
.venv/bin/python -m pytest \
  tests/test_runtime_bundle.py \
  tests/test_runtime_incidents_bundles.py \
  tests/test_bundle_guard.py \
  tests/test_runtime_patch_validation.py \
  tests/test_incident_controller.py \
  tests/test_run_execution.py \
  tests/test_run_control_api.py
```

### Verify 5: acceptance closure

```bash
.venv/bin/python -m pytest \
  tests/test_req_mx_03_bundle_rollback.py \
  tests/test_req_mx_04_recovery_matrix.py \
  tests/test_req_ex_02_export_misrouting_self_heal.py
```

## 8. 回迁时的注意事项

1. `src/book_agent/domain/models/ops.py` 是 round-1 与 round-2 的共同热点，必须按 hunk 回迁，避免覆盖 round-1 已在主仓库吸收的 schema 语义。
2. `src/book_agent/app/runtime/document_run_executor.py` 在主仓库也是热点文件，只迁 round-2 的 review-deadlock replay 和 rollback rebinding hunk。
3. `src/book_agent/services/run_control.py` 只迁 `active_runtime_bundle_revision_id`、`recovered_lineage`、`last_export_route_recovery.active_bundle_revision_id` 等 summary 正规化逻辑。
4. `tests/test_app_runtime.py` 的 checkpoint 修复不是“顺手改测试”，而是 round-2 的必要回归修复；如果漏掉，主仓库 phase-checkpoint 验证会被旧假设卡住。
5. `.forge/**` 里的 report/log/state 只作为证据，不是要落主仓库的产物。

## 9. 一句话总结

round-2 回迁的核心不是“多加几条测试”，而是把 Runtime V2 从 `REQ-EX-02` 单点 export 自愈，扩成一个覆盖 review deadlock、packet exhaustion、chapter-boundary escalation、bundle rollback、stable-revision rebinding 的更完整自愈矩阵，并且继续保留显式状态、版本约束、最小 replay scope 和可审计 lineage。 
