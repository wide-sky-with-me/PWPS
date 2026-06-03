"""Tests for DecisionActor implementations."""

import pytest

from pwps_agent_api.actors.virtual import VirtualDecisionActor
from pwps_agent_api.schemas import (
    DecisionContext,
    DecisionType,
    RiskLevel,
)


@pytest.fixture
def virtual_actor() -> VirtualDecisionActor:
    return VirtualDecisionActor()


@pytest.fixture
def sample_context() -> DecisionContext:
    return DecisionContext(
        run_id="test-run-001",
        session_id="session-001",
        target_fields=["consumable", "current_range"],
        progress_summary={"confirmed_groups": [], "pending_groups": ["basic_condition_group"]},
        candidate_bundle={
            "consumable": [
                {
                    "value": "ER50-6",
                    "confidence": 0.85,
                    "reason": "Standard wire for Q345R GMAW",
                    "evidence_ids": ["ev-1"],
                    "risks": [],
                },
                {
                    "value": "ER50-7",
                    "confidence": 0.7,
                    "reason": "Alternative wire",
                    "evidence_ids": ["ev-2"],
                    "risks": ["Less common choice"],
                },
            ],
            "current_range": [
                {
                    "value": {"min": "180A", "max": "240A"},
                    "confidence": 0.8,
                    "reason": "Standard range for 1.2mm wire",
                    "evidence_ids": ["ev-3"],
                    "risks": [],
                },
            ],
        },
        evidence_summary=[
            {
                "source_type": "local_document",
                "source_title": "GMAW Reference",
                "content": "ER50-6 is standard for carbon steel",
            }
        ],
        risks=[],
        recommended_values={"consumable": "ER50-6"},
        discussion_history=[],
    )


class TestVirtualDecisionActor:
    async def test_decide_with_empty_candidates_returns_request_more_info(
        self, virtual_actor: VirtualDecisionActor
    ) -> None:
        context = DecisionContext(
            run_id="test-run-002",
            session_id="session-002",
            target_fields=["consumable"],
            progress_summary={},
            candidate_bundle={},
            evidence_summary=[],
            risks=[],
            recommended_values={},
            discussion_history=[],
        )
        result = await virtual_actor.decide(context)

        assert result.decision_type is DecisionType.REQUEST_MORE_INFO
        assert result.risk_level is RiskLevel.HIGH
        assert result.requires_replan is True

    async def test_fallback_decide_selects_first_candidate(
        self, virtual_actor: VirtualDecisionActor, sample_context: DecisionContext
    ) -> None:
        # Without LLM API key, should use fallback
        result = await virtual_actor.decide(sample_context)

        # Should select first candidate for each field
        assert result.decision_type is DecisionType.ACCEPT_RECOMMENDED
        assert result.selected_values["consumable"] == "ER50-6"
        assert result.selected_values["current_range"] == {"min": "180A", "max": "240A"}

    async def test_fallback_decide_with_empty_field_candidates(
        self, virtual_actor: VirtualDecisionActor
    ) -> None:
        context = DecisionContext(
            run_id="test-run-003",
            session_id="session-003",
            target_fields=["consumable"],
            progress_summary={},
            candidate_bundle={"consumable": []},
            evidence_summary=[],
            risks=[],
            recommended_values={},
            discussion_history=[],
        )
        result = await virtual_actor.decide(context)

        assert result.decision_type is DecisionType.REQUEST_MORE_INFO
        assert "No acceptable candidates" in result.reason

    async def test_actor_name(self, virtual_actor: VirtualDecisionActor) -> None:
        assert virtual_actor.actor_name == "virtual_decision_actor"

    async def test_decide_preserves_risks_from_candidates(
        self, virtual_actor: VirtualDecisionActor
    ) -> None:
        context = DecisionContext(
            run_id="test-run-004",
            session_id="session-004",
            target_fields=["consumable"],
            progress_summary={},
            candidate_bundle={
                "consumable": [
                    {
                        "value": "J422",
                        "confidence": 0.6,
                        "reason": "SMAW electrode",
                        "evidence_ids": [],
                        "risks": ["Not suitable for GMAW process"],
                    }
                ]
            },
            evidence_summary=[],
            risks=[],
            recommended_values={},
            discussion_history=[],
        )
        result = await virtual_actor.decide(context)

        assert "Not suitable for GMAW process" in result.concerns
