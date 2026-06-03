import json
from pathlib import Path

from pwps_agent_api.knowledge.local_document import LocalDocumentProvider
from pwps_agent_api.knowledge.normalizer import EvidenceNormalizer
from pwps_agent_api.knowledge.service import KnowledgeService
from pwps_agent_api.schemas import KnowledgeQuery, SourceType


async def test_local_document_provider_filters_hits_by_target_field_and_keeps_section(
    tmp_path: Path,
) -> None:
    index_path = tmp_path / "local_documents.json"
    index_path.write_text(
        json.dumps(
            [
                {
                    "source_type": "local_document",
                    "source_id": "doc-gmaw",
                    "title": "GMAW drafting reference",
                    "source_ref": "local://gmaw-reference",
                    "section_path": ["GMAW", "Consumables"],
                    "content": "ER50-6 is a candidate wire for this drafting example.",
                    "target_fields": ["consumable"],
                    "limitations": "Drafting reference only.",
                },
                {
                    "source_type": "local_document",
                    "source_id": "doc-thermal",
                    "title": "Thermal drafting reference",
                    "source_ref": "local://thermal-reference",
                    "section_path": ["Thermal"],
                    "content": "Review preheat against the governing standard.",
                    "target_fields": ["preheat_temperature"],
                    "limitations": "Does not replace engineering review.",
                },
            ]
        ),
        encoding="utf-8",
    )
    provider = LocalDocumentProvider(index_path=index_path)

    hits = await provider.search(KnowledgeQuery(target_fields=["consumable"]))

    assert len(hits) == 1
    assert hits[0].source_id == "doc-gmaw"
    assert hits[0].section_path == ["GMAW", "Consumables"]


async def test_evidence_normalizer_preserves_source_section_content_and_limitations() -> None:
    provider = LocalDocumentProvider()
    query = KnowledgeQuery(target_fields=["consumable"])

    hits = await provider.search(query)
    evidence = await EvidenceNormalizer().normalize(query, hits)

    assert evidence
    assert evidence[0].source_type is SourceType.LOCAL_DOCUMENT
    assert evidence[0].source_title
    assert evidence[0].section_path
    assert evidence[0].content
    assert evidence[0].limitations
    assert evidence[0].target_fields == ["consumable"]


async def test_knowledge_service_uses_model_prior_only_for_fields_without_local_evidence() -> None:
    evidence = await KnowledgeService().evidence_for_fields(["consumable", "unknown_field"])

    evidence_by_field = {
        field_name: [item for item in evidence if field_name in item.target_fields]
        for field_name in ["consumable", "unknown_field"]
    }
    assert {item.source_type for item in evidence_by_field["consumable"]} == {
        SourceType.LOCAL_DOCUMENT
    }
    assert {item.source_type for item in evidence_by_field["unknown_field"]} == {
        SourceType.MODEL_PRIOR
    }
