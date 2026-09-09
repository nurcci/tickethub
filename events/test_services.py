"""Тесты сервисного слоя: подтверждение оплаты и выпуск билета.

Используем фабрики (events/factories.py) вместо ручной сборки объектов —
первое место в проекте, где это оправдано: сценариев много, и часть из
них (например, "заказ в статусе X") завязана именно на статус, а не на
конкретные значения полей.
"""

import pytest

from events.factories import OrderFactory
from events.models import Order, Ticket
from events.services import InvalidOrderStateError, confirm_payment, generate_ticket_for_order


def test_confirm_payment_moves_hold_order_to_paid(db):
    order = OrderFactory(status=Order.Status.HOLD)

    confirm_payment(order)

    order.refresh_from_db()
    assert order.status == Order.Status.PAID
    assert order.paid_at is not None


@pytest.mark.parametrize(
    "status", [Order.Status.PAID, Order.Status.CANCELLED, Order.Status.EXPIRED]
)
def test_confirm_payment_rejects_order_not_in_hold(db, status):
    order = OrderFactory(status=status)

    with pytest.raises(InvalidOrderStateError):
        confirm_payment(order)


def test_generate_ticket_for_order_creates_ticket_with_pdf(db):
    order = OrderFactory(status=Order.Status.PAID)

    ticket = generate_ticket_for_order(order)

    assert ticket.order_id == order.id
    assert ticket.pdf_file.name
    assert ticket.pdf_file.read().startswith(b"%PDF")


def test_generate_ticket_for_order_is_idempotent(db):
    """Повторный вызов для того же заказа не плодит второй билет —
    OneToOneField на Order плюс get_or_create в сервисе."""
    order = OrderFactory(status=Order.Status.PAID)

    first = generate_ticket_for_order(order)
    second = generate_ticket_for_order(order)

    assert first.id == second.id
    assert Ticket.objects.filter(order=order).count() == 1


def test_generate_ticket_for_order_rejects_unpaid_order(db):
    order = OrderFactory(status=Order.Status.HOLD)

    with pytest.raises(InvalidOrderStateError):
        generate_ticket_for_order(order)
