"""Бизнес-логика без привязки к HTTP или Celery — её дёргают и api_orders.py,
и tasks.py, чтобы не дублировать проверки в двух местах."""

import io

from django.core.files.base import ContentFile
from django.utils import timezone
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas

from .models import Order, Ticket


class InvalidOrderStateError(Exception):
    """Операция запрошена для заказа, который сейчас не в подходящем
    для неё статусе (например, попытка оплатить уже оплаченный или
    истёкший заказ)."""


def confirm_payment(order: Order) -> Order:
    """Подтверждает оплату заказа: HOLD -> PAID.

    В реальной системе тут был бы вебхук от платёжного шлюза; здесь
    оплата считается подтверждённой самим фактом вызова.
    """
    if order.status != Order.Status.HOLD:
        raise InvalidOrderStateError(
            f"Нельзя подтвердить оплату заказа #{order.id}: "
            f"текущий статус {order.status!r}, ожидался HOLD"
        )
    order.status = Order.Status.PAID
    order.paid_at = timezone.now()
    order.save(update_fields=["status", "paid_at"])
    return order


def generate_ticket_for_order(order: Order) -> Ticket:
    """Выпускает билет (идемпотентно — OneToOneField не даст создать второй)
    и рендерит для него PDF. Требует оплаченный заказ."""
    if order.status != Order.Status.PAID:
        raise InvalidOrderStateError(
            f"Нельзя выпустить билет для заказа #{order.id}: "
            f"текущий статус {order.status!r}, ожидался PAID"
        )
    ticket, _created = Ticket.objects.get_or_create(order=order)
    pdf_bytes = _render_ticket_pdf(order, ticket)
    ticket.pdf_file.save(f"{ticket.code}.pdf", ContentFile(pdf_bytes), save=True)
    return ticket


def _render_ticket_pdf(order: Order, ticket: Ticket) -> bytes:
    """Рисует одностраничный PDF билета через reportlab. Отдельная функция —
    именно здесь реалистичнее всего словить сбой диска/хранилища, и именно
    его должен ретраить generate_ticket_pdf_task."""
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)

    pdf.setFont("Helvetica-Bold", 20)
    pdf.drawString(2 * cm, 27 * cm, "TicketHub — электронный билет")

    pdf.setFont("Helvetica", 12)
    lines = [
        f"Мероприятие: {order.event.title}",
        f"Площадка: {order.event.venue.name}, {order.event.venue.city}",
        f"Дата: {order.event.starts_at:%d.%m.%Y %H:%M}",
        f"Место: ряд {order.seat.row}, место {order.seat.number}",
        f"Покупатель: {order.buyer_email}",
        f"Код билета: {ticket.code}",
    ]
    y = 25 * cm
    for line in lines:
        pdf.drawString(2 * cm, y, line)
        y -= 1 * cm

    pdf.showPage()
    pdf.save()
    return buffer.getvalue()
