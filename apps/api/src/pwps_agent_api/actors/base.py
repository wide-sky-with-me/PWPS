"""Abstract base class for decision actors.

A DecisionActor evaluates candidate field values and produces a
DecisionResult.  The two concrete implementations are:

- VirtualDecisionActor: LLM-backed automated evaluation
- HumanDecisionActor: presents a PendingUserDecision to the frontend
  and blocks until the user submits their choice
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from pwps_agent_api.schemas import DecisionContext, DecisionResult


class DecisionActor(ABC):
    """Base class for all decision actors."""

    @property
    @abstractmethod
    def actor_name(self) -> str:
        """Human-readable identifier for this actor."""

    @abstractmethod
    async def decide(self, context: DecisionContext) -> DecisionResult:
        """Evaluate candidates and return a decision.

        Implementations MUST:
        - Only select values from the provided candidate bundle
        - Return REQUEST_MORE_INFO when no adequate candidate exists
        - Record risk level and concerns in the result
        """
