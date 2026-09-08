import datetime

import pytest
from django.utils import timezone

from events.models import Event, Order, Seat, Venue


@pytest.fixture
def venue(db):
    return Venue.objects.create(name="Крокус Сити Холл", city="Москва")


@pytest.fixture
def other_venue(db):
    return Venue.objects.create(name="Ледовый дворец", city="Санкт-Петербург")


@pytest.fixture
def seats(venue):
    return [Seat.objects.create(venue=venue, row=1, number=n) for n in (1, 2, 3)]


@pytest.fixture
def event(venue):
    return Event.objects.create(
        venue=venue,
        title="Тестовый концерт",
        description="Описание концерта",
        starts_at=timezone.now() + datetime.timedelta(days=7),
    )


def test_list_events_returns_created_event(client, event):
    resp = client.get("/api/events/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 1
    assert data["items"][0]["id"] == event.id
    assert data["items"][0]["venue"]["city"] == "Москва"


def test_list_events_filters_by_city(client, event, other_venue):
    Event.objects.create(
        venue=other_venue,
        title="Концерт в СПб",
        starts_at=timezone.now() + datetime.timedelta(days=3),
    )

    resp = client.get("/api/events/", {"city": "Москва"})
    data = resp.json()
    assert data["count"] == 1
    assert data["items"][0]["venue"]["city"] == "Москва"


def test_list_events_filters_by_date(client, event):
    wrong_day = (event.starts_at + datetime.timedelta(days=1)).date().isoformat()
    resp = client.get("/api/events/", {"date": wrong_day})
    assert resp.json()["count"] == 0

    right_day = event.starts_at.date().isoformat()
    resp = client.get("/api/events/", {"date": right_day})
    assert resp.json()["count"] == 1


def test_get_event_detail(client, event):
    resp = client.get(f"/api/events/{event.id}")
    assert resp.status_code == 200
    assert resp.json()["title"] == "Тестовый концерт"


def test_get_event_detail_404_for_missing_event(client, db):
    resp = client.get("/api/events/999999")
    assert resp.status_code == 404


def test_seat_map_marks_booked_and_free_seats(client, event, seats):
    booked_seat = seats[0]
    Order.objects.create(event=event, seat=booked_seat, buyer_email="buyer@example.com")

    resp = client.get(f"/api/events/{event.id}/seats")
    assert resp.status_code == 200
    data = resp.json()

    by_id = {s["id"]: s for s in data["seats"]}
    assert by_id[booked_seat.id]["is_available"] is False
    assert by_id[seats[1].id]["is_available"] is True
    assert by_id[seats[2].id]["is_available"] is True


def test_seat_map_404_for_missing_event(client, db):
    resp = client.get("/api/events/999999/seats")
    assert resp.status_code == 404
