import datetime

import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone

from events.models import Event, Order, Seat, Venue


@pytest.fixture
def venue(db):
    return Venue.objects.create(name="Крокус Сити Холл", city="Москва")


@pytest.fixture
def seat(venue):
    return Seat.objects.create(venue=venue, row=1, number=1)


@pytest.fixture
def event(venue):
    return Event.objects.create(
        venue=venue,
        title="Тестовый концерт",
        starts_at=timezone.now() + datetime.timedelta(days=7),
    )


def test_seat_is_unique_within_venue(venue):
    Seat.objects.create(venue=venue, row=1, number=1)
    with pytest.raises(IntegrityError), transaction.atomic():
        Seat.objects.create(venue=venue, row=1, number=1)


def test_order_can_be_created_for_seat(event, seat):
    order = Order.objects.create(event=event, seat=seat, buyer_email="buyer@example.com")
    assert order.status == Order.Status.HOLD


def test_cannot_double_book_same_seat_for_same_event(event, seat):
    """Ядро продукта: второй активный заказ на то же место того же
    мероприятия база данных создать не даст — это и есть защита от
    овербукинга на уровне БД, до всякого Redis (появится на неделе 3)."""
    Order.objects.create(event=event, seat=seat, buyer_email="first@example.com")
    with pytest.raises(IntegrityError), transaction.atomic():
        Order.objects.create(event=event, seat=seat, buyer_email="second@example.com")


def test_cancelled_order_frees_the_seat_for_rebooking(event, seat):
    """А вот если первый заказ отменён — место можно забронировать заново:
    constraint игнорирует CANCELLED/EXPIRED заказы (см. condition в модели)."""
    first = Order.objects.create(event=event, seat=seat, buyer_email="first@example.com")
    first.status = Order.Status.CANCELLED
    first.save()

    second = Order.objects.create(event=event, seat=seat, buyer_email="second@example.com")
    assert second.status == Order.Status.HOLD
