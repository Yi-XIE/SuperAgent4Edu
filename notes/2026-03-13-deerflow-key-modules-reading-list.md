# DeerFlow 关键模块阅读清单

日期：2026-03-13

## 1. 阅读目标

这份清单的目标不是覆盖仓库的所有文件，而是帮助你最快看懂以下 4 个问题：

- DeerFlow 的主流程从哪里进入
- 多代理是怎么调度的
- 记忆系统是怎么读写的
- 前端是怎么把 Agent 过程展示出来的

## 2. 推荐阅读顺序

建议按这个顺序看，而不是随机翻代码：

1. 顶层 README 和运行入口
2. 后端总体架构
3. Lead Agent
4. Subagent 机制
5. Memory 机制
6. Skills 机制
7. Gateway API
8. 前端工作台

这样读的好处是：先有大图，再钻核心机制，最后再看页面怎么接上。

## 3. 第一层：先建立全局理解

先读这些文件：

- `upstream/deer-flow/README.md`
- `upstream/deer-flow/backend/README.md`
- `upstream/deer-flow/frontend/README.md`
- `upstream/deer-flow/backend/docs/ARCHITECTURE.md`
- `upstream/deer-flow/backend/docs/CONFIGURATION.md`

你读这一层时，重点不要纠结实现细节，而是先回答：

- 系统有哪些服务
- 前后端怎么连接
- 哪些能力属于 DeerFlow 的核心卖点

## 4. 第二层：运行入口和系统主干

建议先看这些入口文件：

- `upstream/deer-flow/Makefile`
- `upstream/deer-flow/backend/Makefile`
- `upstream/deer-flow/backend/langgraph.json`
- `upstream/deer-flow/backend/src/gateway/app.py`
- `upstream/deer-flow/frontend/src/app/workspace/page.tsx`
- `upstream/deer-flow/frontend/src/app/workspace/layout.tsx`

你要搞清楚：

- 后端主服务怎么启动
- LangGraph 和 Gateway 怎么协作
- 前端工作台页面从哪里进入

## 5. 第三层：Lead Agent

这是你最该先吃透的一块。

关键文件：

- `upstream/deer-flow/backend/src/agents/lead_agent/agent.py`
- `upstream/deer-flow/backend/src/agents/lead_agent/prompt.py`

阅读重点：

- Lead Agent 是怎么创建的
- 它在什么时候决定任务拆解
- 它的系统提示词里注入了哪些上下文
- 后续你要做教育场景改造时，哪些地方最可能会动

## 6. 第四层：Subagent 机制

你最关注多代理编排，所以这一层要仔细看。

关键文件：

- `upstream/deer-flow/backend/src/subagents/executor.py`
- `upstream/deer-flow/backend/src/subagents/registry.py`
- `upstream/deer-flow/backend/src/subagents/config.py`
- `upstream/deer-flow/backend/src/subagents/builtins/general_purpose.py`
- `upstream/deer-flow/backend/src/subagents/builtins/bash_agent.py`
- `upstream/deer-flow/backend/src/tools/builtins/task_tool.py`

阅读重点：

- 子代理是怎么注册的
- 主代理怎样调用子代理
- 子代理执行结果怎样回传
- 并发和超时是怎么控制的
- 你的教育场景适合把哪些角色变成固定子代理

## 7. 第五层：Memory 机制

这是第二个重点。

关键文件：

- `upstream/deer-flow/backend/src/agents/memory/updater.py`
- `upstream/deer-flow/backend/src/agents/memory/queue.py`
- `upstream/deer-flow/backend/src/agents/memory/prompt.py`
- `upstream/deer-flow/backend/src/agents/middlewares/memory_middleware.py`
- `upstream/deer-flow/backend/src/config/memory_config.py`
- `upstream/deer-flow/backend/src/gateway/routers/memory.py`

阅读重点：

- 记忆是什么时候被抽取的
- 是同步写还是异步写
- 记忆以什么结构存储
- 系统提示什么时候读取记忆
- 你后面怎样把教师偏好、课程连续性和团队模板映射进来

## 8. 第六层：Middleware 机制

如果你想真正理解 DeerFlow 的执行链路，中间件非常关键。

建议重点看：

- `upstream/deer-flow/backend/src/agents/middlewares/thread_data_middleware.py`
- `upstream/deer-flow/backend/src/agents/middlewares/uploads_middleware.py`
- `upstream/deer-flow/backend/src/agents/middlewares/memory_middleware.py`
- `upstream/deer-flow/backend/src/agents/middlewares/title_middleware.py`
- `upstream/deer-flow/backend/src/agents/middlewares/clarification_middleware.py`

阅读重点：

- 每个中间件在什么时机生效
- 哪些上下文是通过中间件注入的
- 你的教育场景未来是否需要增加新的中间件

## 9. 第七层：Skills 机制

这是后面承载 UbD 和 PBL 方法论的关键入口。

关键文件：

- `upstream/deer-flow/backend/src/skills/loader.py`
- `upstream/deer-flow/backend/src/skills/parser.py`
- `upstream/deer-flow/backend/src/skills/types.py`
- `upstream/deer-flow/backend/src/config/skills_config.py`
- `upstream/deer-flow/backend/src/gateway/routers/skills.py`

阅读重点：

- 技能文件是怎么被发现和解析的
- 技能怎样影响系统上下文
- 技能启用/关闭走哪条接口
- 你的教育技能应该放在哪一层最合适

## 10. 第八层：Sandbox 和工具系统

虽然你当前重点不是 Sandbox，但还是要知道主干。

关键文件：

- `upstream/deer-flow/backend/src/sandbox/sandbox.py`
- `upstream/deer-flow/backend/src/sandbox/middleware.py`
- `upstream/deer-flow/backend/src/sandbox/tools.py`
- `upstream/deer-flow/backend/src/sandbox/local/local_sandbox.py`
- `upstream/deer-flow/backend/src/sandbox/local/local_sandbox_provider.py`

阅读重点：

- 文件和命令执行工具如何接入
- 工作目录和虚拟路径怎样映射
- 哪些能力对你的 Demo 真正必要，哪些可以先不用

## 11. 第九层：Gateway API

当前端接入时，这一层会很重要。

关键文件：

- `upstream/deer-flow/backend/src/gateway/app.py`
- `upstream/deer-flow/backend/src/gateway/routers/models.py`
- `upstream/deer-flow/backend/src/gateway/routers/skills.py`
- `upstream/deer-flow/backend/src/gateway/routers/memory.py`
- `upstream/deer-flow/backend/src/gateway/routers/uploads.py`
- `upstream/deer-flow/backend/src/gateway/routers/artifacts.py`

阅读重点：

- 前端依赖了哪些接口
- 记忆和技能怎样从 UI 层被访问
- 你的教育工作台未来需要增加哪些接口，哪些可以先复用

## 12. 第十层：前端工作台

你要做的是“可演示前端”，所以前端不需要全看，但必须看对地方。

优先看这些文件：

- `upstream/deer-flow/frontend/src/app/workspace/page.tsx`
- `upstream/deer-flow/frontend/src/components/workspace/workspace-container.tsx`
- `upstream/deer-flow/frontend/src/components/workspace/chats/chat-box.tsx`
- `upstream/deer-flow/frontend/src/components/workspace/messages/message-list.tsx`
- `upstream/deer-flow/frontend/src/components/workspace/messages/subtask-card.tsx`
- `upstream/deer-flow/frontend/src/components/workspace/settings/memory-settings-page.tsx`
- `upstream/deer-flow/frontend/src/core/memory/api.ts`
- `upstream/deer-flow/frontend/src/core/memory/hooks.ts`
- `upstream/deer-flow/frontend/src/core/skills/api.ts`
- `upstream/deer-flow/frontend/src/core/threads/hooks.ts`

阅读重点：

- 任务输入和消息流如何组织
- 子任务卡片如何展示
- 记忆设置如何在前端接入
- 你后面要做的“教师工作台”更适合复用哪些现成组件

## 13. 最值得先做笔记的 10 个文件

如果你时间有限，先看这 10 个：

1. `upstream/deer-flow/README.md`
2. `upstream/deer-flow/backend/README.md`
3. `upstream/deer-flow/backend/src/agents/lead_agent/agent.py`
4. `upstream/deer-flow/backend/src/agents/lead_agent/prompt.py`
5. `upstream/deer-flow/backend/src/subagents/executor.py`
6. `upstream/deer-flow/backend/src/agents/middlewares/memory_middleware.py`
7. `upstream/deer-flow/backend/src/agents/memory/updater.py`
8. `upstream/deer-flow/backend/src/skills/loader.py`
9. `upstream/deer-flow/backend/src/gateway/app.py`
10. `upstream/deer-flow/frontend/src/components/workspace/messages/subtask-card.tsx`

## 14. 建议的阅读输出

每看完一层，建议你都写 3 类笔记：

- 这个模块解决什么问题
- 它和上下游怎么连接
- 未来做教育场景时你会改哪里

不要只记“这个文件里有什么函数”，要记“为什么它在这里”。

## 15. 下一步

看完这份清单后，建议你立刻做两件事：

1. 开始读第 1 到第 5 节，并在 `notes/` 里写一份自己的模块笔记
2. 再让我继续为你整理下一份文档：`教育场景输入输出定义`
