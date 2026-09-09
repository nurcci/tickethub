"""factory_boy-фабрики для тестов — одно место сборки тестовых объектов
вместо дублирования фикстур в каждом test_*.py."""

import datetime

import factory
from django.utils import timezone

from .models import Event, Order, Seat, Venue


class VenueFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Venue

    name = factory.Sequence(lambda n: f"Площадка {n}")
    city = "Москва"


class SeatFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Seat

    venue = factory.SubFactory(VenueFactory)
    row = factory.Sequence(lambda n: n + 1)
    number = 1


class EventFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Event

    venue = factory.SubFactory(VenueFactory)
    title = factory.Sequence(lambda n: f"Мероприятие {n}")
    starts_at = factory.LazyFunction(lambda: timezone.now() + datetime.timedelta(days=7))


class OrderFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Order

    event = factory.SubFactory(EventFactory)
    # Место должно принадлежать той же площадке, что и мероприятие —
    # SelfAttribute поднимается на уровень OrderFactory и берёт venue
    # уже созданного event, а не плодит независимую площадку.
    seat = factory.SubFactory(SeatFactory, venue=factory.SelfAttribute("..event.venue"))
    buyer_email = factory.Sequence(lambda n: f"buyer{n}@example.com")
    status = Order.Status.HOLD
