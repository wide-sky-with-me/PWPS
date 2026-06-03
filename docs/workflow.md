# pWPS Agent 工作流设计 workflow.md

## 1. 文档定位

本文档定义 pWPS Agent 的 LangGraph 主图、字段组确认子图、Auto/Guided 中断恢复、审计修复循环和 MVP 工作流边界。

---

## 2. 工作流原则

1. LangGraph 负责确定性编排。
2. LLM Skill 只在节点内部完成结构化任务。
3. DecisionActor 只负责字段确认决策。
4. KnowledgeService 负责检索，不负责字段最终选择。
5. AuditEngine 负责审计，不允许静默修复字段。
6. 草案输出发生在字段确认和全局审计之后。
7. 状态使用 Pydantic v2 模型，状态值使用枚举。

---

## 3. 顶层流程

```text
START
  -> normalize_input
  -> understand_requirement
  -> select_mode
  -> build_confirmation_queue
  -> pop_next_target
  -> confirm_target_subgraph
  -> after_target_confirmed
  -> global_audit
  -> build_repair_targets / finalize_output
  -> END
```

---

## 4. 主图节点职责

| 节点 | 职责 |
|---|---|
| normalize_input | 整理用户输入、附件、表单，生成统一任务对象 |
| understand_requirement | 调用 Skill 抽取字段并映射到 FieldState |
| select_mode | 确定 Auto 或 Guided 模式 |
| build_confirmation_queue | 根据字段状态和字段组依赖生成确认队列 |
| pop_next_target | 从队列取出下一个字段组 |
| confirm_target_subgraph | 执行字段组确认子图 |
| after_target_confirmed | 提交字段结果，判断是否继续确认 |
| global_audit | 全局冲突检测、字段审计、发布性评级 |
| build_repair_targets | 将审计问题转化为待修复字段组 |
| finalize_output | 生成结构化输出 |

---

## 5. 字段组确认子图

```text
summarize_progress
  -> plan_resolution
  -> execute_search
  -> collect_evidence
  -> generate_candidates
  -> ask_decision_actor
  -> evaluate_decision
  -> commit_values / discussion_round / replan / accept_last_with_risk
```

---

## 6. DecisionActor 统一抽象

```python
class DecisionActor:
    async def decide(self, context: DecisionContext) -> DecisionResult:
        raise NotImplementedError
```

### VirtualDecisionActor

用于 Auto Draft。

约束：

1. 只能基于候选值做选择、拒绝、要求补充信息或要求重新规划。
2. 不自由生成新字段值。
3. 不编造公司、客户、合同、编号等元信息。
4. 对低证据字段必须标记风险。
5. 硬冲突不能强行确认为 `CONFIRMED`。

### HumanDecisionActor

用于 Guided Draft。

职责：

1. 生成 pending decision。
2. 将候选、证据、风险展示给前端。
3. 等待用户提交。
4. 恢复工作流。

---

## 7. Guided 中断恢复

```text
ask_decision_actor
  -> HumanDecisionActor
  -> create PendingUserDecision
  -> state.status = RunStatus.WAITING_FOR_USER
  -> persist checkpoint
  -> frontend displays decision card
  -> user submits decision
  -> resume workflow
```

PendingUserDecision 必须持久化：

```text
run_id
session_id
target_fields
decision_card
created_at
expires_at(optional)
```

当前 MVP 实现将 `PendingUserDecision` 持久化到 run 记录，并在每次用户提交后恢复 `WorkflowState`、提交当前字段组、生成下一个 pending decision。字段组全部完成后进入全局审计和输出。

---

## 8. 审计规则分级

### Hard Rule

违反即 blocked 或 reference_only。

示例：

```text
GMAW + J422
元信息来自 model_prior
provided_only 字段被模型补全
```

### Risk Rule

不一定阻断，但必须降级并标记风险。

```text
PWHT 无证据
预热温度证据弱
高风险字段未人工确认
```

### Completeness Rule

字段缺失导致 needs_confirmation。

```text
缺少电流/电压/速度
缺少焊材
缺少焊接位置
```

---

## 9. 讨论轮次上限

单字段组默认最多 5 轮。

超过上限：

1. 普通低风险字段：可采纳最后意见并标记 high risk。
2. 高风险字段且存在硬冲突：不得确认为 `CONFIRMED`，应标记 `OVERRIDDEN_CONFLICT`。
3. `provided_only` 字段：不能由模型补全，只能留空、追问或 blocked。

---

## 10. MVP 工作流

MVP-0 保留：

```text
normalize_input
understand_requirement
select_mode
build_confirmation_queue
confirm_target_subgraph
global_audit
finalize_output
```

MVP-0 字段组：

```text
basic_condition_group
consumable_group
parameter_group
thermal_group
meta_group
```

MVP-0 审计规则：

```text
禁止推断字段检查
焊法与焊材匹配检查
关键字段缺失检查
高风险字段确认检查
参数完整性检查
```
