import json
from typing import Protocol

from redis.asyncio import ConnectionPool, Redis

from pwps_agent_api.core.config import get_settings
from pwps_agent_api.schemas import TraceEvent

# Singleton connection pool for Redis
_redis_pool: ConnectionPool | None = None


def _get_redis_pool() -> ConnectionPool:
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = ConnectionPool.from_url(
            get_settings().redis_url, decode_responses=False
        )
    return _redis_pool


class EventStore(Protocol):
    async def publish_many(self, run_id: str, events: list[TraceEvent]) -> None: ...

    async def list_events(self, run_id: str) -> list[TraceEvent]: ...


class RedisEventStore:
    def __init__(self, redis: Redis, *, max_events: int = 500) -> None:
        self._redis = redis
        self._max_events = max_events

    async def publish_many(self, run_id: str, events: list[TraceEvent]) -> None:
        if not events:
            return

        key = _run_events_key(run_id)
        payloads = [
            json.dumps(event.model_dump(mode="json"), ensure_ascii=False, sort_keys=True)
            for event in events
        ]
        await self._redis.rpush(key, *payloads)
        await self._redis.ltrim(key, -self._max_events, -1)

    async def list_events(self, run_id: str) -> list[TraceEvent]:
        raw_events = await self._redis.lrange(_run_events_key(run_id), 0, -1)
        events: list[TraceEvent] = []
        for raw_event in raw_events:
            text = raw_event.decode("utf-8") if isinstance(raw_event, bytes) else raw_event
            events.append(TraceEvent.model_validate(json.loads(text)))
        return events


def get_event_store() -> EventStore:
    redis = Redis(connection_pool=_get_redis_pool())
    return RedisEventStore(redis)


def _run_events_key(run_id: str) -> str:
    return f"runs:{run_id}:events"
