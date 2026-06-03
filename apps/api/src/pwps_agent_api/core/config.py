import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# Load .env from monorepo root
_env_path = Path(__file__).resolve().parents[5] / ".env"
if _env_path.exists():
    load_dotenv(_env_path)


@dataclass(frozen=True)
class Settings:
    database_url: str
    redis_url: str
    local_artifact_dir: Path

    # LLM
    llm_provider: str  # "deepseek" | "openai"
    llm_api_key: str
    llm_base_url: str
    llm_model: str
    llm_temperature: float

    # Embedding (SiliconFlow)
    embedding_api_key: str
    embedding_base_url: str
    embedding_model: str

    # Reranker (SiliconFlow)
    reranker_api_key: str
    reranker_base_url: str
    reranker_model: str

    # Milvus
    milvus_uri: str

    # CORS
    cors_origins: list[str]


def get_settings() -> Settings:
    return Settings(
        database_url=os.getenv(
            "DATABASE_URL",
            "postgresql+asyncpg://pwps:pwps@localhost:5432/pwps_agent",
        ),
        redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
        local_artifact_dir=Path(os.getenv("LOCAL_ARTIFACT_DIR", "./storage/artifacts")),
        # LLM
        llm_provider=os.getenv("LLM_PROVIDER", "deepseek"),
        llm_api_key=os.getenv("LLM_API_KEY", ""),
        llm_base_url=os.getenv("LLM_BASE_URL", "https://api.deepseek.com"),
        llm_model=os.getenv("LLM_MODEL", "deepseek-v4-flash"),
        llm_temperature=float(os.getenv("LLM_TEMPERATURE", "0")),
        # Embedding
        embedding_api_key=os.getenv("EMBEDDING_API_KEY", ""),
        embedding_base_url=os.getenv("EMBEDDING_BASE_URL", "https://api.siliconflow.cn/v1"),
        embedding_model=os.getenv("EMBEDDING_MODEL", "Qwen/Qwen3-Embedding-0.6B"),
        # Reranker
        reranker_api_key=os.getenv("RERANKER_API_KEY", ""),
        reranker_base_url=os.getenv("RERANKER_BASE_URL", "https://api.siliconflow.cn/v1"),
        reranker_model=os.getenv("RERANKER_MODEL", "BAAI/bge-reranker-v2-m3"),
        # Milvus
        milvus_uri=os.getenv("MILVUS_URI", "http://localhost:19530"),
        # CORS
        cors_origins=os.getenv(
            "CORS_ORIGINS",
            "http://localhost:3000,http://127.0.0.1:3000",
        ).split(","),
    )
