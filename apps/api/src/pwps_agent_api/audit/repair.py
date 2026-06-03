from pwps_agent_api.fields import FieldRegistry
from pwps_agent_api.schemas import (
    AuditResult,
    AuditRuleType,
    FieldState,
    FieldStatus,
    FieldTarget,
)


def build_repair_targets(
    audit_result: AuditResult,
    registry: FieldRegistry,
    field_states: dict[str, FieldState],
    *,
    actionable_rule_types: set[AuditRuleType] | None = None,
) -> list[FieldTarget]:
    targets: list[FieldTarget] = []
    seen_groups: set[str] = set()
    for issue in audit_result.issues:
        group_name = issue.repair_target
        if (
            group_name is None
            or group_name in seen_groups
            or (actionable_rule_types is not None and issue.rule_type not in actionable_rule_types)
        ):
            continue

        group = registry.get_group(group_name)
        for field_name in issue.target_fields:
            field = field_states.get(field_name)
            if field is not None and field.group == group_name:
                field.status = FieldStatus.NEEDS_REPAIR

        targets.append(
            FieldTarget(
                group_name=group_name,
                fields=group.fields,
                reason=f"Repair {group.label}: {issue.description}",
                priority=group.confirmation_order,
                source_issue_id=issue.issue_id,
            )
        )
        seen_groups.add(group_name)
    return targets
