"""LangGraph checkpoint manager for state persistence.

Provides checkpoint saver for workflow state persistence.
Uses PostgreSQL in production, InMemorySaver for testing/development.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver

log = logging.getLogger(__name__)

# Module-level checkpointer instance
_checkpointer: BaseCheckpointSaver[Any] | None = None


async def get_checkpointer() -> BaseCheckpointSaver[Any]:
    """Get or create the singleton checkpointer instance."""
    global _checkpointer

    if _checkpointer is not None:
        return _checkpointer

    # Use InMemorySaver for testing or when PostgreSQL is not available
    if os.getenv("TESTING") or os.getenv("USE_MEMORY_CHECKPOINT"):
        from langgraph.checkpoint.memory import InMemorySaver
        _checkpointer = InMemorySaver()
        log.info("Using InMemorySaver for checkpoints")
        return _checkpointer

    # Try PostgreSQL checkpointer
    try:
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

        from pwps_agent_api.core.config import get_settings

        settings = get_settings()
        checkpointer = AsyncPostgresSaver.from_conn_string(settings.database_url)
        # Note: setup() is called when the checkpointer is used
        _checkpointer = checkpointer  # type: ignore[assignment]
        log.info("Using PostgreSQL checkpointer")
        return _checkpointer  # type: ignore[return-value]
    except Exception as e:
        log.warning("Failed to initialize PostgreSQL checkpointer: %s", e)
        log.info("Falling back to InMemorySaver")
        from langgraph.checkpoint.memory import InMemorySaver
        _checkpointer = InMemorySaver()
        return _checkpointer


def set_checkpointer(checkpointer: BaseCheckpointSaver[Any]) -> None:
    """Set the checkpointer instance (for testing)."""
    global _checkpointer
    _checkpointer = checkpointer
