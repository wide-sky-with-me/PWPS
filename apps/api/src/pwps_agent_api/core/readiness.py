from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, Protocol

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class RedisPinger(Protocol):
    def ping(self, **kwargs: Any) -> Awaitable[bool]: ...


@dataclass(frozen=True)
class ApplicationReadinessChecker:
    session_factory: Callable[[], AsyncSession]
    redis: RedisPinger

    async def check(self) -> dict[str, str]:
        async with self.session_factory() as session:
            await session.execute(text("select 1"))
        await self.redis.ping()
        return {
            "configuration": "ok",
            "database": "ok",
            "redis": "ok",
        }
