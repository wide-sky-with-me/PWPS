import json
from dataclasses import dataclass
from pathlib import Path

from pydantic import TypeAdapter

from pwps_agent_api.schemas import KnowledgeHit, KnowledgeQuery

DEFAULT_LOCAL_DOCUMENT_INDEX = (
    Path(__file__).resolve().parents[3] / "data" / "knowledge_base" / "local_documents.json"
)


@dataclass(frozen=True)
class LocalDocumentProvider:
    index_path: Path = DEFAULT_LOCAL_DOCUMENT_INDEX

    async def search(self, query: KnowledgeQuery) -> list[KnowledgeHit]:
        hits = TypeAdapter(list[KnowledgeHit]).validate_python(
            json.loads(self.index_path.read_text(encoding="utf-8"))
        )
        target_fields = set(query.target_fields)
        preferred_sources = set(query.preferred_sources)
        return [
            hit
            for hit in hits
            if target_fields.intersection(hit.target_fields)
            and (not preferred_sources or hit.source_type in preferred_sources)
        ]
