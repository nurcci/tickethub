"""Публичный API мероприятий и мест. Роутер подключается в tickethub/urls.py.

Всё асинхронное — прямо через async ORM (aget, async for), без
sync_to_async.
"""

import datetime

from django.conf import settings
from django.db import IntegrityError
from django.http import Http404
from django.shortcuts import aget_object_or_404
from ninja import Query, Router, Status
from ninja.pagination import PageNumberPagination, paginate

from .models import Event, Order, Seat
from .redis_client import get_redis, seat_hold_key
from .schemas import ErrorOut, EventOut, EventSeatMapOut, HoldSeatIn, HoldSeatOut, SeatOut

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


@router.post("/{event_id}/seats/{seat_id}/hold", response={200: HoldSeatOut, 409: ErrorOut})
async def hold_seat(request, event_id: int, seat_id: int, payload: HoldSeatIn):
    """Забронировать место.

    Сначала атомарный SETNX в Redis — если место уже держат, отказ
    приходит мгновенно, до базы дело не доходит. Если ключ свободен —
    только тогда пишем Order. UniqueConstraint на Order — второй,
    более медленный рубеж защиты на случай гонки мимо Redis.
    """
    event = await aget_object_or_404(Event.objects.select_related("venue"), id=event_id)
    seat = await aget_object_or_404(Seat, id=seat_id, venue_id=event.venue_id)

    key = seat_hold_key(event_id, seat_id)
    async with get_redis() as redis_client:
        acquired = await redis_client.set(
            key, payload.buyer_email, nx=True, ex=settings.SEAT_HOLD_TTL_SECONDS
        )

        if not acquired:
            return Status(
                409,
                ErrorOut(detail="Место уже удерживается другим покупателем, попробуйте позже"),
            )

        try:
            order = await Order.objects.acreate(
                event=event, seat=seat, buyer_email=payload.buyer_email
            )
        except IntegrityError:
            # успели создать заказ мимо Redis — откатываем ключ и отказываем
            await redis_client.delete(key)
            return Status(409, ErrorOut(detail="Место уже забронировано"))

    return Status(
        200,
        HoldSeatOut(
            order_id=order.id,
            status=order.status,
            event_id=event.id,
            seat_id=seat.id,
            hold_expires_at=order.created_at
            + datetime.timedelta(seconds=settings.SEAT_HOLD_TTL_SECONDS),
        ),
    )
