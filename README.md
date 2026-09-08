# TicketHub

Платформа бронирования мест на мероприятия в реальном времени. Флагманский
пет-проект №2 из плана трудоустройства backend-разработчиком — ядро
проекта — честная защита от овербукинга: два человека физически не могут
забронировать одно и то же место.

## Статус
Недели 1-3 — фундамент, публичный API (Django Ninja) и защита от овербукинга в реальном времени: SETNX-блокировка места в Redis (TTL 5 минут) + Celery beat, снимающий просроченные холды.

## Стек
Python, Django, PostgreSQL, Redis, Celery, Docker / Docker Compose,
Pytest, ruff, GitHub Actions.

## Модели
`Venue` (площадка) → `Seat` (физическое место в зале) и `Event`
(мероприятие на площадке) → `Order` (заказ места на мероприятие,
статусы HOLD/PAID/CANCELLED/EXPIRED) → `Ticket` (билет после оплаты).

Защита от овербукинга — на уровне БД уже сейчас: `UniqueConstraint` не даёт
создать два активных заказа на одно место в рамках одного мероприятия.
С недели 3 к этому добавилась блокировка в Redis (SETNX, TTL 5 минут) —
быстрая проверка ещё до похода в базу: `POST /api/events/{id}/seats/{id}/hold`.
Если ключ уже занят, отказ приходит мгновенно, без единого запроса к Postgres.
Просроченные холды (покупатель закрыл вкладку) раз в минуту снимает
Celery beat — задача `events.tasks.release_expired_holds`.

## Запуск локально

    docker compose up -d --build
    docker compose exec web python manage.py createsuperuser

Django Admin: http://localhost:8002/admin/

Swagger-документация API: http://localhost:8002/api/docs

## Тесты

    pip install -r requirements-dev.txt
    pytest -v
