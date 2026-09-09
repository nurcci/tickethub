"""Фоновые задачи Celery. release_expired_holds гоняется по расписанию
Celery beat (см. CELERY_BEAT_SCHEDULE в settings.py) — раз в минуту.

confirm_payment_task и generate_ticket_pdf_task (неделя 4) — намеренно
две отдельные таски, а не одна: подтверждение оплаты и генерация PDF —
разные по природе операции (первая — простое обновление статуса в БД,
вторая — работа с файлами, где реальнее словить транзиентный сбой),
и им нужна разная политика ретраев. Сбой генерации PDF не должен
откатывать уже подтверждённую оплату — а значит, в отдельной таске
его можно спокойно ретраить, не трогая payment-часть.
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


@shared_task
def confirm_payment_task(order_id: int) -> str:
    """Имитирует подтверждение оплаты платёжным шлюзом: в реальной
    системе это был бы обработчик вебхука, здесь — сам факт вызова
    таски. Простое обновление статуса в БД, ретраить нечего — а вот
    выпуск билета сразу после успешной оплаты ставим в очередь отдельной
    таской, чтобы её возможный сбой (и повторные попытки) не влияли
    на уже подтверждённую оплату.
    """
    order = Order.objects.get(id=order_id)
    services.confirm_payment(order)
    generate_ticket_pdf_task.delay(order_id)
    return order.status


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def generate_ticket_pdf_task(self, order_id: int) -> str:
    """Генерирует PDF-билет для оплаченного заказа.

    До 3 повторов с задержкой 5 секунд при сбое — рендеринг и запись
    файла реалистичнее всего сбоят из-за временных проблем с диском/
    хранилищем, и такую ошибку имеет смысл просто повторить, а не
    считать покупку проваленной. А вот InvalidOrderStateError (заказ
    почему-то не оплачен) — не транзиентная проблема, ретраить её
    бессмысленно, поэтому пробрасываем как есть.
    """
    order = Order.objects.select_related("event__venue", "seat").get(id=order_id)
    try:
        ticket = services.generate_ticket_for_order(order)
    except InvalidOrderStateError:
        raise
    except Exception as exc:
        raise self.retry(exc=exc) from exc
    return str(ticket.code)
