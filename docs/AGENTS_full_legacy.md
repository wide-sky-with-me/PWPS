# AGENTS.md - pWPS Agent 开发协作指南

## 1. 目标

本文件面向 Codex、Claude Code、OpenCode 或其他开发 Agent，用于约束实现 pWPS Agent 时的工程顺序、架构边界和禁止事项。

开发目标不是快速拼一个能聊天生成 pWPS 的 Demo，而是实现一个字段驱动、证据支撑、状态可恢复、可审计、可测试、用户友好的 pWPS 草案生成工作流系统。

---

## 2. 必须遵守的硬约束

1. 前端只能使用 pnpm，不使用 npm/yarn。
2. 后端只能使用 uv，不使用 pip/poetry/conda 管理项目依赖。
3. 字段、状态、API、Skill schema 使用 Pydantic v2。
4. 状态使用 StrEnum / Enum，禁止裸字符串状态。
5. Workflow Node 不直接拼 Prompt。
6. Prompt 属于 Skill。
7. LLM 不控制全局流程。
8. KnowledgeService 不直接决定字段值。
9. AuditEngine 不完全依赖 LLM。
10. Output Builder 不执行推理。
11. Render 模块不得修改字段事实。
12. 前端必须考虑用户友好和多端适配。
13. 新包、新技术、新服务引入前必须调查最佳实践和影响范围。
14. 不允许临时 patch 绕过领域规则。
15. 测试避免过度测试，过时测试及时删除。

---

## 3. 开发前阅读规则

按任务类型阅读对应文档：

```text
需求任务 -> requirements.md
架构任务 -> architecture.md, engineering_principles.md
技术栈任务 -> tech_stack.md
阶段任务 -> development_stages.md
Schema 任务 -> data_schema.md
Workflow 任务 -> workflow.md
Skill 任务 -> skill_design.md
知识检索任务 -> knowledge_design.md
API 任务 -> api_contract.md
前端任务 -> frontend_guidelines.md
测试任务 -> testing_strategy.md
安全任务 -> security_and_safety.md
模板任务 -> template_profile_design.md
部署任务 -> deployment_guide.md
AI 协作任务 -> ai_development_workflow.md, change_management.md
```

---

## 4. 推荐实现顺序

```text
Phase 0：项目骨架与环境锁定
Phase 1：Pydantic v2 领域模型
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

## 5. 禁止事项

禁止：

```text
一次性实现所有阶段
绕过 Field Registry
绕过 WorkflowState
绕过 Audit Engine
绕过 Pydantic schema
在前端写领域推理逻辑
把 Auto 和 Guided 写成两套流程
让 VirtualDecisionActor 自由生成字段
用 model_prior 填 company/client/contract_no
新增依赖不说明原因
为了通过测试删除关键测试
保留过时测试误导后续开发
```

---

## 6. 每次开发完成必须汇报

```text
完成了什么：
影响文件：
是否改变 schema：
是否改变 API：
是否改变 workflow：
是否新增依赖：
是否需要迁移：
运行测试：
剩余风险：
```

---

## 7. 最小开发命令

前端：

```bash
pnpm install
pnpm --filter web dev
pnpm --filter web lint
pnpm --filter web typecheck
```

后端：

```bash
cd apps/api
uv sync
uv run fastapi dev src/pwps_agent_api/main.py
uv run pytest
uv run ruff check .
uv run mypy .
```
