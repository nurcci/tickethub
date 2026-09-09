import uuid

from django.db import models
from django.db.models import Q


class Venue(models.Model):
    """Физическая площадка: концертный зал, кинотеатр, стадион и т.п."""

    name = models.CharField(max_length=200)
    city = models.CharField(max_length=100)
    address = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.name} ({self.city})"


class Seat(models.Model):
    """Физическое место в зале — часть постоянной схемы площадки,
    не привязано к конкретному мероприятию.
    """

    venue = models.ForeignKey(Venue, on_delete=models.CASCADE, related_name="seats")
    row = models.PositiveSmallIntegerField()
    number = models.PositiveSmallIntegerField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["venue", "row", "number"], name="unique_seat_per_venue"
            )
        ]
        ordering = ["row", "number"]

    def __str__(self) -> str:
        return f"{self.venue.name} — ряд {self.row}, место {self.number}"


class Event(models.Model):
    """Конкретное мероприятие на площадке в конкретное время."""

    venue = models.ForeignKey(Venue, on_delete=models.CASCADE, related_name="events")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    starts_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["starts_at"]

    def __str__(self) -> str:
        return f"{self.title} — {self.starts_at:%d.%m.%Y %H:%M}"


class Order(models.Model):
    """Заказ одного места на мероприятие.

    HOLD — временная бронь сразу при выборе места, до оплаты; параллельно
    подстрахована блокировкой в Redis. UniqueConstraint ниже — защита от
    овербукинга уже на уровне БД: даже если два запроса проскочат мимо
    Redis, второй активный заказ на то же место база не создаст.
    """

    class Status(models.TextChoices):
        HOLD = "HOLD", "Забронировано"
        PAID = "PAID", "Оплачено"
        CANCELLED = "CANCELLED", "Отменено"
        EXPIRED = "EXPIRED", "Истекло"

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="orders")
    seat = models.ForeignKey(Seat, on_delete=models.CASCADE, related_name="orders")
    buyer_email = models.EmailField()
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.HOLD
    )
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            # Активный заказ (не отменённый и не истёкший) на одно место
            # в рамках одного мероприятия может быть только один.
            models.UniqueConstraint(
                fields=["event", "seat"],
                condition=~Q(status__in=["CANCELLED", "EXPIRED"]),
                name="unique_active_order_per_event_seat",
            )
        ]

    def __str__(self) -> str:
        return f"Заказ #{self.pk} — {self.seat} на «{self.event.title}» ({self.status})"


class Ticket(models.Model):
    """Билет — итоговый артефакт после оплаты заказа. Выпускается
    Celery-таской generate_ticket_pdf_task сразу после подтверждения
    оплаты (events/tasks.py, events/services.py).
    """

    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="ticket")
    code = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    issued_at = models.DateTimeField(auto_now_add=True)
    pdf_file = models.FileField(upload_to="tickets/", blank=True, null=True)

    def __str__(self) -> str:
        return f"Билет {self.code} ({self.order})"
