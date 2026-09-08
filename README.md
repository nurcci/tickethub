# TicketHub

Платформа бронирования мест на мероприятия в реальном времени. Флагманский
пет-проект №2 из плана трудоустройства backend-разработчиком — ядро
проекта — честная защита от овербукинга: два человека физически не могут
забронировать одно и то же место.

## Статус
Недели 1-2 — фундамент (модели, Django Admin, Docker Compose) и публичный API на Django Ninja (async, пагинация, фильтры, Swagger).

## Стек
Python, Django, PostgreSQL, Redis, Celery (со 2-й недели), Docker / Docker
Compose, Pytest, ruff, GitHub Actions.

## Модели
`Venue` (площадка) → `Seat` (физическое место в зале) и `Event`
(мероприятие на площадке) → `Order` (заказ места на мероприятие,
статусы HOLD/PAID/CANCELLED/EXPIRED) → `Ticket` (билет после оплаты).

Защита от овербукинга — на уровне БД уже сейчас: `UniqueConstraint` не даёт
создать два активных заказа на одно место в рамках одного мероприятия.
С недели 3 к этому добавится блокировка в Redis с TTL — быстрая проверка
ещё до похода в базу, чтобы пользователь получал мгновенный ответ
"место занято", а не ждал ошибки уникальности.

## Запуск локально

    docker compose up -d --build
    docker compose exec web python manage.py createsuperuser

Django Admin: http://localhost:8002/admin/

Swagger-документация API: http://localhost:8002/api/docs

## Тесты

    pip install -r requirements-dev.txt
    pytest -v
