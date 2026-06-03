from enum import StrEnum


class RunStatus(StrEnum):
    INITIALIZED = "initialized"
    UNDERSTANDING = "understanding"
    FIELD_CONFIRMING = "field_confirming"
    WAITING_FOR_USER = "waiting_for_user"
    AUDITING = "auditing"
    FINALIZING = "finalizing"
    FINISHED = "finished"
    BLOCKED = "blocked"


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


class TargetType(StrEnum):
    FIELD_GROUP = "field_group"
