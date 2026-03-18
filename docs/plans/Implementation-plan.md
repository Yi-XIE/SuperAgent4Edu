# DeerFlow 教育课程工作台实现计划

日期：2026-03-17

关联文档：

- `docs/plans/Product-design.md`
- `docs/plans/Agent-roles.md`
- `docs/plans/Hitl-checkpoints.md`
- `docs/prompts/Reviewer-critic-prompts.md`
- `docs/standards/course-generation-quality-spec.md`

## 封板执行状态（2026-03-17 晚）

- 已落代码：
  - Clarification `options` 容错解析（数组 / 字符串化数组 / 普通字符串）。
  - 聊天页审批卡兜底：模型直接输出审批文本时，也能渲染为审批卡。
  - 教育技能与 SOUL 硬约束增强：课时一致性、预算上限、安全禁用项前置检查。
  - 自动化验收脚本：`upstream/deer-flow/scripts/education_closeout_eval.py`。
- 已验证通过：
  - 前端 `tsc`。
  - 教育合同测试：clarification / frontend contracts / docs sync / assets。
  - 状态机分支：`CP2=调整研究重点`、`CP3` 二次拒绝回到 `CP1`。
- 当前剩余风险（模型侧）：
  - `Step 3.5 Flash` 在少数回合仍可能输出自由文本确认而非标准 checkpoint 文案，导致“纯自动正常路径”不稳定。

## 1. 文档目的

这份文档用于把当前教育课程工作台从已有 Demo 收敛到可持续扩展的 `4+1` 运行模型，并明确：

- 第一版先落什么
- 哪些能力要收敛
- 代码和文档要如何同步
- 哪些能力仍然保持延后

## 2. 当前实现基线

当前代码已经具备以下基础：

- 教育任务输入与运行主链
- 草案评审卡与返工护栏
- `Reviewer` / `Critic` 双层评审能力
- 教育工件输出区与结果摘要
- 资源库、模板库与教育记忆面板的基础结构

当前主要问题不是“主流程不存在”，而是运行角色和文档口径还不够收敛，容易继续朝“概念分工 = 运行角色”方向膨胀。

## 3. 本轮实现目标

本轮统一目标是：

1. 把运行模型固定为 `4+1`
2. 把 `Asset Retrieval` 和 `Asset Extraction` 明确为系统能力
3. 把评审链固定为 `Reviewer 常开，Critic 条件启用`
4. 把返工目标收敛到 `Blueprint` 或 `Package`
5. 保证产品文档、角色文档、审批文档和 prompt 文档口径一致

## 4. 目标运行模型

### 4.1 运行角色

第一版统一采用以下 `4+1` 运行角色：

1. `Lead Agent`
2. `Blueprint Agent`
3. `Package Agent`
4. `Reviewer Agent`
5. `Critic Agent`（可选）

### 4.2 系统能力

以下能力保留为系统能力，不做一等 agent：

- `Asset Retrieval`
- `Asset Extraction`

### 4.3 概念层映射

运行角色收敛后，教学设计逻辑仍保留以下概念层：

- `目标蓝图`：内部对应 `UbD Stage 1`
- `证据设计`：内部对应 `UbD Stage 2`
- `活动流程`：内部对应 `UbD Stage 3`
- `学具附录`
- `最终整理`

映射关系如下：

- `Blueprint Agent` 承载 `目标蓝图 + 研究支撑`
- `Package Agent` 承载 `证据设计 + 活动流程 + 学具附录 + 最终整理`

## 5. 第一版必做范围

### 5.1 任务流

第一版必须把以下任务流做顺：

1. 任务简报
2. 生成策略确认
3. 课程蓝图生成
4. 课程蓝图锁定
5. 完整课包生成
6. 草案评审
7. 素材提取确认

### 5.2 强审批点

第一版保持 `3 个强审批点 + 1 个轻确认节点`：

1. `任务确认点`
2. `课程蓝图锁定点`
3. `草案评审点`
4. `素材提取确认`

### 5.3 质量控制

第一版必须保留：

- `Reviewer` 第一轮专业审查
- `Critic` 条件性挑战复核
- 基于质量规范的不可妥协项检查
- 局部返工护栏

### 5.4 素材沉淀

第一版必须至少支持：

- 生成前素材召回
- 草案通过后候选素材提取
- 教师确认后写入个人素材台

## 6. 本轮文档与 prompt 收敛项

### 6.1 必须统一的术语

本轮所有对外文档统一采用：

- `目标蓝图`
- `证据设计`
- `活动流程`
- `课程蓝图`
- `完整课包`

不再继续把对外说明写成旧的“细拆分运行角色”命名，而统一使用当前运行层和教师化术语。

### 6.2 Prompt 层统一要求

评审层 prompt 必须同步到以下输入合同：

- `TaskBrief`
- `CourseBlueprint`
- `CoursePackage`
- 质量规范
- 当前是否包含学具附录

评审结果必须优先输出运行层回退建议：

- `Blueprint Agent`
- `Package Agent`
- `Lead Agent`

### 6.3 文档同步要求

以下文档必须保持同一口径：

- `docs/plans/Product-design.md`
- `docs/plans/Agent-roles.md`
- `docs/plans/Hitl-checkpoints.md`
- `docs/plans/Implementation-plan.md`
- `docs/prompts/Reviewer-critic-prompts.md`

## 7. 代码侧演进建议

### 7.1 先做文档与编排口径收敛

优先顺序如下：

1. 收敛文档和 prompt
2. 收敛运行态命名和回退目标
3. 再决定是否真的拆并运行节点

原因是当前很多“角色过多”的问题还停留在说明层，不一定需要立刻大改代码。

### 7.2 编排层收敛方向

代码层后续应朝以下方向演进：

- 把蓝图生成相关节点收敛到 `Blueprint` 阶段
- 把完整课包相关节点收敛到 `Package` 阶段
- 让 `Reviewer` 成为默认质量闸门
- 只在高风险场景启用 `Critic`
- 把素材召回和素材提取做成围绕主流程的能力调用

### 7.3 前端展示收敛方向

前端展示优先面向教师认知，而不是面向内部编排细节：

- 中间执行流显示 `任务简报 / 蓝图生成 / 课包生成 / 质量评审 / 素材提取`
- 右侧结果区显示 `课程蓝图 / 教案 / PPT / 学具 / 参考资料 / 本次提取素材`
- 返工按钮继续使用教学语言，但运行层只回退到 `Blueprint` 或 `Package`

## 8. 暂不处理范围

本轮不处理以下内容：

- 重权限体系
- 复杂模板市场
- 完整学生端
- 工作流可视化编辑器
- 学具库存与供应链
- 精美 PPT 自动排版
- 大规模团队协作治理

## 9. 完成标准

本轮完成标准如下：

1. 所有主文档和评审 prompt 都采用 `4+1` 口径
2. 不再把 `Asset Retrieval` / `Asset Extraction` 写成运行 agent
3. `Critic` 被明确定义为条件启用，而不是默认常开
4. 返工目标被明确收敛为 `Blueprint` 或 `Package`
5. 文档同步测试通过

## 10. 下一步实现优先级

在文档层收敛完成后，建议按以下优先级推进代码：

1. 先把运行态和前端术语同步到 `Blueprint / Package`
2. 再把 `Reviewer` / `Critic` 结构化结果真正写回运行态
3. 再把素材台接进生成前召回与生成后提取链路
4. 最后再评估模板库、资源库和校本协作的整合深度
