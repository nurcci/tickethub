"""Redis-блокировка мест и очистка просроченных холдов."""

import asyncio
import datetime

import pytest
from django.test import AsyncClient
from django.utils import timezone

from events.models import Event, Order, Seat, Venue
from events.redis_client import get_sync_redis, seat_hold_key
from events.tasks import release_expired_holds


@pytest.fixture
def venue(db):
    return Venue.objects.create(name="Ледовый дворец", city="Москва")


@pytest.fixture
def seat(venue):
    return Seat.objects.create(venue=venue, row=1, number=1)


@pytest.fixture
def event(venue):
    return Event.objects.create(
        venue=venue, title="Финал", starts_at=timezone.now() + datetime.timedelta(days=1)
    )


@pytest.fixture(autouse=True)
def clear_redis_lock():
    """Redis — общее состояние между тестами (в отличие от тестовой БД,
    которая откатывается сама), поэтому чистим ключи блокировок вручную
    до и после каждого теста."""
    r = get_sync_redis()
    r.flushdb()
    yield
    r.flushdb()


def test_hold_seat_creates_order_and_redis_key(client, event, seat):
    resp = client.post(
        f"/api/events/{event.id}/seats/{seat.id}/hold",
        {"buyer_email": "buyer@example.com"},
        content_type="application/json",
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "HOLD"

    order = Order.objects.get(id=data["order_id"])
    assert order.buyer_email == "buyer@example.com"

    r = get_sync_redis()
    assert r.get(seat_hold_key(event.id, seat.id)) == "buyer@example.com"


def test_hold_seat_rejects_second_hold_before_first_expires(client, event, seat):
    first = client.post(
        f"/api/events/{event.id}/seats/{seat.id}/hold",
        {"buyer_email": "first@example.com"},
        content_type="application/json",
    )
    assert first.status_code == 200

    second = client.post(
        f"/api/events/{event.id}/seats/{seat.id}/hold",
        {"buyer_email": "second@example.com"},
        content_type="application/json",
    )
    assert second.status_code == 409


@pytest.mark.django_db(transaction=True)
async def test_only_one_of_two_concurrent_holds_succeeds(event, seat):
    """Два по-настоящему параллельных запроса на одно и то же место.
    Спор решается атомарным SETNX в Redis — ровно один клиент получает
    бронь, второй мгновенно получает 409."""
    url = f"/api/events/{event.id}/seats/{seat.id}/hold"
    client_a, client_b = AsyncClient(), AsyncClient()

    resp_a, resp_b = await asyncio.gather(
        client_a.post(url, {"buyer_email": "a@example.com"}, content_type="application/json"),
        client_b.post(url, {"buyer_email": "b@example.com"}, content_type="application/json"),
    )

    statuses = sorted([resp_a.status_code, resp_b.status_code])
    assert statuses == [200, 409]

    hold_qs = Order.objects.filter(event=event, seat=seat, status=Order.Status.HOLD)
    holds = [o async for o in hold_qs]
    assert len(holds) == 1


def test_release_expired_holds_marks_stale_orders_as_expired(event, seat):
    order = Order.objects.create(event=event, seat=seat, buyer_email="stale@example.com")
    stale_moment = timezone.now() - datetime.timedelta(seconds=400)
    Order.objects.filter(id=order.id).update(created_at=stale_moment)

    updated_count = release_expired_holds()

    order.refresh_from_db()
    assert updated_count == 1
    assert order.status == Order.Status.EXPIRED


def test_release_expired_holds_leaves_fresh_holds_alone(event, seat):
    order = Order.objects.create(event=event, seat=seat, buyer_email="fresh@example.com")

    updated_count = release_expired_holds()

    order.refresh_from_db()
    assert updated_count == 0
    assert order.status == Order.Status.HOLD
