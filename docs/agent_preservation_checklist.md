# Agent 规则保留检查清单

本文件用于在重构 `AGENTS.md`、移动规则或新增任务文档后，验证关键规则没有丢失。

## 1. 常驻规则检查

检查 `AGENTS.md` 是否仍明确包含：

- [ ] 前端只使用 `pnpm`。
- [ ] 后端只使用 `uv`。
- [ ] 字段、状态、API、Skill schema 统一使用 `Pydantic v2`。
- [ ] 状态使用 `StrEnum / Enum`，禁止裸字符串状态。
- [ ] Auto / Guided 共用同一字段确认工作流。
- [ ] Workflow Node 不直接拼 Prompt。
- [ ] Prompt 属于 Skill。
- [ ] LLM 不控制全局流程。
- [ ] KnowledgeService 不直接决定字段值。
- [ ] AuditEngine 不完全依赖 LLM。
- [ ] 前端必须考虑用户友好和多端适配。
- [ ] 新依赖引入前必须做最佳实践调查和影响分析。
- [ ] 禁止临时 patch 绕过核心规则。
- [ ] 测试避免过度测试，过时测试及时删除。

## 2. 路由表检查

检查 `AGENTS.md` 是否能路由到：

- [ ] `requirements.md`
- [ ] `architecture.md`
- [ ] `tech_stack.md`
- [ ] `development_stages.md`
- [ ] `data_schema.md`
- [ ] `workflow.md`
- [ ] `skill_design.md`
- [ ] `knowledge_design.md`
- [ ] `api_contract.md`
- [ ] `frontend_guidelines.md`
- [ ] `engineering_principles.md`
- [ ] `ai_development_workflow.md`
- [ ] `change_management.md`
- [ ] `testing_strategy.md`
- [ ] `observability.md`
- [ ] `security_and_safety.md`
- [ ] `evaluation_plan.md`
- [ ] `template_profile_design.md`
- [ ] `deployment_guide.md`
- [ ] `agent_progressive_disclosure.md`
- [ ] `consistency_check.md`

## 3. 关键词保留检查

重构后至少搜索以下关键词，确认仍能找到明确规则：

```text
pnpm
uv
Pydantic v2
StrEnum
DecisionActor
WorkflowState
Field Registry
Prompt 属于 Skill
KnowledgeService
AuditEngine
多端适配
最佳实践调查
影响分析
过时测试
Prompt Injection
publishability
```

## 4. 冲突检查

检查是否存在以下冲突：

- [ ] 同时要求 `pnpm` 和 `npm/yarn`。
- [ ] 同时要求 `uv` 和 `pip/poetry/conda` 管理项目依赖。
- [ ] 同时要求 Pydantic v2 和 dataclass/Literal 作为主模型。
- [ ] 同时要求状态裸字符串和枚举状态。
- [ ] 同时要求 Auto / Guided 分离流程和统一流程。
- [ ] 同时允许 Workflow Node 拼 Prompt 和禁止拼 Prompt。
- [ ] 同时允许 LLM 控制流程和要求确定性 Workflow。

## 5. 文档变更后必做

当新增、删除、重命名文档时：

1. 更新 `README.md` 文件清单。
2. 更新 `AGENTS.md` 路由表。
3. 更新本检查清单。
4. 更新 `consistency_check.md`。
5. 重新打包最终文档。

## 6. 本次检查结果记录模板

```text
检查日期：
变更摘要：
新增文档：
删除/重命名文档：
常驻规则是否完整：
路由表是否完整：
关键词检查结果：
冲突检查结果：
剩余风险：
```
