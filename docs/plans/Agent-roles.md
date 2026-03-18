# DeerFlow 教育课程工作台运行角色说明

日期：2026-03-17

关联文档：

- `docs/plans/Product-design.md`
- `docs/plans/Implementation-plan.md`
- `docs/plans/Hitl-checkpoints.md`
- `docs/standards/course-generation-quality-spec.md`
- `docs/prompts/Reviewer-critic-prompts.md`

## 1. 文档目的

这份文档用于定义教育课程工作台的 `运行角色`、`概念分工`、协作关系和返工路径。

这一版的核心取舍是：

- 概念层可以细
- 运行层必须收敛

也就是说，文档仍然保留“目标蓝图 / 证据设计 / 活动流程 / 学具附录 / 最终整理”这些教学设计层次，但第一版不把每一层都做成独立 agent。

## 2. 双层结构

### 2.1 运行层

第一版建议采用 `4+1` 运行模型：

1. `Lead Agent`
2. `Blueprint Agent`
3. `Package Agent`
4. `Reviewer Agent`
5. `Critic Agent`（可选）

### 2.2 系统能力层

以下两项保留为系统能力，而不是一等 agent：

- `Asset Retrieval`
- `Asset Extraction`

### 2.3 概念分工层

为了保证课程设计逻辑仍然清楚，系统内部继续按以下概念层思考：

- `目标蓝图`：内部对应 `UbD Stage 1`
- `证据设计`：内部对应 `UbD Stage 2`
- `活动流程`：内部对应 `UbD Stage 3`
- `学具附录`
- `最终整理`

其中：

- `Blueprint Agent` 负责 `目标蓝图 + 研究支撑`
- `Package Agent` 负责 `证据设计 + 活动流程 + 学具附录 + 最终整理`

## 3. 运行角色总览

| 运行角色 | 主要目标 | 核心输入 | 核心输出 | 是否直接触发 HITL |
|---|---|---|---|---|
| `Lead Agent` | 统筹任务、策略、审批与总控 | 用户任务、教师记忆、团队模板、素材召回结果 | 任务简报、审批卡、最终汇总、入库确认 | 是 |
| `Blueprint Agent` | 生成可锁定的课程蓝图 | 任务简报、素材建议、研究约束 | 大概念、核心问题、项目方向、研究支撑摘要 | 否 |
| `Package Agent` | 生成完整课包 | 蓝图结果、素材建议、学具约束、输出偏好 | 证据设计、活动流程、学具附录、教案、PPT 大纲 | 否 |
| `Reviewer Agent` | 做第一轮质量闸门 | 完整课包、质量规范 | reviewer 报告与结构化摘要 | 否 |
| `Critic Agent` | 做挑战性复核 | 完整课包、reviewer 结果 | critic 报告与结构化摘要 | 否 |

说明：

- 第一版只允许 `Lead Agent` 与教师直接进行审批交互。
- `Critic Agent` 默认不是每轮都开，只在高风险、低置信度或老师明确要求严格复核时启用。

## 4. 系统能力总览

| 系统能力 | 发生时机 | 输入 | 输出 |
|---|---|---|---|
| `Asset Retrieval` | 生成前 | 任务简报、教师素材台、资源库、教师记忆 | 相关素材、优先复用建议、冲突提示 |
| `Asset Extraction` | 草案通过后 | 完整课包、评审结果 | 候选素材清单、推荐分类、来源位置、入库建议 |

## 5. 协作原则

### 5.1 总原则

这套系统不是“越多 agent 越好”，而是：

- 让老师感受到清楚的备课流程
- 让运行链路尽量短
- 让课程设计逻辑仍然完整

### 5.2 为什么要收敛角色

如果把每个教学环节都做成独立运行角色，会带来几个问题：

- 编排过重，稳定性下降
- 运行更慢
- 边界更多是文档边界，不是必须的运行边界
- 老师感知不到这些细粒度角色，只会觉得流程碎

因此第一版选择：

- 文档上保留细分逻辑
- 运行上只保留少量强角色

### 5.3 协作顺序

建议运行顺序如下：

1. `Lead Agent` 读取任务、记忆和启用能力
2. `Asset Retrieval` 召回相关素材与参考资料
3. `Lead Agent` 形成任务简报并确认生成策略
4. `Blueprint Agent` 生成课程蓝图
5. `Lead Agent` 发起蓝图锁定
6. `Package Agent` 生成完整课包
7. `Reviewer Agent` 做首轮质量评审
8. 视风险决定是否启用 `Critic Agent`
9. `Lead Agent` 发起草案评审
10. `Asset Extraction` 抽取候选素材
11. `Lead Agent` 发起素材入库确认

### 5.4 模板与策略硬约束（V1.3+）

- `workflow_template_id` 不再只是存档字段，而是运行时约束输入：
  - 可覆盖回退映射（`rerun_map`）
  - 可开关 checkpoint（尤其 `cp4-asset-extraction-confirm`）
  - 可设置返工护栏上限（`guard.max_local_rework`）
- Critic 策略采用显式字段：
  - `critic_policy=manual_on | manual_off | auto`
  - `critic_activation_reason` 用于解释 auto 启停结果
- 生成前素材召回会写入 run 快照：
  - `asset_retrieval_notes`
  - `selected_asset_ids`
  - `retrieval_snapshot_at`

## 6. 角色说明

### 6.1 `Lead Agent`

职责：

- 读取用户输入
- 读取教师记忆、团队规则和素材召回结果
- 形成任务简报
- 判断本轮更适合“从零生成”还是“优先复用”
- 调度下游运行角色
- 在关键节点发起审批
- 汇总评审结论
- 在结尾推动素材入库与记忆写入

不负责什么：

- 不直接代替 Blueprint 或 Package 完成全部专业内容
- 不在下游角色出问题时用表面润色掩盖结构问题

### 6.2 `Blueprint Agent`

职责：

- 提炼大概念
- 设计核心问题与驱动方向
- 给出项目方向
- 吸收研究支撑与相关素材
- 输出老师可锁定的课程蓝图

内部覆盖的概念层：

- `目标蓝图`
- `研究支撑`

不负责什么：

- 不直接生成完整课包
- 不独立整理最终教案和 PPT

### 6.3 `Package Agent`

职责：

- 把蓝图转成完整课包
- 设计评价证据与表现性任务
- 编排活动流程和课时结构
- 生成学具附录
- 完成教案与 PPT 大纲整理

内部覆盖的概念层：

- `证据设计`
- `活动流程`
- `学具附录`
- `最终整理`

不负责什么：

- 不重新定义已锁定的蓝图方向
- 不替代 Reviewer 进行质量裁决

### 6.4 `Reviewer Agent`

职责：

- 按质量规范做第一轮专业审查
- 先检查硬门槛，再看 rubric
- 输出结构化评审摘要
- 给出可执行的局部返工建议

不负责什么：

- 不直接改写课包
- 不因为案例好看就要求照抄案例外形

### 6.5 `Critic Agent`

职责：

- 对 Reviewer 结论做挑战性复核
- 识别伪通过、漏判和隐藏风险
- 在必要时升级返工建议

启用条件建议：

- Reviewer 结果边界模糊
- 任务风险较高
- 老师明确要求更严格审查
- 系统判断当前草案置信度偏低

不负责什么：

- 不替代 Reviewer
- 不直接重写课包

## 7. 概念分工映射

虽然运行角色收敛，但教学设计逻辑仍然保持以下映射：

| 概念层 | 对外展示名 | 内部实现映射 | 当前承载角色 |
|---|---|---|---|
| 目标层 | `目标蓝图` | `UbD Stage 1` | `Blueprint Agent` |
| 证据层 | `证据设计` | `UbD Stage 2` | `Package Agent` |
| 活动层 | `活动流程` | `UbD Stage 3` | `Package Agent` |
| 学具层 | `学具附录` | Learning Kit | `Package Agent` |
| 呈现层 | `最终整理` | Presentation | `Package Agent` |

## 8. 返工路径

第一版默认支持“局部返工”，不建议一旦老师不满意就全量重跑。

建议返工映射如下：

| 问题类型 | 优先回退对象 | 说明 |
|---|---|---|
| 大概念、核心问题、项目方向不合适 | `Blueprint Agent` | 先修蓝图层 |
| 评价、活动、学具或整理存在明显问题 | `Package Agent` | 先修课包层 |
| 首轮质量判断过松或边界模糊 | `Reviewer Agent` | 先修评审层 |
| Reviewer 结论可能漏判 | `Critic Agent` | 只在已启用 critic 时成立 |
| 多模块冲突或返工方向不清 | `Lead Agent` | 由总控重新决定回退顺序 |

## 9. HITL 映射

### 9.1 节点设计

第一阶段建议采用 `3 个强审批点 + 1 个轻确认节点`：

1. `任务确认点`
2. `课程蓝图锁定点`
3. `草案评审点`
4. `素材提取确认`

### 9.2 由谁发起

- 只有 `Lead Agent` 可以发起这些节点
- 其他角色只负责产出，不直接打断老师

### 9.3 与运行角色的关系

| 节点 | 上游角色 | 下游影响 |
|---|---|---|
| `任务确认点` | `Lead Agent` | 是否进入 Blueprint 阶段 |
| `课程蓝图锁定点` | `Blueprint Agent` | 是否进入 Package 阶段 |
| `草案评审点` | `Package Agent` + `Reviewer` + `Critic` | 是否返工或接受 |
| `素材提取确认` | `Asset Extraction` | 是否把候选素材写入素材台 |

## 10. 前端展示映射

前端不需要把所有内部概念层都做成独立泳道，但应让老师看得懂当前在做什么。

建议展示为：

- `中间执行流`
  - 任务简报
  - 蓝图生成中
  - 课包生成中
  - 质量评审中
  - 素材提取中

- `右侧结果区`
  - 课程蓝图
  - 教案
  - PPT
  - 学具
  - 参考资料
  - 本次提取素材

## 11. 第一版实现建议

### 11.1 运行角色优先

第一版优先把以下 4+1 跑稳：

- `Lead Agent`
- `Blueprint Agent`
- `Package Agent`
- `Reviewer Agent`
- `Critic Agent`（可选）

### 11.2 系统能力不要误做成 agent

以下两项先实现为系统能力更合适：

- `Asset Retrieval`
- `Asset Extraction`

### 11.3 最重要的约束

- 不要把每个教学环节都拆成一等运行角色
- 不要让 `Package Agent` 变成无边界的大杂烩
- 不要让 Reviewer 或 Critic 代替上游偷偷修结构问题
- 不要让审批点继续增多
