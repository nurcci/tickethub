import datetime

from django.core.management.base import BaseCommand
from django.utils import timezone

from events.models import Event, Seat, Venue


class Command(BaseCommand):
    """Наполняет пустую базу одной площадкой и мероприятием — чтобы живое
    демо не встречало посетителя пустым списком. Ничего не делает, если
    площадки уже есть (безопасно гонять на каждом деплое)."""

    help = "Создаёт демо-площадку с местами и мероприятие, если база пустая"

    def handle(self, *args, **options):
        if Venue.objects.exists():
            self.stdout.write("Площадки уже есть — пропускаю сидинг")
            return

        venue = Venue.objects.create(
            name="Ледовый дворец",
            city="Санкт-Петербург",
            address="пр. Пятилеток, 1",
        )

        rows, seats_per_row = 4, 6
        Seat.objects.bulk_create(
            [
                Seat(venue=venue, row=row, number=number)
                for row in range(1, rows + 1)
                for number in range(1, seats_per_row + 1)
            ]
        )

        event = Event.objects.create(
            venue=venue,
            title="Демо-концерт TicketHub",
            description=(
                "Тестовое мероприятие для живого демо — забронируй любое "
                "место и оплати заказ, чтобы увидеть весь флоу целиком."
            ),
            starts_at=timezone.now() + datetime.timedelta(days=14),
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Создано: {venue} — {rows * seats_per_row} мест, {event}"
            )
        )
