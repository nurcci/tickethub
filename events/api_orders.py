"""Эндпоинты жизненного цикла уже созданного заказа: оплата и статус.

Отдельный роутер от events/api.py: там — просмотр мероприятий и мест
(публичный каталог), здесь — конкретный заказ конкретного покупателя.
"""

from asgiref.sync import sync_to_async
from django.shortcuts import aget_object_or_404
from ninja import Router, Status

from .models import Order, Ticket
from .schemas import ErrorOut, OrderOut, PaymentAcceptedOut
from .tasks import confirm_payment_task

router = Router(tags=["orders"])


@router.post("/{order_id}/pay", response={202: PaymentAcceptedOut, 404: ErrorOut, 409: ErrorOut})
async def pay_order(request, order_id: int):
    """Инициирует оплату заказа.

    Подтверждение происходит асинхронно в Celery-воркере
    (confirm_payment_task) — эндпоинт сразу отвечает 202 Accepted,
    финальный статус и билет смотрите через GET /orders/{id}.
    """
    order = await aget_object_or_404(Order, id=order_id)
    if order.status != Order.Status.HOLD:
        return Status(
            409,
            ErrorOut(
                detail=(
                    f"Оплатить можно только заказ в статусе HOLD, "
                    f"текущий статус: {order.status}"
                )
            ),
        )
    # .delay() — синхронный сетевой вызов к брокеру (Redis); в async-view
    # оборачиваем в sync_to_async, чтобы не блокировать event loop.
    await sync_to_async(confirm_payment_task.delay)(order_id)
    return Status(202, PaymentAcceptedOut(order_id=order.id, status=order.status))


@router.get("/{order_id}", response=OrderOut)
async def get_order(request, order_id: int):
    """Статус заказа и, если оплата подтверждена и билет уже выпущен —
    его код и ссылка на PDF."""
    order = await aget_object_or_404(
        Order.objects.select_related("event", "seat"), id=order_id
    )
    ticket = await Ticket.objects.filter(order=order).afirst()
    return OrderOut(
        order_id=order.id,
        status=order.status,
        event_id=order.event_id,
        seat_id=order.seat_id,
        buyer_email=order.buyer_email,
        ticket_code=str(ticket.code) if ticket else None,
        ticket_pdf_url=(ticket.pdf_file.url if ticket and ticket.pdf_file else None),
    )
