"""Жизненный цикл заказа: оплата и статус. Отдельный роутер от api.py —
там каталог мероприятий, здесь — уже конкретный заказ."""

from asgiref.sync import sync_to_async
from django.shortcuts import aget_object_or_404
from ninja import Router, Status

from .models import Order, Ticket
from .schemas import ErrorOut, OrderOut, PaymentAcceptedOut
from .tasks import confirm_payment_task

router = Router(tags=["orders"])


@router.post("/{order_id}/pay", response={202: PaymentAcceptedOut, 404: ErrorOut, 409: ErrorOut})
async def pay_order(request, order_id: int):
    """Инициирует оплату. Подтверждение идёт асинхронно в воркере —
    отвечаем 202, финальный статус и билет смотреть через GET /orders/{id}."""
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
    # .delay() синхронный (поход в Redis), поэтому в async-view через sync_to_async
    await sync_to_async(confirm_payment_task.delay)(order_id)
    return Status(202, PaymentAcceptedOut(order_id=order.id, status=order.status))


@router.get("/{order_id}", response=OrderOut)
async def get_order(request, order_id: int):
    """Статус заказа + код и ссылка на билет, если он уже выпущен."""
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
