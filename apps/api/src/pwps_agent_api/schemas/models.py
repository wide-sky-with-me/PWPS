from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from pwps_agent_api.schemas.enums import (
    AuditRuleType,
    ConfirmationPolicy,
    DecisionType,
    FieldStatus,
    FieldType,
    InferencePolicy,
    Mode,
    Publishability,
    RiskLevel,
    RunStatus,
    SourceType,
    TargetType,
)

FieldValue = str | int | float | bool | list[Any] | dict[str, Any] | None


class KnowledgeQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_fields: list[str]
    query: str = ""
    preferred_sources: list[SourceType] = Field(default_factory=list)
    purpose: str = "support field candidate generation"
    context: dict[str, Any] = Field(default_factory=dict)


class KnowledgeHit(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_type: SourceType
    source_id: str
    title: str
    source_ref: str | None = None
    section_path: list[str] = Field(default_factory=list)
    content: str
    target_fields: list[str]
    page: int | None = None
    table_id: str | None = None
    score: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    limitations: str | None = None


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


class FieldState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    group: str
    value: FieldValue = None
    status: FieldStatus = FieldStatus.UNKNOWN

    source_type: SourceType | None = None
    inference_policy: InferencePolicy

    candidates: list[dict[str, Any]] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)

    confidence: float | None = Field(default=None, ge=0, le=1)
    risk_level: RiskLevel = RiskLevel.LOW
    needs_human_confirmation: bool = False

    discussion_session_id: str | None = None
    updated_at: str | None = None

    schema_version: str = "1.0.0"


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
    metadata: dict[str, Any] = Field(default_factory=dict)
    evidence_version: str = "1.0.0"


class DecisionContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    session_id: str
    target_fields: list[str]
    progress_summary: dict[str, Any]
    candidate_bundle: dict[str, Any]
    evidence_summary: list[dict[str, Any]]
    risks: list[dict[str, Any]]
    recommended_values: dict[str, Any]
    discussion_history: list[dict[str, Any]]


class DecisionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision_type: DecisionType
    selected_values: dict[str, Any] = Field(default_factory=dict)
    reason: str
    concerns: list[str] = Field(default_factory=list)
    risk_level: RiskLevel = RiskLevel.MEDIUM
    requires_replan: bool = False


class DiscussionRound(BaseModel):
    model_config = ConfigDict(extra="forbid")

    round_index: int
    decision: DecisionResult
    evaluation: dict[str, Any]
    system_response: str | None = None
    created_at: str


class DiscussionSession(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: str
    target_fields: list[str]
    actor_type: Mode
    progress_summary: dict[str, Any]
    rounds: list[DiscussionRound] = Field(default_factory=list)
    max_rounds: int = 5
    final_decision: DecisionResult | None = None
    closed_reason: str | None = None


class AuditIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    issue_id: str
    rule_type: AuditRuleType
    severity: RiskLevel
    target_fields: list[str]
    description: str
    recommended_action: str
    repair_target: str | None = None
    source_rule: str


class AuditResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    publishability: Publishability
    issues: list[AuditIssue] = Field(default_factory=list)
    summary: str
    audit_version: str = "1.0.0"


class FieldTarget(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_type: TargetType = TargetType.FIELD_GROUP
    group_name: str
    fields: list[str]
    reason: str
    priority: int = 0
    source_issue_id: str | None = None


class TraceEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event: str
    summary: str
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: str


class SkillCallRecord(BaseModel):
    """Detailed record of a single Skill invocation for observability."""

    model_config = ConfigDict(extra="forbid")

    skill_name: str
    skill_version: str
    prompt_version: str
    model_name: str | None = None
    input_hash: str | None = None
    output_hash: str | None = None
    validation_status: str = "ok"
    latency_ms: int | None = None
    created_at: str


class PendingUserDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    session_id: str
    target_group: str
    target_fields: list[str]
    summary: str
    candidates: dict[str, list[dict[str, Any]]] = Field(default_factory=dict)
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    risks: list[dict[str, Any]] = Field(default_factory=list)
    recommended: dict[str, Any] = Field(default_factory=dict)
    created_at: str
    expires_at: str | None = None


class WorkflowState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    status: RunStatus
    raw_input: str
    normalized_input: dict[str, Any] | None = None
    mode: Mode | None = None

    field_states: dict[str, FieldState] = Field(default_factory=dict)
    target_queue: list[FieldTarget] = Field(default_factory=list)
    current_target: FieldTarget | None = None

    evidence_store: dict[str, Evidence] = Field(default_factory=dict)
    field_evidence_map: dict[str, list[str]] = Field(default_factory=dict)
    repair_targets: list[FieldTarget] = Field(default_factory=list)

    discussion_sessions: list[DiscussionSession] = Field(default_factory=list)
    current_discussion_id: str | None = None

    audit_result: AuditResult | None = None
    final_output: dict[str, Any] | None = None

    trace: list[TraceEvent] = Field(default_factory=list)
    skill_calls: list[SkillCallRecord] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)

    schema_version: str = "1.0.0"
    field_registry_version: str = "1.0.0"
    workflow_version: str = "1.0.0"
    skill_versions: dict[str, str] = Field(default_factory=dict)
