"""Automated evaluation runner for pWPS Agent.

Loads the evaluation dataset and measures:
- Field extraction accuracy
- Audit detection rate
- Publishability correctness

Usage:
    uv run python -m tests.eval.runner
"""

import asyncio
import json
from pathlib import Path
from typing import Any

from pwps_agent_api.audit.engine import AuditEngine
from pwps_agent_api.fields import load_default_field_registry
from pwps_agent_api.skills.requirement_understanding import RequirementUnderstandingSkill

DATASET_PATH = Path(__file__).parent / "dataset.json"


async def run_evaluation() -> dict[str, Any]:
    """Run evaluation against the dataset and return metrics."""
    dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    skill = RequirementUnderstandingSkill()
    registry = load_default_field_registry()
    audit = AuditEngine()

    results = []
    for case in dataset:
        case_result = await _evaluate_case(case, skill, registry, audit)
        results.append(case_result)

    # Compute aggregate metrics
    total = len(results)
    field_correct = sum(r["field_accuracy"] for r in results) / total
    audit_correct = sum(r["audit_correct"] for r in results) / total

    return {
        "total_cases": total,
        "field_extraction_accuracy": round(field_correct, 3),
        "audit_detection_accuracy": round(audit_correct, 3),
        "results": results,
    }


async def _evaluate_case(
    case: dict[str, Any],
    skill: RequirementUnderstandingSkill,
    registry: Any,
    audit: AuditEngine,
) -> dict[str, Any]:
    """Evaluate a single test case."""
    extracted = await skill.run(case["input"])

    # Field extraction accuracy
    expected_fields = case.get("expected_fields", {})
    correct = 0
    total = len(expected_fields)
    details = {}

    for field_name, expected_value in expected_fields.items():
        if expected_value is None:
            # Field should NOT be extracted
            is_correct = field_name not in extracted or extracted[field_name].value is None
        else:
            # Field should be extracted with correct value
            actual = extracted.get(field_name)
            is_correct = actual is not None and actual.value == expected_value

        actual_field = extracted.get(field_name)
        actual_value = actual_field.value if actual_field else None
        details[field_name] = {
            "expected": expected_value,
            "actual": actual_value,
            "correct": is_correct,
        }
        if is_correct:
            correct += 1

    field_accuracy = correct / total if total > 0 else 1.0

    # Audit detection (run audit on extracted fields)
    audit_result = audit.audit(extracted, registry)
    expected_issues = set(case.get("expected_audit_issues", []))
    actual_rules = {issue.source_rule for issue in audit_result.issues}

    # Check if expected audit issues are detected
    audit_correct = 1.0
    if expected_issues:
        detected = expected_issues.intersection(actual_rules)
        audit_correct = len(detected) / len(expected_issues)

    return {
        "case_id": case["id"],
        "category": case.get("category", "unknown"),
        "field_accuracy": field_accuracy,
        "audit_correct": audit_correct,
        "field_details": details,
        "actual_audit_rules": list(actual_rules),
        "expected_audit_rules": list(expected_issues),
    }


async def main() -> None:
    """Run evaluation and print results."""
    print("Running pWPS Agent evaluation...\n")
    results = await run_evaluation()

    print(f"Total cases: {results['total_cases']}")
    print(f"Field extraction accuracy: {results['field_extraction_accuracy']:.1%}")
    print(f"Audit detection accuracy: {results['audit_detection_accuracy']:.1%}")
    print()

    for r in results["results"]:
        status = "✓" if r["field_accuracy"] == 1.0 and r["audit_correct"] == 1.0 else "✗"
        print(f"  {status} {r['case_id']} ({r['category']})")
        if r["field_accuracy"] < 1.0:
            print(f"    Field accuracy: {r['field_accuracy']:.1%}")
        if r["audit_correct"] < 1.0:
            print(f"    Audit accuracy: {r['audit_correct']:.1%}")


if __name__ == "__main__":
    asyncio.run(main())
