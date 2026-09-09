"""Redis-клиенты: асинхронный для API, синхронный для Celery (воркер и
beat синхронные по своей природе)."""

import redis
import redis.asyncio as aioredis
from django.conf import settings

# один пул на процесс, для Celery это безопасно
_sync_pool = redis.ConnectionPool.from_url(settings.REDIS_URL, decode_responses=True)


def get_redis() -> aioredis.Redis:
    """Новое подключение на каждый вызов: `async with get_redis() as r:`.

    Без общего пула на уровне модуля — иначе в тестах (где каждый вызов
    поднимает свой event loop) рано или поздно словим "Event loop is
    closed". В реальном деплое (один loop на процесс) это не бьёт по
    производительности.
    """
    return aioredis.from_url(settings.REDIS_URL, decode_responses=True)


def get_sync_redis() -> redis.Redis:
    return redis.Redis(connection_pool=_sync_pool)


def seat_hold_key(event_id: int, seat_id: int) -> str:
    """Ключ блокировки места: одна пара (мероприятие, место) — один ключ,
    независимо от того, кто пытается его забронировать."""
    return f"seat_hold:{event_id}:{seat_id}"
