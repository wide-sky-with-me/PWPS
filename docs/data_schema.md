# pWPS Agent 数据模型设计 data_schema.md

## 1. 文档定位

本文档定义 pWPS Agent 的核心数据结构。最终版统一使用 Pydantic v2，不再使用 dataclass 作为领域模型主定义，不使用裸字符串表示状态。

---

## 2. 基础约束

1. 所有跨模块传递的数据结构使用 `pydantic.BaseModel`。
2. 所有状态、模式、策略、评级使用 `StrEnum / Enum`。
3. 禁止在业务代码中使用裸字符串状态比较。
4. 所有可持久化对象包含版本字段。
5. LLM Skill 的输入输出也必须使用 Pydantic v2 schema。

示例：

```python
from enum import StrEnum
from pydantic import BaseModel, Field, ConfigDict

class RunStatus(StrEnum):
    INITIALIZED = "initialized"
    UNDERSTANDING = "understanding"
    FIELD_CONFIRMING = "field_confirming"
    WAITING_FOR_USER = "waiting_for_user"
    AUDITING = "auditing"
    FINALIZING = "finalizing"
    FINISHED = "finished"
    BLOCKED = "blocked"

# 推荐
if state.status is RunStatus.BLOCKED:
    ...

# 禁止
if state.status == "blocked":
    ...
```

---

## 3. 枚举定义

```python
from enum import StrEnum

class Mode(StrEnum):
    AUTO = "auto"
    GUIDED = "guided"

class FieldType(StrEnum):
    STRING = "string"
    NUMBER = "number"
    RANGE = "range"
    ENUM = "enum"
    LIST = "list"
    BOOLEAN = "boolean"
    TEMPERATURE = "temperature"
    DIMENSION = "dimension"
    TEXT = "text"

class FieldStatus(StrEnum):
    UNKNOWN = "unknown"
    PROVIDED = "provided"
    CANDIDATE_GENERATED = "candidate_generated"
    DISCUSSING = "discussing"
    CONFIRMED = "confirmed"
    AUDITED = "audited"
    OVERRIDDEN = "overridden"
    OVERRIDDEN_CONFLICT = "overridden_conflict"
    BLOCKED = "blocked"
    CONFLICT = "conflict"
    NEEDS_REPAIR = "needs_repair"

class SourceType(StrEnum):
    USER_INPUT = "user_input"
    LOCAL_STANDARD = "local_standard"
    ENTERPRISE_STANDARD = "enterprise_standard"
    STRUCTURED_KB = "structured_kb"
    HISTORY_WPS = "history_wps"
    HISTORY_PQR = "history_pqr"
    LOCAL_DOCUMENT = "local_document"
    TEXTBOOK_OR_HANDBOOK = "textbook_or_handbook"
    WEB = "web"
    MODEL_PRIOR = "model_prior"

class InferencePolicy(StrEnum):
    PROVIDED_ONLY = "provided_only"
    EVIDENCE_REQUIRED = "evidence_required"
    MODEL_ALLOWED = "model_allowed"
    DERIVED = "derived"

class ConfirmationPolicy(StrEnum):
    AUTO_CONFIRM_IF_HIGH_CONFIDENCE = "auto_confirm_if_high_confidence"
    ALWAYS_CONFIRM = "always_confirm"
    CONFIRM_IF_LOW_EVIDENCE = "confirm_if_low_evidence"
    CONFIRM_IF_USER_MISSING = "confirm_if_user_missing"
    NEVER_INFER = "never_infer"

class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class DecisionType(StrEnum):
    ACCEPT_RECOMMENDED = "accept_recommended"
    CHOOSE_ALTERNATIVE = "choose_alternative"
    OVERRIDE = "override"
    REQUEST_MORE_INFO = "request_more_info"
    REJECT = "reject"

class Publishability(StrEnum):
    DRAFT_PUBLISHABLE = "draft_publishable"
    NEEDS_CONFIRMATION = "needs_confirmation"
    REFERENCE_ONLY = "reference_only"
    BLOCKED = "blocked"

class AuditRuleType(StrEnum):
    HARD = "hard"
    RISK = "risk"
    COMPLETENESS = "completeness"
```

---

## 4. 字段注册表

```python
from pydantic import BaseModel, Field, ConfigDict

class FieldSpec(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    label: str
    group: str
    field_type: FieldType
    description: str

    unit: str | None = None
    enum_values: list[str] = Field(default_factory=list)

    required_for_start: bool = False
    required_for_draft: bool = False
    high_risk: bool = False

    inference_policy: InferencePolicy = InferencePolicy.MODEL_ALLOWED
    confirmation_policy: ConfirmationPolicy = ConfirmationPolicy.CONFIRM_IF_LOW_EVIDENCE

    dependencies: list[str] = Field(default_factory=list)
    affects: list[str] = Field(default_factory=list)

    output_section: str | None = None
    audit_rules: list[str] = Field(default_factory=list)
    candidate_strategy: str | None = None
    examples: list[str] = Field(default_factory=list)

    field_registry_version: str = "1.0.0"
```

---

## 5. 字段组定义

```python
class FieldGroupSpec(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    label: str
    description: str

    fields: list[str]
    required_fields: list[str] = Field(default_factory=list)
    optional_fields: list[str] = Field(default_factory=list)

    depends_on_groups: list[str] = Field(default_factory=list)
    confirmation_order: int = 0

    can_confirm_together: bool = True
    allow_partial_commit: bool = True
    max_discussion_rounds: int = 5
    audit_after_commit: bool = True
```

---

## 6. 字段状态

```python
class FieldState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    group: str
    value: str | int | float | bool | list | dict | None = None
    status: FieldStatus = FieldStatus.UNKNOWN

    source_type: SourceType | None = None
    inference_policy: InferencePolicy

    candidates: list[dict] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)

    confidence: float | None = Field(default=None, ge=0, le=1)
    risk_level: RiskLevel = RiskLevel.LOW
    needs_human_confirmation: bool = False

    discussion_session_id: str | None = None
    updated_at: str | None = None

    schema_version: str = "1.0.0"
```

---

## 7. 证据对象

```python
class Evidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence_id: str
    source_type: SourceType
    source_title: str
    source_ref: str | None = None
    section_path: list[str] = Field(default_factory=list)
    content: str

    target_fields: list[str]
    credibility: float = Field(ge=0, le=1)
    limitations: str | None = None

    retrieved_at: str
    metadata: dict = Field(default_factory=dict)
    evidence_version: str = "1.0.0"
```

---

## 8. 决策对象

```python
class DecisionContext(BaseModel):
    run_id: str
    session_id: str
    target_fields: list[str]
    progress_summary: dict
    candidate_bundle: dict
    evidence_summary: list[dict]
    risks: list[dict]
    recommended_values: dict
    discussion_history: list[dict]

class DecisionResult(BaseModel):
    decision_type: DecisionType
    selected_values: dict = Field(default_factory=dict)
    reason: str
    concerns: list[str] = Field(default_factory=list)
    risk_level: RiskLevel = RiskLevel.MEDIUM
    requires_replan: bool = False
```

---

## 9. 讨论记录

```python
class DiscussionRound(BaseModel):
    round_index: int
    decision: DecisionResult
    evaluation: dict
    system_response: str | None = None
    created_at: str

class DiscussionSession(BaseModel):
    session_id: str
    target_fields: list[str]
    actor_type: Mode
    progress_summary: dict
    rounds: list[DiscussionRound] = Field(default_factory=list)
    max_rounds: int = 5
    final_decision: DecisionResult | None = None
    closed_reason: str | None = None
```

---

## 10. 审计对象

```python
class AuditIssue(BaseModel):
    issue_id: str
    rule_type: AuditRuleType
    severity: RiskLevel
    target_fields: list[str]
    description: str
    recommended_action: str
    repair_target: str | None = None
    source_rule: str

class AuditResult(BaseModel):
    publishability: Publishability
    issues: list[AuditIssue] = Field(default_factory=list)
    summary: str
    audit_version: str = "1.0.0"
```

---

## 11. 工作流状态

```python
class FieldTarget(BaseModel):
    target_type: str = "field_group"
    group_name: str
    fields: list[str]
    reason: str
    priority: int = 0
    source_issue_id: str | None = None

class TraceEvent(BaseModel):
    event: str
    summary: str
    payload: dict = Field(default_factory=dict)
    created_at: str

class WorkflowState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    status: RunStatus
    raw_input: str
    normalized_input: dict | None = None
    mode: Mode | None = None

    field_states: dict[str, FieldState] = Field(default_factory=dict)
    target_queue: list[FieldTarget] = Field(default_factory=list)
    current_target: FieldTarget | None = None

    evidence_store: dict[str, Evidence] = Field(default_factory=dict)
    field_evidence_map: dict[str, list[str]] = Field(default_factory=dict)

    discussion_sessions: list[DiscussionSession] = Field(default_factory=list)
    current_discussion_id: str | None = None

    audit_result: AuditResult | None = None
    final_output: dict | None = None

    trace: list[TraceEvent] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)

    schema_version: str = "1.0.0"
    field_registry_version: str = "1.0.0"
    workflow_version: str = "1.0.0"
    skill_versions: dict[str, str] = Field(default_factory=dict)
```

---

## 12. 数据库映射建议

```text
runs
  run_id
  status
  mode
  raw_input
  workflow_state_jsonb
  schema_version
  created_at
  updated_at

field_states
  run_id
  field_name
  group_name
  status
  source_type
  value_jsonb
  evidence_ids_jsonb
  risk_level

skill_calls
  run_id
  skill_name
  skill_version
  input_jsonb
  output_jsonb
  validation_status

evidence
  evidence_id
  run_id
  source_type
  source_title
  source_ref
  content
  metadata_jsonb

audit_issues
  issue_id
  run_id
  rule_type
  severity
  target_fields_jsonb
  repair_target
```

---

## 13. 版本化要求

每个 Run 必须记录：

```text
schema_version
field_registry_version
workflow_version
skill_versions
prompt_versions
template_version
```

这用于后续复现、调试、旧任务恢复和评估对比。
