"""Стресс-тест защиты от овербукинга: N потоков одновременно бронируют
одно и то же место через Django test.Client — настоящие потоки, настоящий
Postgres и Redis внутри контейнера. Дополняет locustfile.py конкретной
воспроизводимой цифрой.

Запуск (при поднятом docker compose):

    docker compose exec -T web python manage.py shell < events/stress_test.py
"""

import json
import threading
from collections import Counter

from django.test import Client

from events.models import Seat

SEAT_ID = 3
N = 50

seat = Seat.objects.select_related("venue").get(id=SEAT_ID)
event = seat.venue.events.first()
if event is None:
    raise SystemExit(
        f"На площадке «{seat.venue}» нет ни одного мероприятия — "
        f"сначала создай Event через Django Admin."
    )

print(f"Место: {seat} | Мероприятие: {event} (event_id={event.id})")
print(f"Запускаю {N} параллельных попыток забронировать ЭТО ЖЕ место...")

results: list[int] = []
lock = threading.Lock()


def attempt(i: int) -> None:
    # SERVER_NAME="localhost" — иначе test.Client шлёт Host: testserver,
    # которого нет в ALLOWED_HOSTS, и вместо честного 409 получаем
    # 400 DisallowedHost ещё до того, как запрос доходит до вьюхи.
    client = Client(SERVER_NAME="localhost")
    response = client.post(
        f"/api/events/{event.id}/seats/{SEAT_ID}/hold",
        data=json.dumps({"buyer_email": f"stress{i}@example.com"}),
        content_type="application/json",
    )
    with lock:
        results.append(response.status_code)


threads = [threading.Thread(target=attempt, args=(i,)) for i in range(N)]
for t in threads:
    t.start()
for t in threads:
    t.join()

print(f"Всего запросов: {N}")
print("Коды ответов:", Counter(results))
print(
    "Ожидаемо: ровно один 200 (успешный hold) и остальные 409 "
    "(Conflict) — если так, защита от овербукинга держится и под "
    "настоящей параллельной нагрузкой, не только в тестах с двумя "
    "корутинами."
)
