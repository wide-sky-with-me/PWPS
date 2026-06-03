# pWPS Agent 可观测性设计 observability.md

## 1. 文档定位

本文档定义日志、TraceEvent、Skill 调用记录、证据链、审计链路和调试策略。

---

## 2. 可观测性目标

系统必须能回答：

```text
这个字段为什么是这个值？
用了哪些证据？
哪个 Skill 生成的？
哪个 Actor 确认的？
用户是否覆盖过？
审计是否发现问题？
最终 publishability 为什么是 needs_confirmation？
```

---

## 3. Run Trace

每个 run 记录：

```text
run_id
input
mode
state transitions
field timeline
skill calls
evidence ids
decision history
audit issues
final output
versions
```

---

## 4. TraceEvent

```python
class TraceEvent(BaseModel):
    event: str
    summary: str
    payload: dict = {}
    created_at: str
```

典型事件：

```text
normalize_input
understand_requirement
build_confirmation_queue
plan_resolution
execute_search
collect_evidence
generate_candidates
ask_decision_actor
evaluate_decision
commit_values
global_audit
finalize_output
```

MVP API 实现中，TraceEvent 同时写入两处：

```text
Redis run event list      用于前端快速读取运行事件
RunRecord.trace_json      用于持久化回退和审计
```

---

## 5. Skill 调用记录

每次 Skill 调用记录：

```text
skill_name
skill_version
prompt_version
model_name
input_schema_version
output_schema_version
input_json
output_json
validation_status
latency_ms
error
```

敏感信息需要脱敏。

---

## 6. 前端状态可观测

前端应展示：

```text
当前运行状态
当前字段组
等待用户 / 正在生成 / 正在审计 / 已完成
错误提示
重试入口
```

不要只显示“加载中”。

---

## 7. 调试页面建议

开发环境可提供 Run Debug 页面：

```text
WorkflowState JSON
Trace timeline
Skill calls
Evidence list
Audit issues
Version info
```

生产环境需要权限控制。
