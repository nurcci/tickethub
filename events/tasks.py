"""Фоновые задачи Celery. release_expired_holds гоняется по расписанию
beat раз в минуту (см. CELERY_BEAT_SCHEDULE в settings.py).

confirm_payment_task и generate_ticket_pdf_task — намеренно разные таски:
подтверждение оплаты и генерация PDF по-разному ломаются и по-разному
должны ретраиться, а сбой рендера билета не должен откатывать уже
подтверждённую оплату.
"""

import datetime

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from . import services
from .models import Order
from .services import InvalidOrderStateError


@shared_task
def release_expired_holds() -> int:
    """Снимает просроченные холды. Ключ в Redis к этому моменту уже сам
    истёк по TTL — здесь только синхронизируем базу: HOLD старше
    SEAT_HOLD_TTL_SECONDS переводим в EXPIRED, место снова свободно.

    Возвращает число обновлённых заказов — видно в логах, что задача
    реально что-то делает.
    """
    cutoff = timezone.now() - datetime.timedelta(seconds=settings.SEAT_HOLD_TTL_SECONDS)
    return Order.objects.filter(status=Order.Status.HOLD, created_at__lt=cutoff).update(
        status=Order.Status.EXPIRED
    )


@shared_task
def confirm_payment_task(order_id: int) -> str:
    """Имитирует подтверждение оплаты (в реальности — вебхук шлюза).
    Простое обновление статуса, ретраить нечего; выпуск билета ставим
    отдельной таской, чтобы её сбои не трогали уже подтверждённую оплату.
    """
    order = Order.objects.get(id=order_id)
    services.confirm_payment(order)
    generate_ticket_pdf_task.delay(order_id)
    return order.status


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def generate_ticket_pdf_task(self, order_id: int) -> str:
    """Генерирует PDF-билет для оплаченного заказа. До 3 ретраев с
    задержкой 5с — рендер/запись файла реалистичнее всего сбоят временно.
    InvalidOrderStateError не транзиентная, ретраить её бессмысленно —
    пробрасываем как есть.
    """
    order = Order.objects.select_related("event__venue", "seat").get(id=order_id)
    try:
        ticket = services.generate_ticket_for_order(order)
    except InvalidOrderStateError:
        raise
    except Exception as exc:
        raise self.retry(exc=exc) from exc
    return str(ticket.code)
