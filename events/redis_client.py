"""Redis-клиенты: асинхронный — для API-эндпоинтов (Django Ninja),
синхронный — для Celery-задач (Celery worker/beat синхронные по своей
природе, оборачивать их в asyncio смысла нет).
"""

import redis
import redis.asyncio as aioredis
from django.conf import settings

# Синхронный клиент (Celery) живёт весь процесс — один пул на него
# переиспользуется корректно, event loop тут ни при чём.
_sync_pool = redis.ConnectionPool.from_url(settings.REDIS_URL, decode_responses=True)


def get_redis() -> aioredis.Redis:
    """Новое подключение на каждый вызов — используйте как `async with
    get_redis() as r:`, чтобы соединение закрывалось само.

    Общий connection pool на уровне модуля тут специально не заводим:
    он бы кэшировал живые соединения между вызовами, а любой код, где
    async-view дёргается не из одного долгоживущего ASGI event loop
    (например, синхронный Django test client в тестах — на каждый вызов
    поднимает свой event loop), рано или поздно наткнётся на "Event loop
    is closed" при попытке переиспользовать соединение из закрытого loop.
    В реальном ASGI-деплое (uvicorn) event loop один на процесс, так что
    на проде это не бьёт по производительности — только чуть больше
    накладных расходов в тестах.
    """
    return aioredis.from_url(settings.REDIS_URL, decode_responses=True)


def get_sync_redis() -> redis.Redis:
    return redis.Redis(connection_pool=_sync_pool)


def seat_hold_key(event_id: int, seat_id: int) -> str:
    """Ключ блокировки места: одна пара (мероприятие, место) — один ключ,
    независимо от того, кто пытается его забронировать."""
    return f"seat_hold:{event_id}:{seat_id}"
