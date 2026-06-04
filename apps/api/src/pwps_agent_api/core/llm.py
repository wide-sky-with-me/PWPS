"""LLM and Embedding model factory.

Provider-aware factory that returns the correct LangChain model class
based on the LLM_PROVIDER setting:

    deepseek  -> langchain_deepseek.ChatDeepSeek  (native structured output)
    openai    -> langchain_openai.ChatOpenAI       (OpenAI-compatible fallback)

Embedding always uses langchain_openai.OpenAIEmbeddings (SiliconFlow compatible).
"""

from functools import lru_cache

from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel
from pydantic import SecretStr

from pwps_agent_api.core.config import Settings, get_settings


@lru_cache(maxsize=1)
def get_chat_model(settings: Settings | None = None) -> BaseChatModel:
    """Return a chat model instance based on LLM_PROVIDER.  Cached per process."""
    s = settings or get_settings()
    api_key = SecretStr(s.llm_api_key) if s.llm_api_key else None

    if s.llm_provider == "deepseek":
        from langchain_deepseek import ChatDeepSeek

        return ChatDeepSeek(
            model=s.llm_model,
            api_key=api_key,
            base_url=s.llm_base_url,
            temperature=s.llm_temperature,
            # Use JSON mode for structured output (thinking mode doesn't support tool_choice)
            model_kwargs={"response_format": {"type": "json_object"}},
        )

    # Default: OpenAI-compatible
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=s.llm_model,
        api_key=api_key,
        base_url=s.llm_base_url,
        temperature=s.llm_temperature,
    )


@lru_cache(maxsize=1)
def get_embedding_model(settings: Settings | None = None) -> Embeddings:
    """Return an embedding model instance.  Cached per process."""
    from langchain_openai import OpenAIEmbeddings

    s = settings or get_settings()
    return OpenAIEmbeddings(
        model=s.embedding_model,
        api_key=SecretStr(s.embedding_api_key) if s.embedding_api_key else None,
        base_url=s.embedding_base_url,
    )
