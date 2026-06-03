# pWPS Agent API 契约 api_contract.md

## 1. 文档定位

本文档定义前后端 API 契约。所有请求响应必须由 Pydantic v2 schema 定义，并通过 OpenAPI 暴露给前端。

---

## 2. API 原则

1. 后端是状态事实来源。
2. 前端不得猜测字段状态。
3. 所有 API 请求响应必须有 schema。
4. 状态值使用枚举，不使用随意字符串。
5. 业务错误返回结构化错误码。
6. API 变更必须更新文档、测试和前端类型。

---

## 3. 创建任务

```http
POST /api/runs
```

请求：

```json
{
  "input": "Q345R，12mm，对接焊，平焊，GMAW，生成 pWPS 草案",
  "mode": "auto",
  "attachments": []
}
```

响应：

```json
{
  "run_id": "run_001",
  "status": "initialized"
}
```

状态转换：

```text
none -> RunStatus.INITIALIZED
```

---

## 4. 获取任务状态

```http
GET /api/runs/{run_id}
```

响应：

```json
{
  "run_id": "run_001",
  "status": "field_confirming",
  "mode": "guided",
  "current_target": {
    "group_name": "consumable_group",
    "fields": ["filler_metal", "shielding_gas"]
  },
  "progress": {
    "confirmed_groups": ["basic_condition_group"],
    "remaining_groups": ["parameter_group", "thermal_group"]
  },
  "publishability": null
}
```

---

## 5. 获取当前确认卡片

```http
GET /api/runs/{run_id}/current-decision
```

仅当状态为 `WAITING_FOR_USER` 或 Guided 当前需要用户确认时返回。

当前实现会将 pending decision 持久化到 run 记录；进程重启后仍可通过该接口恢复当前确认卡片。

响应：

```json
{
  "run_id": "run_001",
  "session_id": "ds_001",
  "target_group": "consumable_group",
  "target_fields": ["filler_metal", "shielding_gas"],
  "summary": "...",
  "candidates": {},
  "evidence": [],
  "risks": [],
  "recommended": {}
}
```

当前实现每次提交后提交当前字段组，并推进到下一个 pending decision。所有字段组完成后执行全局审计和结构化输出。

---

## 6. 提交用户决策

```http
POST /api/runs/{run_id}/decision
```

请求：

```json
{
  "session_id": "ds_001",
  "decision_type": "choose_alternative",
  "selected_values": {
    "filler_metal": "ER50-6"
  },
  "comment": "先按这个生成草案"
}
```

响应：

```json
{
  "run_id": "run_001",
  "status": "field_confirming",
  "accepted": true
}
```

---

## 7. 获取输出

```http
GET /api/runs/{run_id}/outputs
```

响应：

```json
{
  "pwps": {},
  "field_report": {},
  "evidence_report": {},
  "risk_report": {},
  "discussion_trace": [],
  "publishability": "needs_confirmation"
}
```

---

## 8. 事件流

```http
GET /api/runs/{run_id}/events
```

用途：前端展示运行进度、Skill 状态、审计状态。

当前实现：

```text
Run TraceEvent 会发布到 Redis，并同时保存在 run 记录中。
GET /api/runs/{run_id}/events 优先读取 Redis 事件；若 Redis 中无事件，则回退到持久化 trace。
```

事件示例：

```json
{
  "event": "generate_candidates",
  "summary": "已为焊材字段组生成候选值",
  "created_at": "2026-06-01T00:00:00Z"
}
```

---

## 9. 文档上传

```http
POST /api/documents/upload
```

MVP 可只保存文件元数据和本地路径。后续进入 ingestion worker。

---

## 10. 错误结构

```json
{
  "error_code": "RUN_NOT_FOUND",
  "message": "Run not found.",
  "details": {}
}
```

常见错误码：

```text
RUN_NOT_FOUND
INVALID_STATE_TRANSITION
DECISION_SESSION_EXPIRED
SCHEMA_VALIDATION_ERROR
WORKFLOW_INTERRUPTED
AUDIT_BLOCKED
UNSUPPORTED_FILE_TYPE
```

---

## 11. API 变更规则

任何 API 变更必须同步：

```text
Pydantic schema
OpenAPI
前端 API client
测试
api_contract.md
AGENTS.md 如涉及开发约束
```
