"""CLI script to ingest documents into the Milvus vector store.

Usage:
    uv run python -m pwps_agent_api.cli.ingest --source data/knowledge_base/local_documents.json
    uv run python -m pwps_agent_api.cli.ingest --source /path/to/docs/
"""

import argparse
import asyncio
import json
from pathlib import Path

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pydantic import TypeAdapter
from pymilvus import (  # type: ignore[import-untyped]
    CollectionSchema,
    DataType,
    FieldSchema,
    MilvusClient,
)

from pwps_agent_api.core.config import get_settings
from pwps_agent_api.core.llm import get_embedding_model
from pwps_agent_api.schemas import KnowledgeHit

_COLLECTION = "pwps_knowledge"
_CHUNK_SIZE = 500
_CHUNK_OVERLAP = 50


async def ingest(source: Path) -> None:
    settings = get_settings()
    if not settings.embedding_api_key:
        print("ERROR: EMBEDDING_API_KEY not set. Cannot ingest.")
        return

    documents = _load_documents(source)
    if not documents:
        print("No documents found to ingest.")
        return

    print(f"Loaded {len(documents)} document(s) from {source}")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=_CHUNK_SIZE,
        chunk_overlap=_CHUNK_OVERLAP,
    )
    chunks = splitter.split_documents(documents)
    print(f"Split into {len(chunks)} chunk(s)")

    # Embed all chunks
    embedding = get_embedding_model(settings)
    texts = [c.page_content for c in chunks]
    metadatas = [c.metadata for c in chunks]
    vectors = await embedding.aembed_documents(texts)
    dim = len(vectors[0])

    # Connect to Milvus
    client = MilvusClient(uri=settings.milvus_uri)

    if client.has_collection(_COLLECTION):
        client.drop_collection(_COLLECTION)
        print(f"Dropped existing collection '{_COLLECTION}'")

    # Create collection with explicit schema
    fields = [
        FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
        FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=dim),
        FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65535),
        FieldSchema(name="source_type", dtype=DataType.VARCHAR, max_length=64),
        FieldSchema(name="source_id", dtype=DataType.VARCHAR, max_length=256),
        FieldSchema(name="title", dtype=DataType.VARCHAR, max_length=512),
        FieldSchema(name="source_ref", dtype=DataType.VARCHAR, max_length=512),
        FieldSchema(name="section_path", dtype=DataType.VARCHAR, max_length=1024),
        FieldSchema(name="target_fields", dtype=DataType.VARCHAR, max_length=1024),
        FieldSchema(name="limitations", dtype=DataType.VARCHAR, max_length=2048),
    ]
    schema = CollectionSchema(fields=fields, enable_dynamic_field=True)
    client.create_collection(
        collection_name=_COLLECTION,
        schema=schema,
        metric_type="COSINE",
    )
    print(f"Created collection '{_COLLECTION}' (dim={dim})")

    # Create index on vector field
    index_params = client.prepare_index_params()
    index_params.add_index(
        field_name="vector",
        index_type="AUTOINDEX",
        metric_type="COSINE",
    )
    client.create_index(
        collection_name=_COLLECTION,
        index_params=index_params,
    )

    # Insert data
    data = [
        {
            "vector": vec,
            "text": text,
            "source_type": meta.get("source_type", ""),
            "source_id": meta.get("source_id", ""),
            "title": meta.get("title", ""),
            "source_ref": meta.get("source_ref", ""),
            "section_path": meta.get("section_path", ""),
            "target_fields": meta.get("target_fields", ""),
            "limitations": meta.get("limitations", ""),
        }
        for vec, text, meta in zip(vectors, texts, metadatas, strict=True)
    ]
    client.insert(collection_name=_COLLECTION, data=data)
    client.flush(_COLLECTION)
    client.load_collection(_COLLECTION)
    print(f"Ingested {len(data)} chunk(s) into Milvus")


def _load_documents(source: Path) -> list[Document]:
    if source.is_file():
        return _load_json_file(source)
    if source.is_dir():
        docs: list[Document] = []
        for json_file in sorted(source.glob("**/*.json")):
            docs.extend(_load_json_file(json_file))
        return docs
    print(f"Source not found: {source}")
    return []


def _load_json_file(path: Path) -> list[Document]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    hits = TypeAdapter(list[KnowledgeHit]).validate_python(raw)
    return [_hit_to_doc(hit) for hit in hits]


def _hit_to_doc(hit: KnowledgeHit) -> Document:
    metadata: dict[str, str] = {
        "source_type": hit.source_type.value,
        "source_id": hit.source_id,
        "title": hit.title,
        "source_ref": hit.source_ref or "",
        "limitations": hit.limitations or "",
    }
    if hit.section_path:
        metadata["section_path"] = ",".join(hit.section_path)
    if hit.target_fields:
        metadata["target_fields"] = ",".join(hit.target_fields)
    return Document(page_content=hit.content, metadata=metadata)


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest documents into the Milvus vector store.")
    parser.add_argument(
        "--source",
        required=True,
        type=Path,
        help="Path to a JSON file or directory of JSON files to ingest.",
    )
    args = parser.parse_args()
    asyncio.run(ingest(args.source))


if __name__ == "__main__":
    main()
