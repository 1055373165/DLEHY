# AI Agent Runtime V2 Round 2 回迁执行版

Last Updated: 2026-03-27
Target Repo: `/Users/smy/project/book-agent`
Source Repo: `/tmp/book-agent-agent-runtime-v2.pUOyOf`
Companion Plan: [agent-runtime-v2-round2-mainline-backport-plan.md](/Users/smy/project/book-agent/docs/agent-runtime-v2-round2-mainline-backport-plan.md)

## 1. 当前预检结论

截至 2026-03-27，这个主仓库还不适合直接执行 round-2 backport，原因有两个：

### 1.1 当前工作树不是干净状态

当前主仓库存在本轮无关改动：

- `autopilot/**` 删除
- `src/book_agent/app/runtime/document_run_executor.py` 已修改
- `src/book_agent/cli.py` 已修改
- `tests/test_run_execution.py` 已修改
- `.autopilot/**`、`forge/**`、`src/book_agent/tools/forge_*` 等未跟踪文件

结论：

- 不要在当前工作树上直接拷贝或打 patch。
- 推荐先新建一个干净 worktree 或新分支来做回迁。

### 1.2 round-1 基线尚未完整落主仓库

实际预检结果显示，round-2 依赖的多个 round-1 文件在主仓库中仍然缺失：

- `src/book_agent/infra/repositories/runtime_resources.py`
- `src/book_agent/app/runtime/controllers/chapter_controller.py`
- `src/book_agent/app/runtime/controllers/packet_controller.py`
- `src/book_agent/app/runtime/controllers/run_controller.py`
- `src/book_agent/app/runtime/controllers/incident_controller.py`
- `src/book_agent/services/incident_triage.py`
- `src/book_agent/services/runtime_bundle.py`
- `src/book_agent/services/runtime_patch_validation.py`
- `tests/test_review_sessions.py`
- `tests/test_runtime_resources.py`
- `tests/test_runtime_resources_repository.py`
- `tests/test_incident_triage.py`
- `tests/test_runtime_v2_enums.py`
- `tests/test_incident_controller.py`
- `tests/test_runtime_bundle.py`
- `tests/test_runtime_incidents_bundles.py`
- `tests/test_req_ex_02_export_misrouting_self_heal.py`

结论：

- round-2 不能脱离 round-1 单独回迁。
- 实际执行顺序必须是：
  1. 先落 round-1
  2. 再落 round-2

round-1 源计划在：

- [agent-runtime-v2-mainline-backport-plan.md](/tmp/book-agent-agent-runtime-v2.pUOyOf/docs/agent-runtime-v2-mainline-backport-plan.md)

## 2. 推荐执行方式

### 2.1 推荐在新 worktree 中执行

建议先开一个干净 worktree：

```bash
git worktree add /tmp/book-agent-runtime-v2-backport -b codex/runtime-v2-mainline-backport
cd /tmp/book-agent-runtime-v2-backport
```

原因：

1. 不污染当前主仓库里正在进行的 `forge` / supervisor 改动。
2. 便于 round-1 和 round-2 按顺序回迁。
3. 便于冲突时直接丢弃整个 backport worktree。

### 2.2 执行原则

1. `whole-file add` 用复制。
2. 热点文件一律用 hunk patch。
3. 每一组 commit 做完后立刻跑本组验证，不等全部回迁完再统一跑。
4. `tests/test_req_ex_02_export_misrouting_self_heal.py` 是保护回归，必须在 round-2 尾声复验。

## 3. 实际执行顺序

### Step 0: 先完成 round-1 回迁

先按源计划完成 round-1：

- [agent-runtime-v2-mainline-backport-plan.md](/tmp/book-agent-agent-runtime-v2.pUOyOf/docs/agent-runtime-v2-mainline-backport-plan.md)

只有当下面这些文件在目标仓库中都已存在时，才进入 round-2：

- `src/book_agent/infra/repositories/runtime_resources.py`
- `src/book_agent/app/runtime/controllers/chapter_controller.py`
- `src/book_agent/app/runtime/controllers/packet_controller.py`
- `src/book_agent/app/runtime/controllers/run_controller.py`
- `src/book_agent/app/runtime/controllers/incident_controller.py`
- `src/book_agent/services/incident_triage.py`
- `src/book_agent/services/runtime_bundle.py`
- `src/book_agent/services/runtime_patch_validation.py`
- `tests/test_review_sessions.py`
- `tests/test_runtime_resources.py`
- `tests/test_runtime_resources_repository.py`
- `tests/test_incident_triage.py`
- `tests/test_runtime_v2_enums.py`
- `tests/test_incident_controller.py`
- `tests/test_runtime_bundle.py`
- `tests/test_runtime_incidents_bundles.py`
- `tests/test_req_ex_02_export_misrouting_self_heal.py`

### Step 1: Round-2 Commit 1

目标：

- `ReviewSession` resource
- `controller_runner` / `ChapterController` generation-bound review session ensure
- `tests/test_app_runtime.py` checkpoint multiplicity 修复

#### 1.1 整文件复制

```bash
mkdir -p alembic/versions src/book_agent/app/runtime/controllers tests
cp /tmp/book-agent-agent-runtime-v2.pUOyOf/alembic/versions/20260327_0013_review_sessions.py alembic/versions/
cp /tmp/book-agent-agent-runtime-v2.pUOyOf/src/book_agent/app/runtime/controllers/review_controller.py src/book_agent/app/runtime/controllers/
```

#### 1.2 hunk patch 文件

按文件逐个生成 patch：

```bash
mkdir -p /tmp/round2-backport-patches/commit1
git diff --no-index -- src/book_agent/domain/enums.py /tmp/book-agent-agent-runtime-v2.pUOyOf/src/book_agent/domain/enums.py > /tmp/round2-backport-patches/commit1/domain_enums.patch || true
git diff --no-index -- src/book_agent/domain/models/ops.py /tmp/book-agent-agent-runtime-v2.pUOyOf/src/book_agent/domain/models/ops.py > /tmp/round2-backport-patches/commit1/domain_models_ops.patch || true
git diff --no-index -- src/book_agent/infra/repositories/runtime_resources.py /tmp/book-agent-agent-runtime-v2.pUOyOf/src/book_agent/infra/repositories/runtime_resources.py > /tmp/round2-backport-patches/commit1/runtime_resources_repo.patch || true
git diff --no-index -- src/book_agent/app/runtime/controllers/chapter_controller.py /tmp/book-agent-agent-runtime-v2.pUOyOf/src/book_agent/app/runtime/controllers/chapter_controller.py > /tmp/round2-backport-patches/commit1/chapter_controller.patch || true
git diff --no-index -- src/book_agent/app/runtime/controller_runner.py /tmp/book-agent-agent-runtime-v2.pUOyOf/src/book_agent/app/runtime/controller_runner.py > /tmp/round2-backport-patches/commit1/controller_runner.patch || true
git diff --no-index -- tests/test_review_sessions.py /tmp/book-agent-agent-runtime-v2.pUOyOf/tests/test_review_sessions.py > /tmp/round2-backport-patches/commit1/test_review_sessions.patch || true
git diff --no-index -- tests/test_runtime_resources.py /tmp/book-agent-agent-runtime-v2.pUOyOf/tests/test_runtime_resources.py > /tmp/round2-backport-patches/commit1/test_runtime_resources.patch || true
git diff --no-index -- tests/test_runtime_resources_repository.py /tmp/book-agent-agent-runtime-v2.pUOyOf/tests/test_runtime_resources_repository.py > /tmp/round2-backport-patches/commit1/test_runtime_resources_repository.patch || true
git diff --no-index -- tests/test_app_runtime.py /tmp/book-agent-agent-runtime-v2.pUOyOf/tests/test_app_runtime.py > /tmp/round2-backport-patches/commit1/test_app_runtime.patch || true
```

然后逐个审查并应用：

```bash
git apply --reject /tmp/round2-backport-patches/commit1/*.patch
```

#### 1.3 验证

```bash
.venv/bin/python -m pytest \
  tests/test_review_sessions.py \
  tests/test_runtime_resources.py \
  tests/test_runtime_resources_repository.py \
  tests/test_app_runtime.py
```

### Step 2: Round-2 Commit 2

目标：

- `runtime_lane_health.py`
- `recovery_matrix.py`
- packet/review/run controller 投影

#### 2.1 整文件复制

```bash
mkdir -p src/book_agent/services tests
cp /tmp/book-agent-agent-runtime-v2.pUOyOf/src/book_agent/services/runtime_lane_health.py src/book_agent/services/
cp /tmp/book-agent-agent-runtime-v2.pUOyOf/src/book_agent/services/recovery_matrix.py src/book_agent/services/
cp /tmp/book-agent-agent-runtime-v2.pUOyOf/tests/test_runtime_lane_health.py tests/
cp /tmp/book-agent-agent-runtime-v2.pUOyOf/tests/test_recovery_matrix.py tests/
```

#### 2.2 hunk patch 文件

```bash
mkdir -p /tmp/round2-backport-patches/commit2
git diff --no-index -- src/book_agent/app/runtime/controllers/packet_controller.py /tmp/book-agent-agent-runtime-v2.pUOyOf/src/book_agent/app/runtime/controllers/packet_controller.py > /tmp/round2-backport-patches/commit2/packet_controller.patch || true
git diff --no-index -- src/book_agent/app/runtime/controllers/review_controller.py /tmp/book-agent-agent-runtime-v2.pUOyOf/src/book_agent/app/runtime/controllers/review_controller.py > /tmp/round2-backport-patches/commit2/review_controller.patch || true
git diff --no-index -- src/book_agent/app/runtime/controllers/run_controller.py /tmp/book-agent-agent-runtime-v2.pUOyOf/src/book_agent/app/runtime/controllers/run_controller.py > /tmp/round2-backport-patches/commit2/run_controller.patch || true
git diff --no-index -- src/book_agent/infra/repositories/runtime_resources.py /tmp/book-agent-agent-runtime-v2.pUOyOf/src/book_agent/infra/repositories/runtime_resources.py > /tmp/round2-backport-patches/commit2/runtime_resources_repo.patch || true
git diff --no-index -- tests/test_runtime_resources.py /tmp/book-agent-agent-runtime-v2.pUOyOf/tests/test_runtime_resources.py > /tmp/round2-backport-patches/commit2/test_runtime_resources.patch || true
git diff --no-index -- tests/test_runtime_resources_repository.py /tmp/book-agent-agent-runtime-v2.pUOyOf/tests/test_runtime_resources_repository.py > /tmp/round2-backport-patches/commit2/test_runtime_resources_repository.patch || true
git diff --no-index -- tests/test_review_sessions.py /tmp/book-agent-agent-runtime-v2.pUOyOf/tests/test_review_sessions.py > /tmp/round2-backport-patches/commit2/test_review_sessions.patch || true
git apply --reject /tmp/round2-backport-patches/commit2/*.patch
```

#### 2.3 验证

```bash
.venv/bin/python -m pytest \
  tests/test_runtime_lane_health.py \
  tests/test_recovery_matrix.py \
  tests/test_runtime_resources.py \
  tests/test_runtime_resources_repository.py \
  tests/test_review_sessions.py
```

### Step 3: Round-2 Commit 3

目标：

- review deadlock incident family
- bounded replay
- `REQ-MX-01`

#### 3.1 hunk patch 文件

```bash
mkdir -p /tmp/round2-backport-patches/commit3
git diff --no-index -- src/book_agent/domain/enums.py /tmp/book-agent-agent-runtime-v2.pUOyOf/src/book_agent/domain/enums.py > /tmp/round2-backport-patches/commit3/domain_enums.patch || true
git diff --no-index -- src/book_agent/services/incident_triage.py /tmp/book-agent-agent-runtime-v2.pUOyOf/src/book_agent/services/incident_triage.py > /tmp/round2-backport-patches/commit3/incident_triage.patch || true
git diff --no-index -- src/book_agent/app/runtime/controllers/incident_controller.py /tmp/book-agent-agent-runtime-v2.pUOyOf/src/book_agent/app/runtime/controllers/incident_controller.py > /tmp/round2-backport-patches/commit3/incident_controller.patch || true
git diff --no-index -- src/book_agent/app/runtime/controllers/review_controller.py /tmp/book-agent-agent-runtime-v2.pUOyOf/src/book_agent/app/runtime/controllers/review_controller.py > /tmp/round2-backport-patches/commit3/review_controller.patch || true
git diff --no-index -- src/book_agent/app/runtime/document_run_executor.py /tmp/book-agent-agent-runtime-v2.pUOyOf/src/book_agent/app/runtime/document_run_executor.py > /tmp/round2-backport-patches/commit3/document_run_executor.patch || true
git diff --no-index -- src/book_agent/services/run_execution.py /tmp/book-agent-agent-runtime-v2.pUOyOf/src/book_agent/services/run_execution.py > /tmp/round2-backport-patches/commit3/run_execution.patch || true
git diff --no-index -- tests/test_incident_triage.py /tmp/book-agent-agent-runtime-v2.pUOyOf/tests/test_incident_triage.py > /tmp/round2-backport-patches/commit3/test_incident_triage.patch || true
git diff --no-index -- tests/test_runtime_v2_enums.py /tmp/book-agent-agent-runtime-v2.pUOyOf/tests/test_runtime_v2_enums.py > /tmp/round2-backport-patches/commit3/test_runtime_v2_enums.patch || true
git diff --no-index -- tests/test_incident_controller.py /tmp/book-agent-agent-runtime-v2.pUOyOf/tests/test_incident_controller.py > /tmp/round2-backport-patches/commit3/test_incident_controller.patch || true
git apply --reject /tmp/round2-backport-patches/commit3/*.patch
cp /tmp/book-agent-agent-runtime-v2.pUOyOf/tests/test_req_mx_01_review_deadlock_self_heal.py tests/
```

#### 3.2 验证

```bash
.venv/bin/python -m pytest \
  tests/test_incident_triage.py \
  tests/test_incident_controller.py \
  tests/test_runtime_v2_enums.py \
  tests/test_run_execution.py \
  tests/test_req_mx_01_review_deadlock_self_heal.py
```

### Step 4: Round-2 Commit 4

目标：

- `chapter_hold`
- packet exhaustion -> chapter boundary
- `REQ-MX-02`

#### 4.1 hunk patch 文件

```bash
mkdir -p /tmp/round2-backport-patches/commit4
git diff --no-index -- src/book_agent/domain/models/ops.py /tmp/book-agent-agent-runtime-v2.pUOyOf/src/book_agent/domain/models/ops.py > /tmp/round2-backport-patches/commit4/domain_models_ops.patch || true
git diff --no-index -- src/book_agent/services/recovery_matrix.py /tmp/book-agent-agent-runtime-v2.pUOyOf/src/book_agent/services/recovery_matrix.py > /tmp/round2-backport-patches/commit4/recovery_matrix.patch || true
git diff --no-index -- src/book_agent/app/runtime/controllers/chapter_controller.py /tmp/book-agent-agent-runtime-v2.pUOyOf/src/book_agent/app/runtime/controllers/chapter_controller.py > /tmp/round2-backport-patches/commit4/chapter_controller.patch || true
git diff --no-index -- src/book_agent/app/runtime/controllers/packet_controller.py /tmp/book-agent-agent-runtime-v2.pUOyOf/src/book_agent/app/runtime/controllers/packet_controller.py > /tmp/round2-backport-patches/commit4/packet_controller.patch || true
git apply --reject /tmp/round2-backport-patches/commit4/*.patch
cp /tmp/book-agent-agent-runtime-v2.pUOyOf/tests/test_req_mx_02_chapter_hold_escalation.py tests/
```

#### 4.2 验证

```bash
.venv/bin/python -m pytest \
  tests/test_req_mx_02_chapter_hold_escalation.py \
  tests/test_runtime_lane_health.py \
  tests/test_recovery_matrix.py \
  tests/test_run_execution.py
```

### Step 5: Round-2 Commit 5

目标：

- runtime bundle governance
- bundle guard
- canary rollback
- stable revision rebinding

#### 5.1 整文件复制

```bash
mkdir -p alembic/versions src/book_agent/services tests
cp /tmp/book-agent-agent-runtime-v2.pUOyOf/alembic/versions/20260327_0014_runtime_bundle_rollback_lineage.py alembic/versions/
cp /tmp/book-agent-agent-runtime-v2.pUOyOf/src/book_agent/services/bundle_guard.py src/book_agent/services/
cp /tmp/book-agent-agent-runtime-v2.pUOyOf/tests/test_bundle_guard.py tests/
```

#### 5.2 hunk patch 文件

```bash
mkdir -p /tmp/round2-backport-patches/commit5
git diff --no-index -- src/book_agent/domain/models/ops.py /tmp/book-agent-agent-runtime-v2.pUOyOf/src/book_agent/domain/models/ops.py > /tmp/round2-backport-patches/commit5/domain_models_ops.patch || true
git diff --no-index -- src/book_agent/services/runtime_bundle.py /tmp/book-agent-agent-runtime-v2.pUOyOf/src/book_agent/services/runtime_bundle.py > /tmp/round2-backport-patches/commit5/runtime_bundle.patch || true
git diff --no-index -- src/book_agent/services/runtime_patch_validation.py /tmp/book-agent-agent-runtime-v2.pUOyOf/src/book_agent/services/runtime_patch_validation.py > /tmp/round2-backport-patches/commit5/runtime_patch_validation.patch || true
git diff --no-index -- src/book_agent/app/runtime/controllers/incident_controller.py /tmp/book-agent-agent-runtime-v2.pUOyOf/src/book_agent/app/runtime/controllers/incident_controller.py > /tmp/round2-backport-patches/commit5/incident_controller.patch || true
git diff --no-index -- src/book_agent/app/runtime/document_run_executor.py /tmp/book-agent-agent-runtime-v2.pUOyOf/src/book_agent/app/runtime/document_run_executor.py > /tmp/round2-backport-patches/commit5/document_run_executor.patch || true
git diff --no-index -- src/book_agent/services/run_control.py /tmp/book-agent-agent-runtime-v2.pUOyOf/src/book_agent/services/run_control.py > /tmp/round2-backport-patches/commit5/run_control.patch || true
git diff --no-index -- tests/test_runtime_bundle.py /tmp/book-agent-agent-runtime-v2.pUOyOf/tests/test_runtime_bundle.py > /tmp/round2-backport-patches/commit5/test_runtime_bundle.patch || true
git diff --no-index -- tests/test_runtime_incidents_bundles.py /tmp/book-agent-agent-runtime-v2.pUOyOf/tests/test_runtime_incidents_bundles.py > /tmp/round2-backport-patches/commit5/test_runtime_incidents_bundles.patch || true
git diff --no-index -- tests/test_runtime_patch_validation.py /tmp/book-agent-agent-runtime-v2.pUOyOf/tests/test_runtime_patch_validation.py > /tmp/round2-backport-patches/commit5/test_runtime_patch_validation.patch || true
git diff --no-index -- tests/test_incident_controller.py /tmp/book-agent-agent-runtime-v2.pUOyOf/tests/test_incident_controller.py > /tmp/round2-backport-patches/commit5/test_incident_controller.patch || true
git diff --no-index -- tests/test_run_execution.py /tmp/book-agent-agent-runtime-v2.pUOyOf/tests/test_run_execution.py > /tmp/round2-backport-patches/commit5/test_run_execution.patch || true
git diff --no-index -- tests/test_run_control_api.py /tmp/book-agent-agent-runtime-v2.pUOyOf/tests/test_run_control_api.py > /tmp/round2-backport-patches/commit5/test_run_control_api.patch || true
git apply --reject /tmp/round2-backport-patches/commit5/*.patch
```

#### 5.3 验证

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

### Step 6: Round-2 Commit 6

目标：

- acceptance closure
- `REQ-MX-03`
- `REQ-MX-04`
- `REQ-EX-02` protective regression

#### 6.1 整文件复制

```bash
cp /tmp/book-agent-agent-runtime-v2.pUOyOf/tests/test_req_mx_03_bundle_rollback.py tests/
cp /tmp/book-agent-agent-runtime-v2.pUOyOf/tests/test_req_mx_04_recovery_matrix.py tests/
```

#### 6.2 验证

```bash
.venv/bin/python -m pytest \
  tests/test_req_mx_03_bundle_rollback.py \
  tests/test_req_mx_04_recovery_matrix.py \
  tests/test_req_ex_02_export_misrouting_self_heal.py
```

## 4. 建议的提交顺序

建议一组一提交：

1. `feat(runtime-v2): add review session runtime resource and generation-bound reconciliation`
2. `feat(runtime-v2): add lane health and unified recovery matrix`
3. `feat(runtime-v2): add review-deadlock incident classification and bounded replay`
4. `feat(runtime-v2): add chapter-boundary escalation after packet repair exhaustion`
5. `feat(runtime-v2): add bundle rollback governance and stable revision rebinding`
6. `test(runtime-v2): close acceptance coverage for bundle rollback and recovery matrix`

## 5. 执行中最容易踩坑的点

1. 不要跳过 round-1。
2. 不要在当前脏工作树直接执行。
3. `document_run_executor.py`、`run_control.py`、`domain/models/ops.py`、`incident_controller.py` 都是热点文件，必须先看 patch 再 apply。
4. `tests/test_app_runtime.py` 的修复是 round-2 真回归，不是“随手调测试”。
5. 最后一轮一定要跑 `tests/test_req_ex_02_export_misrouting_self_heal.py`，否则你不知道 round-2 是否把 round-1 竖切打坏。

## 6. 一句话执行摘要

实际执行时不要直接“把 round-2 拷进主仓库”，而要：

1. 先在干净 worktree 里完成 round-1
2. 再按 6 个 commit slice 逐组回迁 round-2
3. 每组都跑本组验证
4. 最后用 `REQ-MX-03`、`REQ-MX-04` 和 `REQ-EX-02` 收口。 
