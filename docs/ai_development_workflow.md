# AI 辅助开发工作流 ai_development_workflow.md

## 1. 文档定位

本文档约束使用 Codex、Claude Code、OpenCode 或其他 AI Agent 进行开发时的流程，保证 AI 辅助开发不会破坏架构一致性。

---

## 2. 标准开发流程

每次任务必须遵循：

```text
理解需求
  -> 查阅相关文档
  -> 定位影响模块
  -> 制定小步计划
  -> 实现最小变更
  -> 运行相关测试
  -> 检查影响面
  -> 更新文档
  -> 输出变更总结
```

---

## 3. 开发前必须读取

根据任务类型读取：

```text
产品 / 功能：requirements.md, development_stages.md
架构 / 模块：architecture.md, engineering_principles.md
Schema / 状态：data_schema.md
工作流：workflow.md
Skill：skill_design.md
知识检索：knowledge_design.md
API：api_contract.md
前端：frontend_guidelines.md
测试：testing_strategy.md
安全：security_and_safety.md
```

---

## 4. AI Agent 禁止行为

1. 未读文档直接大范围修改。
2. 自行引入新框架、新数据库、新组件库。
3. 绕过 Pydantic schema。
4. 使用裸字符串状态。
5. 在 workflow node 中直接拼 prompt。
6. 让前端实现领域推理。
7. 静默删除测试。
8. 为了让测试过而降低测试价值。
9. 不说明影响面的重构。
10. 一次性改动多个无关模块。

---

## 5. 任务拆分原则

AI 任务应尽量小步：

```text
一个任务只完成一个明确目标。
一个任务尽量只影响一个层级。
涉及 schema/workflow/api 的任务必须单独处理。
```

不推荐任务：

```text
“把整个系统实现了”
“顺便优化一下所有代码”
“把前后端都接上”
```

推荐任务：

```text
“实现 FieldSpec 和 FieldState Pydantic 模型，并补测试”
“实现 build_confirmation_queue 的纯函数和测试”
“实现 POST /api/runs 的 schema 和空流程持久化”
```

---

## 6. 变更总结模板

每次 AI 开发完成后必须输出：

```text
完成了什么：
影响了哪些文件：
是否改变 schema：
是否改变 API：
是否改变 workflow：
是否新增依赖：
运行了哪些测试：
剩余风险：
```

---

## 7. 不确定时的处理

AI 不确定时，不应直接猜测实现。应：

1. 先查文档。
2. 查代码中的现有抽象。
3. 给出最小假设。
4. 在变更总结中标记不确定点。
5. 避免做不可逆的大改。


---

## 附：渐进披露读取规则

AI 开发 Agent 不应把所有文档一次性加载进上下文。每次任务应先读取 `AGENTS.md`，再根据路由表读取必要文档。

任务读取策略：

```text
简单前端任务：AGENTS.md + frontend_guidelines.md + api_contract.md
Schema 任务：AGENTS.md + data_schema.md + consistency_check.md
Workflow 任务：AGENTS.md + workflow.md + data_schema.md + skill_design.md
Skill 任务：AGENTS.md + skill_design.md + testing_strategy.md
知识检索任务：AGENTS.md + knowledge_design.md + security_and_safety.md
依赖引入任务：AGENTS.md + tech_stack.md + engineering_principles.md + change_management.md
```

若发现 `AGENTS.md` 膨胀，应按 `agent_progressive_disclosure.md` 进行重构，并用 `agent_preservation_checklist.md` 验证规则未丢失。
