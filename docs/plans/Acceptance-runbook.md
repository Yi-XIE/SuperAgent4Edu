# DeerFlow 教育课程工作台 V1.3 验收运行手册

日期：2026-03-16

## 1. 目的

这份手册用于团队统一执行 V1.3 集成验收，确认三项闭环能力：

1. 双层评审（Reviewer + Critic）
2. 草案评审返工护栏
3. 教师记忆区与本次使用信号可视化

## 2. 环境准备

工作目录：`upstream/deer-flow`

前置要求：

- Node.js + pnpm 可用
- Python 3.12 可用
- `uv` 可用（用于 backend 测试）

建议命令：

```bash
cd upstream/deer-flow
make install
```

## 3. 自动化校验

### 3.1 后端测试

```bash
cd backend
uv run pytest -p no:capture tests/test_education_agent_assets.py \
  tests/test_education_memory_prompt.py \
  tests/test_education_memory_router.py \
  tests/test_education_frontend_contracts.py \
  tests/test_education_clarification_contract.py \
  tests/test_education_hitl_memory_middleware.py \
  tests/test_task_tool_core_logic.py
```

通过标准：

- 全部测试通过
- Critic 阶段、返工护栏、memory agent 分支合同均可验证

### 3.2 前端类型校验

```bash
cd ../frontend
pnpm exec tsc --noEmit --incremental false
```

通过标准：

- 无 TypeScript 类型错误

### 3.3 收尾脚本（推荐）

用于快速收集“模型实测 + 分支状态机验收”统一报告：

```bash
cd upstream/deer-flow/backend
OPENROUTER_API_KEY=... PYTHONPATH=. \
python ../scripts/education_closeout_eval.py \
  --model step-3.5-flash \
  --subagent-timeout 5 \
  --report /tmp/education_closeout_report_fast.json
```

说明：

- `normal_accept`：真实模型路径（会受模型协议遵循度影响）。
- `cp2_adjust_research_state_machine`：状态机验证“调整研究重点”回退链。
- `cp3_guardrail_state_machine`：状态机验证“二次拒绝重开 CP1”护栏。

## 4. 手工烟测（必须全过）

### 用例 1：审批点 1 触发

步骤：

1. 启动系统：`make dev`
2. 打开 `/workspace/agents/education-course-studio/chats/new`
3. 输入不完整任务（缺课时或学具限制）

期望：

- 出现“任务确认点”审批卡
- 选项可点击回传

### 用例 2：审批点 2 局部回退

步骤：

1. 在审批点 1 选择“继续并锁定当前任务约束”
2. 等待 Stage1 + Research 完成并进入审批点 2
3. 选择“调整研究重点”

期望：

- 不全量重跑
- 仅触发 `Research -> Learning-Kit -> Presentation -> Reviewer -> Critic` 相关阶段回退

### 用例 3：审批点 3 学具局部返工

步骤：

1. 让流程完成 `Presentation -> Reviewer -> Critic` 并进入审批点 3
2. 首次选择“重做学具附录”

期望：

- 仅重跑 `Learning-Kit + Presentation + Reviewer + Critic`
- 不重跑前序 UbD 阶段

### 用例 4：审批点 3 返工护栏

步骤：

1. 在用例 3 完成后再次进入审批点 3
2. 第二次继续选择任一非“接受”选项（如“重做活动流程”）

期望：

- 不继续无限局部返工
- 流程回到“任务确认点”，并在 details 中提示重开原因

### 用例 5：最终交付展示

步骤：

1. 在审批点 3 选择“接受”

期望：

- artifact 区可见核心成果
- 至少包含以下 5 个核心文件：
  - `ubd-course-card.md`
  - `lesson-plan.md`
  - `ppt-outline.md`
  - `reference-summary.md`
  - `artifact-manifest.json`

### 用例 6：教师记忆区与本次使用信号

步骤：

1. 完成一次课程包验收
2. 新建第二次会话，进入同一路由

期望：

- 右侧可见“教师记忆区”
- 可见“本次使用信号”列表（`education_signals`）
- 面板异常时主对话不受影响（面板可降级隐藏）

## 5. 常见失败排查

### 启动即失败（资产缺失）

现象：

- `make dev` 或 `make up` 前报 education asset validation failed

排查：

- 检查 `agents/education-course-studio/config.yaml` 与 `SOUL.md`
- 检查 9 个 `skills/custom/*/SKILL.md`（包含 `course-quality-critic`）
- 手动执行：`./scripts/sync-education-assets.sh`

### pytest 运行崩溃（Segmentation fault）

现象：

- 运行 `uv run pytest ...` 直接 `Segmentation fault`

排查：

- 改用 `uv run pytest -p no:capture ...` 关闭 pytest 默认 capture
- 保持在仓库内的 `backend/` 目录执行

### 审批卡不显示

现象：

- 出现 clarification 文本但未渲染为教育审批卡

排查：

- 确认当前 agent 为 `education-course-studio`
- 检查 clarification 内容是否包含：
  - 标题（任务确认点/课程蓝图锁定点/草案评审点）
  - 编号选项（`1. ...`）
  - 可选元字段（`checkpoint_id` / `recommended_option` / `retry_target` / `details`）

### 草案评审没有 Critic 摘要

现象：

- 草案评审点出现，但只显示 Reviewer 信息

排查：

- 确认流程顺序是 `Package -> Reviewer -> Critic -> Checkpoint 3`
- 检查 `/mnt/user-data/workspace/critic-summary.json` 是否生成
- 检查 `critic-summary.json` 是否包含 `verdict` 与 `agreement_with_reviewer`

### 记忆面板未显示

现象：

- 教育 agent 聊天页右侧没有“教师记忆区”

排查：

- 确认当前路由是 `education-course-studio`
- 检查 `GET /api/memory?agent_name=education-course-studio` 是否返回有效 JSON
- 确认 `facts` 或 `education_signals` 至少有一项可展示
