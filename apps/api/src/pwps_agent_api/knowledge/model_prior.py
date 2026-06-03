from dataclasses import dataclass
from datetime import UTC, datetime

from pwps_agent_api.schemas import Evidence, SourceType


@dataclass(frozen=True)
class ModelPriorKnowledgeService:
    provider_name: str = "model_prior"

    async def evidence_for_fields(self, target_fields: list[str]) -> list[Evidence]:
        retrieved_at = datetime.now(UTC).isoformat()
        return [
            Evidence(
                evidence_id=f"model-prior-{field_name}",
                source_type=SourceType.MODEL_PRIOR,
                source_title="Deterministic MVP model prior",
                source_ref="phase-2-auto-cli",
                content=f"MVP fallback prior for {field_name}; requires human review.",
                target_fields=[field_name],
                credibility=0.35,
                limitations="Model prior only; not a standard, PQR, WPQR, or enterprise source.",
                retrieved_at=retrieved_at,
                metadata={"provider": self.provider_name},
            )
            for field_name in target_fields
        ]
