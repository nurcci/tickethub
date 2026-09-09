"""Тесты Celery-тасок оплаты.

confirm_payment_task вызываем напрямую (как обычную функцию — таска не
bind, ретраев не делает, это просто обновление статуса + постановка
следующей таски в очередь). generate_ticket_pdf_task, наоборот, гоняем
через .apply() — это штатный способ Celery выполнить bind-таску
синхронно и локально, с полноценным self.request, чтобы self.retry()
отработал по-настоящему (пересчитал попытку сам, без брокера и воркера),
а не упал с ошибкой "нет активного контекста задачи".
"""

from unittest.mock import patch

import pytest

from events.factories import OrderFactory
from events.models import Order, Ticket
from events.tasks import confirm_payment_task, generate_ticket_pdf_task


def test_confirm_payment_task_marks_order_paid_and_queues_ticket_generation(db):
    order = OrderFactory(status=Order.Status.HOLD)

    with patch("events.tasks.generate_ticket_pdf_task.delay") as mocked_delay:
        result = confirm_payment_task(order.id)

    order.refresh_from_db()
    assert result == Order.Status.PAID
    assert order.status == Order.Status.PAID
    mocked_delay.assert_called_once_with(order.id)


def test_generate_ticket_pdf_task_creates_ticket_on_success(db):
    order = OrderFactory(status=Order.Status.PAID)

    result = generate_ticket_pdf_task.apply(args=(order.id,))

    assert result.successful()
    ticket = Ticket.objects.get(order=order)
    assert str(ticket.code) == result.get()
    assert ticket.pdf_file.name


def test_generate_ticket_pdf_task_retries_and_recovers_from_transient_failure(db):
    """Имитируем временный сбой при рендере PDF (например, диск на
    секунду недоступен) — таска должна повторить попытку и в итоге
    успешно выпустить билет, а не просто упасть."""
    order = OrderFactory(status=Order.Status.PAID)

    with patch("events.services._render_ticket_pdf") as mocked_render:
        mocked_render.side_effect = [OSError("no space left on device"), b"%PDF-fake-content"]

        result = generate_ticket_pdf_task.apply(args=(order.id,))

    assert result.successful()
    assert mocked_render.call_count == 2
    assert Ticket.objects.filter(order=order).exists()


def test_generate_ticket_pdf_task_gives_up_after_max_retries(db):
    """А если сбой не временный, а постоянный — после исчерпания лимита
    попыток таска должна упасть с исходной ошибкой, а не тихо зависнуть."""
    order = OrderFactory(status=Order.Status.PAID)

    with patch("events.services._render_ticket_pdf") as mocked_render:
        mocked_render.side_effect = OSError("disk permanently unavailable")

        result = generate_ticket_pdf_task.apply(args=(order.id,))

    assert result.failed()
    with pytest.raises(OSError):
        result.get()
    # max_retries=3 => 1 первая попытка + 3 повтора = 4 вызова
    assert mocked_render.call_count == 4
    assert not Ticket.objects.filter(order=order, pdf_file__gt="").exists()


def test_generate_ticket_pdf_task_does_not_retry_on_unpaid_order(db):
    """InvalidOrderStateError — не транзиентная ошибка (заказ не станет
    оплаченным сам по себе от повторной попытки), поэтому ретраев быть
    не должно, таска должна упасть сразу с первой попытки."""
    order = OrderFactory(status=Order.Status.HOLD)

    result = generate_ticket_pdf_task.apply(args=(order.id,))

    assert result.failed()
    with pytest.raises(Exception, match="ожидался PAID"):
        result.get()
