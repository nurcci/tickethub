"""Тесты HTTP-слоя оплаты: POST /orders/{id}/pay и GET /orders/{id}.

confirm_payment_task.delay мокаем — эндпоинт должен только поставить
таску в очередь и сразу ответить 202, реальное выполнение таски уже
проверено отдельно в test_tasks_payment.py. Так тест не зависит от
живого Celery-воркера и не оставляет за собой мусор в очереди.
"""

from unittest.mock import patch

from events.factories import OrderFactory
from events.models import Order


def test_pay_order_returns_202_and_queues_confirmation_task(client, db):
    order = OrderFactory(status=Order.Status.HOLD)

    with patch("events.api_orders.confirm_payment_task.delay") as mocked_delay:
        resp = client.post(f"/api/orders/{order.id}/pay")

    assert resp.status_code == 202
    data = resp.json()
    assert data["order_id"] == order.id
    assert data["status"] == "HOLD"  # реальное подтверждение ещё не произошло
    mocked_delay.assert_called_once_with(order.id)


def test_pay_order_404_for_missing_order(client, db):
    resp = client.post("/api/orders/999999/pay")
    assert resp.status_code == 404


def test_pay_order_409_when_not_in_hold(client, db):
    order = OrderFactory(status=Order.Status.PAID)

    with patch("events.api_orders.confirm_payment_task.delay") as mocked_delay:
        resp = client.post(f"/api/orders/{order.id}/pay")

    assert resp.status_code == 409
    mocked_delay.assert_not_called()


def test_get_order_without_ticket_yet(client, db):
    order = OrderFactory(status=Order.Status.HOLD)

    resp = client.get(f"/api/orders/{order.id}")

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "HOLD"
    assert data["ticket_code"] is None
    assert data["ticket_pdf_url"] is None


def test_get_order_includes_ticket_once_issued(client, db):
    order = OrderFactory(status=Order.Status.PAID)
    from events.services import generate_ticket_for_order

    ticket = generate_ticket_for_order(order)

    resp = client.get(f"/api/orders/{order.id}")

    assert resp.status_code == 200
    data = resp.json()
    assert data["ticket_code"] == str(ticket.code)
    assert data["ticket_pdf_url"].endswith(".pdf")


def test_get_order_404_for_missing_order(client, db):
    resp = client.get("/api/orders/999999")
    assert resp.status_code == 404
