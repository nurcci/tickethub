"""HTML-страницы поверх events/api.py — тот же API, только с интерфейсом.
Сами действия (бронь, оплата) идут через fetch к JSON-эндпоинтам, эти
вьюхи просто отдают разметку и начальные данные.
"""

from django.shortcuts import get_object_or_404, render

from .models import Event, Order, Seat


def event_list(request):
    events = Event.objects.select_related("venue").order_by("starts_at")
    return render(request, "events/list.html", {"events": events})


def event_detail(request, event_id: int):
    event = get_object_or_404(Event.objects.select_related("venue"), id=event_id)

    booked_seat_ids = set(
        Order.objects.filter(
            event=event, status__in=[Order.Status.HOLD, Order.Status.PAID]
        ).values_list("seat_id", flat=True)
    )

    seats = list(Seat.objects.filter(venue_id=event.venue_id).order_by("row", "number"))
    rows = {}
    for seat in seats:
        seat.is_available = seat.id not in booked_seat_ids
        rows.setdefault(seat.row, []).append(seat)

    return render(
        request,
        "events/detail.html",
        {"event": event, "rows": sorted(rows.items())},
    )


def order_detail(request, order_id: int):
    order = get_object_or_404(Order.objects.select_related("event", "seat"), id=order_id)
    return render(request, "events/order.html", {"order": order})
