# DeerFlow 教育工作台 V1.3 封板审计

日期：2026-03-18

## 1. 审计结论

- 主链路代码已可运行，前端教育页与聊天增强已落地。
- `CP2/CP3/CP4` 回退与护栏逻辑在状态机层可验证通过。
- run-thread 已一体化：`run_id` 业务主键、`thread_id` 会话载体、`bootstrap` 首轮前置。
- 自由文本审批路径已具备结构化兜底（含默认 checkpoint_id 推断）。

## 2. P0/P1/P2 缺口清单

### P0（已修复）

1. Clarification 选项被逐字拆分
- 现象：`options` 为字符串时被按字符编号，审批卡不可用。
- 处理：后端 middleware 增加 `options` 容错归一化（数组 / 字符串化数组 / 普通字符串）。

2. 模型不走 `ask_clarification` 时审批卡消失
- 现象：模型直接输出审批文本，前端按普通 assistant 气泡显示。
- 处理：前端消息分组增加审批文本兜底，命中 checkpoint 文本时仍渲染审批卡。

### P1（已修复）

1. 正常路径模型协议遵循度不稳定
- 处理：
  - Clarification 与前端解析层均支持自由文本归一化；
  - 无 metadata 时前端按 checkpoint 类型回填默认 `checkpoint_id`，保证状态机可写回。

2. 质量约束仍依赖模型遵循
- 处理：
  - 已增加 Presentation 前程序化硬校验器；
  - 不通过时触发受控 fallback 并在审批点暴露风险。

### P2（增强项，不在当前文档必做范围）

1. 收尾脚本可进一步拆分为：
- 快速验收（状态机 + 合同）
- 全链路模型验收（长时运行）

2. 质量评分可升级为：
- 规则评分 + LLM 评审双轨评分，并沉淀趋势数据。

## 3. 复现入口

- 自动化脚本：`upstream/deer-flow/scripts/education_closeout_eval.py`
- 最新报告示例：
  - `/tmp/education_closeout_report_fast2.json`
