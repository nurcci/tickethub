"""Фоновые задачи Celery. release_expired_holds гоняется по расписанию
Celery beat (см. CELERY_BEAT_SCHEDULE в settings.py) — раз в минуту.
"""

import datetime

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from .models import Order


@shared_task
def release_expired_holds() -> int:
    """Снимает просроченные холды.

    Ключ блокировки в Redis к этому моменту уже сам истёк по TTL (это
    решает проблему "занято навсегда", если покупатель просто закрыл
    вкладку) — здесь только синхронизируем состояние в базе: Order,
    которые провисели в HOLD дольше SEAT_HOLD_TTL_SECONDS, переводим
    в EXPIRED, и место снова становится доступным для брони.

    Возвращает количество обновлённых заказов — удобно видеть в логах
    Celery, что задача реально что-то делает, а не просто существует.
    """
    cutoff = timezone.now() - datetime.timedelta(seconds=settings.SEAT_HOLD_TTL_SECONDS)
    return Order.objects.filter(status=Order.Status.HOLD, created_at__lt=cutoff).update(
        status=Order.Status.EXPIRED
    )
