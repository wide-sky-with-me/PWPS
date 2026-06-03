from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from pwps_agent_api.core.config import get_settings

# Lazy-initialized engine and session maker
_engine: AsyncEngine | None = None
_async_session_maker: async_sessionmaker[AsyncSession] | None = None


def _get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(settings.database_url)
    return _engine


def _get_session_maker() -> async_sessionmaker[AsyncSession]:
    global _async_session_maker
    if _async_session_maker is None:
        _async_session_maker = async_sessionmaker(_get_engine(), expire_on_commit=False)
    return _async_session_maker


# Backward-compatible module-level access
class _SessionMakerProxy:
    """Proxy that lazily initializes the session maker."""

    def __call__(self) -> AsyncSession:
        return _get_session_maker()()

    def __getattr__(self, name: str) -> Any:
        return getattr(_get_session_maker(), name)


AsyncSessionMaker = _SessionMakerProxy()


async def get_session() -> AsyncIterator[AsyncSession]:
    async with _get_session_maker()() as session:
        yield session
