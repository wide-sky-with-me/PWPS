# 变更管理与影响分析 change_management.md

## 1. 文档定位

本文档定义代码、Schema、API、Workflow、Skill、数据库和文档变更的管理规则。

---

## 2. 变更类型

```text
Feature Change      新功能
Bug Fix             缺陷修复
Schema Change       数据结构变更
Workflow Change     工作流变更
API Change          接口变更
Dependency Change   依赖变更
Migration Change    数据库迁移
Prompt/Skill Change Skill 行为变更
Refactor            重构
```

---

## 3. 修改前检查清单

任何修改前必须回答：

```text
1. 这次修改解决什么问题？
2. 影响哪些模块？
3. 是否改变 Pydantic schema？
4. 是否改变 API contract？
5. 是否改变 WorkflowState？
6. 是否改变字段注册表？
7. 是否改变 Skill 输入输出？
8. 是否需要数据库迁移？
9. 是否需要更新测试？
10. 是否需要更新文档？
11. 是否影响前端多端体验？
12. 是否影响安全边界？
```

---

## 4. 高风险变更

以下变更必须单独处理，不要和其他功能混在一起：

```text
FieldSpec / FieldState
WorkflowState
DecisionActor
Skill schema
AuditRule
KnowledgeService
API contract
DB models / Alembic migration
Run persistence
```

---

## 5. 数据迁移规则

1. 数据库结构变更必须走 Alembic。
2. WorkflowState JSONB 结构变更必须提升 schema_version。
3. Field Registry 变更必须提升 field_registry_version。
4. Skill 输入输出变更必须提升 skill_version 或 schema_version。
5. 旧 run 的恢复策略必须说明。

---

## 6. 文档同步规则

变更后必须同步相关文档：

```text
API -> api_contract.md
Schema -> data_schema.md
Workflow -> workflow.md
Skill -> skill_design.md
技术栈 -> tech_stack.md
测试 -> testing_strategy.md
安全 -> security_and_safety.md
AI 开发约束 -> AGENTS.md
```

---

## 7. 回滚策略

每次高风险变更必须说明：

```text
如何回滚代码？
如何回滚数据库？
是否影响已创建 run？
是否需要兼容旧 schema？
```


---

## Agent 指令变更管理

修改 `AGENTS.md`、新增规则文档、移动规则时，也必须走变更管理。

变更前回答：

```text
这条规则是否应该常驻？
是否已有同类规则？
会不会与现有技术栈、Schema、Workflow、测试、安全约束冲突？
移动后 AGENTS.md 是否仍能路由到它？
是否更新了 agent_preservation_checklist.md？
```

变更后执行：

```text
读取新的 AGENTS.md
检查路由表
搜索关键词
检查冲突
记录到 consistency_check.md
```
