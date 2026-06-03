# AGENTS.md - pWPS Agent 精简入口

本文件是开发 Agent 的**常驻路由入口**，不是完整百科。详细规则按任务类型读取对应文档。

## 1. 项目范围

实现一个字段驱动、证据支撑、状态可恢复、可审计、可测试、用户友好的 pWPS 草案生成工作流系统。

系统不是“聊天生成 WPS”的 Demo，也不生成正式可签发 WPS；正式 WPS/PQR/WPQR 必须由人工和工艺评定确认。

## 2. 常驻硬约束

1. 前端只使用 `pnpm`；后端只使用 `uv`。
2. 字段、状态、API、Skill schema 统一使用 `Pydantic v2`。
3. 状态使用 `StrEnum / Enum`，禁止裸字符串状态。
4. Auto / Guided 共用同一字段确认工作流，只替换 `DecisionActor`。
5. Workflow Node 不直接拼 Prompt；Prompt 属于 Skill。
6. LLM 不控制全局流程；KnowledgeService 不直接决定字段值；AuditEngine 不完全依赖 LLM。
7. 前端必须默认考虑用户友好和多端适配。
8. 新依赖、新技术、新服务引入前必须完成最佳实践调查和影响分析。
9. 禁止临时 patch 绕过 Field Registry、WorkflowState、AuditEngine、Pydantic schema 或安全边界。
10. 测试保护核心路径，但避免过度测试；过时测试必须及时删除。

## 3. 按需读取路由

| 任务类型 | 必读文档 |
|---|---|
| 产品范围 / MVP | `requirements.md`, `development_stages.md` |
| 架构 / 模块边界 | `architecture.md`, `engineering_principles.md` |
| 技术栈 / 环境 / 依赖 | `tech_stack.md`, `deployment_guide.md` |
| Schema / 状态 / 版本化 | `data_schema.md` |
| Workflow / LangGraph / 中断恢复 | `workflow.md` |
| Skill / Prompt / LLM 结构化调用 | `skill_design.md` |
| 知识检索 / RAG / 文档入库 | `knowledge_design.md` |
| API / 前后端契约 | `api_contract.md` |
| 前端体验 / 多端适配 | `frontend_guidelines.md` |
| AI 协作开发 | `ai_development_workflow.md`, `change_management.md` |
| 测试 | `testing_strategy.md` |
| 可观测性 / 调试 | `observability.md` |
| 安全 / 风险 / Prompt Injection | `security_and_safety.md` |
| 评估 / 质量指标 | `evaluation_plan.md` |
| 模板 / 标准 Profile / 企业 Profile | `template_profile_design.md` |
| Agent 指令治理 / 渐进披露 | `agent_progressive_disclosure.md`, `agent_preservation_checklist.md` |
| 一致性检查 | `consistency_check.md` |

## 4. 开发流程

每次任务遵循：

```text
理解需求 -> 读取路由文档 -> 做小步计划 -> 修改代码 -> 运行必要测试 -> 总结影响面
```

禁止在未读取相关文档的情况下直接修改核心代码。

## 5. 修改后必须汇报

```text
完成了什么：
影响文件：
是否改变 schema/API/workflow：
是否新增依赖或服务：
是否需要迁移：
运行了哪些测试：
剩余风险：
```

## 6. 优先级

当文档冲突时，按以下优先级处理：

```text
用户当前明确指令
> 本 AGENTS.md 常驻硬约束
> data_schema/workflow/api_contract/skill_design 等领域契约
> 具体任务文档
> 代码当前实现
```

发现冲突时，先记录在 `consistency_check.md` 或变更总结中，再做最小必要修正。
