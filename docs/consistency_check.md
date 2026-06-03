# 最终版一致性检查 consistency_check.md

## 1. 检查结论

已对最终版文档进行一致性检查，并修正了此前存在的关键不一致：

1. `data_schema.md` 中不再使用 `dataclass + Literal` 作为主模型定义，已统一为 `Pydantic v2 BaseModel + StrEnum`。
2. 状态定义已统一使用枚举，包括 `RunStatus`、`FieldStatus`、`DecisionType`、`Publishability`、`AuditRuleType`。
3. 前端包管理统一为 `pnpm`。
4. 后端包管理统一为 `uv`。
5. Auto / Guided 的统一抽象保持一致：共用字段确认工作流，只替换 `DecisionActor`。
6. `VirtualDecisionActor` 权限已收紧：只审候选、选候选、请求补证，不自由生成新字段。
7. `Prompt belongs to Skill` 已在 `architecture.md`、`skill_design.md`、`workflow.md`、`AGENTS.md` 中保持一致。
8. MVP 技术边界一致：PostgreSQL + Redis + Local FS；Qdrant / MinIO / MinerU / Docling 后续阶段引入。
9. 前端体验和多端适配已独立成文，并同步到 AGENTS 约束。
10. AI 开发稳定性相关规范已补齐：AI 开发工作流、变更管理、测试策略、可观测性、安全、评估。
11. 模板体系边界已补齐：Field Registry、Code Profile、Company Profile、Render Template 分层明确。
12. 部署运行边界已补齐：本地开发、环境变量、迁移、健康检查和生产禁区明确。

---

## 2. 关键概念对照

| 概念 | 最终约定 | 对应文档 |
|---|---|---|
| 前端包管理 | pnpm | tech_stack.md, AGENTS.md |
| 后端包管理 | uv | tech_stack.md, AGENTS.md |
| Schema | Pydantic v2 | data_schema.md |
| 状态 | StrEnum / Enum | data_schema.md |
| 工作流 | LangGraph 确定性主图 | workflow.md |
| LLM 能力 | Skill | skill_design.md |
| Prompt 归属 | Skill owns prompt | architecture.md, skill_design.md |
| Auto / Guided | DecisionActor 替换 | requirements.md, workflow.md |
| MVP 服务 | PostgreSQL + Redis + Local FS | tech_stack.md, development_stages.md |
| V1/V2 服务 | Qdrant / MinIO / MinerU / Docling | development_stages.md, knowledge_design.md |
| 前端形态 | 字段确认工作台 | frontend_guidelines.md |
| 模板体系 | Registry / Profile / Render Template 分层 | template_profile_design.md |
| 部署运行 | Local / staging / production 分层 | deployment_guide.md |
| AI 开发流程 | 小步计划 + 影响分析 + 测试 + 总结 | ai_development_workflow.md |

---

## 3. 已修正的不一致

### 3.1 Schema 定义方式

此前文档中存在 `dataclass + Literal` 示例，与“统一 Pydantic v2”的结论冲突。最终版已改为：

```text
BaseModel
Field
ConfigDict
StrEnum
```

### 3.2 状态比较方式

最终版统一为：

```python
if state.status is RunStatus.BLOCKED:
    ...
```

不推荐：

```python
if state.status == "blocked":
    ...
```

### 3.3 开发阶段

最终版阶段顺序统一为：

```text
Phase 0 项目骨架
Phase 1 领域模型
Phase 2 Auto CLI
Phase 3 API 与持久化
Phase 4 Guided 中断恢复
Phase 5 前端工作台
Phase 6 本地文档检索
Phase 7 审计修复
Phase 8 文档解析与向量库
Phase 9 评估观测安全部署
```

---

## 4. 后续维护规则

任何后续文档修改必须检查：

1. 是否改变技术栈。
2. 是否改变阶段划分。
3. 是否改变 schema。
4. 是否改变工作流。
5. 是否改变 API。
6. 是否改变 Skill 输入输出。
7. 是否需要同步 AGENTS.md。
8. 是否需要更新 consistency_check.md。

---

## 5. 当前文档状态

当前版本可以作为“完全版开发文档包”交给 Codex、Claude Code、OpenCode 或人工开发者使用。

建议后续不要继续大幅扩写，而是随着真实代码实现，把文档从“设计态”逐步更新为“实现态”。


---

## 渐进披露一致性检查

本最终版已按 Agent 指令渐进披露思想进行优化：

1. `AGENTS.md` 已从详细规则仓库调整为精简路由入口。
2. 高频、长期、必须始终遵守的规则保留在 `AGENTS.md`。
3. 前端、后端、Schema、Workflow、Skill、知识检索、测试、安全等任务细节由专项文档承载。
4. 新增 `agent_progressive_disclosure.md` 说明规则分类、下沉、读取和维护方式。
5. 新增 `agent_preservation_checklist.md` 用于检查规则迁移后是否丢失。
6. 保留旧版完整 Agent 规则快照 `AGENTS_full_legacy.md`，仅作为迁移备查，不作为开发入口。

后续维护要求：

```text
修改 AGENTS.md -> 必须检查 agent_preservation_checklist.md
新增文档 -> 必须更新 README.md 与 AGENTS.md 路由表
移动规则 -> 必须做关键词保留检查
发现冲突 -> 必须先解决冲突，再更新路由
```
