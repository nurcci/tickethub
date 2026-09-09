"""Нагрузочный тест (неделя 5). Запуск локально против docker-compose:

    pip install locust
    locust -f locustfile.py --host=http://localhost:8002

Дальше открыть http://localhost:8089, задать число пользователей и
запустить — Locust покажет RPS, задержки и процент ошибок в реальном
времени. Ниже два сценария: обычный читающий трафик (то, что происходит
в жизни чаще всего — люди листают афишу) и намеренная гонка за одно и то
же место, чтобы под нагрузкой ещё раз убедиться, что защита от
овербукинга не проседает при параллельных запросах, а не только в тестах
с двумя корутинами (events/test_hold.py).
"""

import random

from locust import HttpUser, between, task


class BrowsingUser(HttpUser):
    """Имитирует обычного посетителя: листает список мероприятий и карты
    мест. Это большинство трафика в реальном сервисе бронирования —
    вес задач ниже подобран соответственно (список/детали чаще, чем
    попытка забронировать)."""

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
    """Намеренно бьётся за ОДНО и то же место (event_id=1, seat_id=1) —
    при большом числе таких пользователей одновременно должно пройти
    ровно столько успешных бронирований, сколько раз это место успевало
    легитимно освобождаться (в норме — почти всегда 409 Conflict, что и
    является ожидаемым, правильным результатом теста)."""

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
