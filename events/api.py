"""Публичный API на Django Ninja. Роутер подключается в tickethub/urls.py.

Эндпоинты асинхронные — используем нативный async ORM Django (aget,
async for, values_list().aiterator()) без обёрток вроде sync_to_async,
там, где это API размера "список / карта мест" оправдано: запросы не
блокируют event loop сервера, пока ждут ответа от базы.
"""

import datetime

from django.http import Http404
from django.shortcuts import aget_object_or_404
from ninja import Query, Router
from ninja.pagination import PageNumberPagination, paginate

from .models import Event, Order, Seat
from .schemas import EventOut, EventSeatMapOut, SeatOut

router = Router(tags=["events"])


@router.get("/", response=list[EventOut])
@paginate(PageNumberPagination, page_size=20)
async def list_events(
    request,
    city: str = Query(None, description="Фильтр по городу площадки"),  # noqa: B008
    date: datetime.date = Query(  # noqa: B008
        None, description="Фильтр по дате начала (YYYY-MM-DD)"
    ),
):
    """Список мероприятий с пагинацией и фильтрами по городу/дате."""
    qs = Event.objects.select_related("venue").order_by("starts_at")
    if city:
        qs = qs.filter(venue__city__iexact=city)
    if date:
        qs = qs.filter(starts_at__date=date)
    return qs


@router.get("/{event_id}", response=EventOut)
async def get_event(request, event_id: int):
    """Детали одного мероприятия."""
    return await aget_object_or_404(Event.objects.select_related("venue"), id=event_id)


@router.get("/{event_id}/seats", response=EventSeatMapOut)
async def get_seat_map(request, event_id: int):
    """Карта мест конкретного мероприятия: все места площадки + для
    каждого — занято оно (есть активный HOLD/PAID заказ) или свободно.
    """
    try:
        event = await Event.objects.select_related("venue").aget(id=event_id)
    except Event.DoesNotExist as exc:
        raise Http404("Event not found") from exc

    booked_seat_ids = {
        seat_id
        async for seat_id in Order.objects.filter(
            event=event, status__in=[Order.Status.HOLD, Order.Status.PAID]
        ).values_list("seat_id", flat=True)
    }

    seats_qs = Seat.objects.filter(venue_id=event.venue_id).order_by("row", "number")
    seats = [
        SeatOut(
            id=seat.id,
            row=seat.row,
            number=seat.number,
            is_available=seat.id not in booked_seat_ids,
        )
        async for seat in seats_qs
    ]

    return EventSeatMapOut(event=event, seats=seats)
