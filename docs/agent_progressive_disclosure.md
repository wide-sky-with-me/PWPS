# Agent 指令渐进披露规范

## 1. 目的

本项目采用“渐进式披露”的 Agent 指令治理方式：根级 `AGENTS.md` 只保留高频、长期有效、必须始终遵守的规则；详细任务规则下沉到聚焦文档中，开发 Agent 按任务类型读取。

这样可以降低常驻上下文成本，避免重要规则被低频细节稀释，同时保持规则完整可追踪。

## 2. 核心原则

1. `AGENTS.md` 是路由入口，不是百科全书。
2. 常驻规则必须短、硬、稳定。
3. 任务细节必须进入专门文档。
4. 每类任务必须能从 `AGENTS.md` 找到对应必读文档。
5. 移动规则前必须检查冲突。
6. 移动规则后必须用 preservation checklist 验证规则未丢失。
7. 不允许因为压缩入口文件而删除安全、架构、技术栈、测试、领域边界等关键约束。

## 3. 常驻规则保留标准

规则满足以下任一条件，应留在 `AGENTS.md`：

- 每次开发都必须遵守。
- 违反后会导致架构方向错误。
- 违反后会破坏领域安全或工程安全。
- 违反后会导致 AI 开发工作流失控。
- 是包管理器、Schema、Workflow、Prompt 归属等全局约束。

示例：

```text
前端只使用 pnpm。
后端只使用 uv。
字段、状态、API、Skill schema 统一使用 Pydantic v2。
Prompt 属于 Skill，Workflow Node 不直接拼 Prompt。
Auto 和 Guided 共用同一字段确认工作流。
```

## 4. 下沉规则分类标准

以下规则不应长期堆在 `AGENTS.md`，应移动到对应文档：

| 规则类型 | 目标文档 |
|---|---|
| 前端布局、多端适配、组件选择 | `frontend_guidelines.md` |
| 后端框架、数据库、服务依赖 | `tech_stack.md`, `deployment_guide.md` |
| Pydantic 模型、枚举、版本字段 | `data_schema.md` |
| LangGraph 主图、子图、路由 | `workflow.md` |
| Skill 结构、Prompt、校验、重试 | `skill_design.md` |
| RAG、IR、KnowledgeProvider | `knowledge_design.md` |
| API 请求响应和错误码 | `api_contract.md` |
| 测试分层和测试删除规则 | `testing_strategy.md` |
| 变更影响分析 | `change_management.md` |
| 安全、Prompt Injection、敏感信息 | `security_and_safety.md` |

## 5. Agent 读取策略

Agent 每次任务只读取必要文档：

```text
先读 AGENTS.md
再根据任务类型读路由表中对应文档
如果任务涉及多个模块，读取所有相关契约文档
如果任务改变核心模型或流程，同时读取 consistency_check.md
```

不要因为“可能有用”而把所有文档一次性塞入上下文。

## 6. 规则移动流程

当发现 `AGENTS.md` 膨胀时：

1. 完整阅读现有 `AGENTS.md`。
2. 标记每条规则的类型：常驻 / 任务细节 / 重复 / 冲突 / 过时。
3. 先解决冲突，再移动规则。
4. 将任务细节移动到最聚焦的文档。
5. 在 `AGENTS.md` 的路由表中加入入口。
6. 更新 `agent_preservation_checklist.md`。
7. 做关键词检查，确认规则仍能被找到。
8. 复读新的 `AGENTS.md`，确认它能作为独立入口使用。

## 7. 禁止事项

禁止：

```text
为了缩短 AGENTS.md 删除关键规则
把同一规则复制到多个文档造成冲突
只移动内容但不更新路由表
只更新路由表但不检查目标文档是否真的包含规则
让 AGENTS.md 重新变成命令大全、技术百科或长篇设计文档
```

## 8. 与本项目文档的关系

本规范不替代其他文档。它只规定：

```text
哪些规则常驻
哪些规则按需读取
如何保持规则不丢失
如何降低 Agent 常驻上下文负担
```

领域设计仍以 `data_schema.md`、`workflow.md`、`skill_design.md`、`knowledge_design.md` 等契约文档为准。
