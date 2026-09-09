"""Нагрузочный тест. Запуск локально против docker-compose:

    pip install locust
    locust -f locustfile.py --host=http://localhost:8002

Дальше http://localhost:8089 — задать число пользователей и смотреть
RPS/задержки/ошибки вживую. Два сценария: обычный читающий трафик и
намеренная гонка за одно место — проверка защиты от овербукинга не
только в юнит-тестах, но и под реальной нагрузкой.
"""

import random

from locust import HttpUser, between, task


class BrowsingUser(HttpUser):
    """Обычный посетитель: листает список мероприятий и карты мест —
    большинство трафика в реальном сервисе."""

    weight = 5
    wait_time = between(0.5, 2.0)

    @task(3)
    def list_events(self):
        self.client.get("/api/events/", name="/api/events/ (список)")

    @task(2)
    def seat_map(self):
        self.client.get("/api/events/1/seats", name="/api/events/{id}/seats")

    @task(1)
    def swagger_docs(self):
        self.client.get("/api/docs", name="/api/docs")


class OverbookingRaceUser(HttpUser):
    """Намеренно бьётся за одно и то же место (event_id=1, seat_id=1) —
    почти всегда 409, и это правильный результат."""

    weight = 1
    wait_time = between(0.1, 0.3)

    @task
    def race_for_seat(self):
        email = f"loadtest-{random.randint(1, 1_000_000)}@example.com"
        self.client.post(
            "/api/events/1/seats/1/hold",
            json={"buyer_email": email},
            name="/api/events/{id}/seats/{id}/hold (race)",
        )
