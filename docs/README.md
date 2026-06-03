# pWPS Agent 最终开发文档包（渐进披露优化版）

本目录用于指导重新实现一套面向 pWPS（Preliminary Welding Procedure Specification，预焊接工艺规程）草案生成的智能系统。

系统定位不是替代焊接工程师签发正式 WPS，也不是替代 PQR/WPQR 工艺评定，而是通过字段确认、证据检索、候选推理、人机协同和全局审计，生成一份可追踪、可解释、可审查的 pWPS 草案。

---

## 1. 最终版核心约束

1. 前端统一使用 `pnpm`。
2. 后端统一使用 `uv`。
3. 字段定义、状态定义、API schema、Skill 输入输出统一使用 `Pydantic v2`。
4. 状态不使用裸字符串，统一使用 `StrEnum / Enum`。
5. 前端采用 `Next.js App Router + TypeScript + Tailwind CSS + shadcn/ui + TanStack Query`。
6. 后端采用 `FastAPI + LangGraph + Pydantic v2 + SQLAlchemy async + Alembic`。
7. MVP 使用 `PostgreSQL + Redis + Local FS`，后续阶段引入 `Qdrant / MinIO / MinerU / Docling / Reranker`。
8. Auto 和 Guided 共用同一套字段组确认工作流，只替换 `DecisionActor`。
9. LLM 不控制全局流程，只作为结构化 `Skill` 使用。
10. Prompt 属于 Skill，Workflow Node 不直接拼 Prompt。
11. 用户体验和多端适配是前端基础约束，不是后期优化。
12. 新包、新技术、新服务引入前必须先调查最佳实践和影响范围。
13. 避免碎片化开发，任何修改都要做影响分析。
14. 测试保护核心业务路径，但避免过度测试、重复测试和过时测试堆积。
15. AI 开发 Agent 必须遵循“理解需求 -> 查文档 -> 计划 -> 小步实现 -> 测试 -> 总结影响面”的流程。

---

## 2. 文件说明

| 文件 | 作用 |
|---|---|
| `requirements.md` | 产品需求、用户场景、MVP 范围、成功指标 |
| `architecture.md` | 系统架构、模块边界、项目结构、分层设计 |
| `tech_stack.md` | 技术选型、环境管理、基础服务、开发命令 |
| `development_stages.md` | 阶段化开发目标、技术增减、交付物、验收标准 |
| `data_schema.md` | Pydantic v2 数据模型、枚举状态、版本化字段 |
| `workflow.md` | LangGraph 主图、字段组子图、Auto/Guided 中断恢复 |
| `skill_design.md` | Skill 标准结构、Prompt 归属、版本管理、校验策略 |
| `knowledge_design.md` | KnowledgeService、统一 IR、证据归一化、RAG 演进 |
| `api_contract.md` | 前后端 API 契约、请求响应、状态转换、错误码 |
| `frontend_guidelines.md` | 用户友好、多端适配、字段确认工作台设计 |
| `engineering_principles.md` | 软件设计原则、新技术引入、修改影响分析、测试治理 |
| `ai_development_workflow.md` | AI 辅助开发工作流、任务拆解、实现约束、自查流程 |
| `change_management.md` | 变更管理、影响分析、文档同步、迁移策略 |
| `testing_strategy.md` | 测试分层、Mock LLM、避免过度测试、过时测试删除 |
| `observability.md` | 日志、TraceEvent、Skill 调用记录、调试与审计链路 |
| `security_and_safety.md` | 文件安全、Prompt Injection、防泄漏、领域风险边界 |
| `evaluation_plan.md` | 质量评估指标、数据集、人工评审、持续优化 |
| `template_profile_design.md` | 字段注册表、标准 Profile、企业模板、渲染模板边界 |
| `deployment_guide.md` | 本地开发、环境变量、迁移、部署和运行规则 |
| `AGENTS.md` | 面向 Codex / Claude Code / OpenCode 的执行约束 |
| `agent_progressive_disclosure.md` | Agent 指令渐进披露、根入口压缩、按需读取规则 |
| `agent_preservation_checklist.md` | Agent 规则保留检查清单、关键词检查、冲突检查 |
| `consistency_check.md` | 最终版一致性检查结果和后续维护规则 |

---

## 3. 推荐阅读顺序

```text
requirements.md
  -> architecture.md
  -> tech_stack.md
  -> development_stages.md
  -> data_schema.md
  -> workflow.md
  -> skill_design.md
  -> knowledge_design.md
  -> api_contract.md
  -> frontend_guidelines.md
  -> engineering_principles.md
  -> ai_development_workflow.md
  -> change_management.md
  -> testing_strategy.md
  -> observability.md
  -> security_and_safety.md
  -> evaluation_plan.md
  -> template_profile_design.md
  -> deployment_guide.md
  -> AGENTS.md
  -> agent_progressive_disclosure.md
  -> agent_preservation_checklist.md
```

---

## 4. 推荐开发顺序

```text
Phase 0：项目骨架与环境锁定
Phase 1：领域模型与 Schema
Phase 2：Auto CLI 最小闭环
Phase 3：FastAPI API 与持久化
Phase 4：Guided 中断恢复
Phase 5：前端字段确认工作台
Phase 6：本地文档检索与证据链增强
Phase 7：审计修复闭环
Phase 8：文档解析、向量库、对象存储
Phase 9：评估、观测、安全、部署增强
```

---

## 5. 给开发 Agent 的一句话

不要把系统做成一个“会聊天生成 pWPS 的大模型应用”。

要把它做成一个：

> 字段驱动、证据支撑、状态可恢复、Skill 可测试、流程可审计、前端用户友好、AI 开发可稳定协作的软件工程系统。
