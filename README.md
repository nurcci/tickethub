# TicketHub

Бронирование мест на мероприятия в реальном времени, с честной защитой
от овербукинга — два человека физически не могут занять одно и то же
место, даже если жмут кнопку одновременно.

**Живое демо:** _(появится после деплоя — см. «Деплой» ниже)_

## Стек

Python, Django, Django Ninja, PostgreSQL, Redis, Celery, reportlab,
gunicorn, whitenoise, Docker Compose, Pytest + factory_boy, Locust,
ruff, GitHub Actions, Render / Neon / Upstash.

## Как это устроено

`Venue` (площадка) → `Seat` (физическое место) и `Event` (мероприятие
на площадке) → `Order` (заказ места на мероприятие, статусы
HOLD/PAID/CANCELLED/EXPIRED) → `Ticket` (билет после оплаты, с PDF).

Защита от овербукинга — в два слоя. Сначала быстрая проверка в Redis
(`SETNX` с TTL): если место уже кто-то держит, отказ приходит мгновенно,
без единого запроса к базе. Следом — `UniqueConstraint` на уровне
Postgres, второй, более медленный, но абсолютный рубеж на случай, если
что-то проскочит мимо Redis. Просроченные брони (человек закрыл вкладку,
не оплатив) раз в минуту снимает Celery beat.

Оплата асинхронная: `POST /api/orders/{id}/pay` сразу отвечает `202`, а
подтверждение и генерация PDF-билета идут в воркере — это две разные
Celery-таски, специально разделённые, чтобы сбой при рендере PDF не
откатывал уже подтверждённую оплату. Бизнес-логика лежит в
`events/services.py`, её дёргают и HTTP-эндпоинты, и таски — не
дублируется.

Поверх API — обычный веб-интерфейс на Django-шаблонах: список
мероприятий, карта мест, бронь по email и страница заказа с оплатой
и ссылкой на билет (`events/views.py`, `events/templates`,
`events/static`). Сам API отдельно документирован через Swagger —
`/api/docs`.

## Запуск локально

    docker compose up -d --build
    docker compose exec web python manage.py createsuperuser

Сайт: http://localhost:8002

Django Admin: http://localhost:8002/admin/

Swagger: http://localhost:8002/api/docs

## Тесты

    pip install -r requirements-dev.txt
    pytest -v

## Нагрузочное тестирование

    pip install locust
    locust -f locustfile.py --host=http://localhost:8002

Два сценария: обычное чтение (список, карта мест) и намеренная гонка
множества «покупателей» за одно и то же место.

Отдельно — точечный стресс-тест на 50 параллельных попыток забронировать
одно место (`events/stress_test.py`, через `Django test.Client`, без
сети наружу, с настоящими Postgres и Redis):

    docker compose exec -T web python manage.py shell < events/stress_test.py

Реальный результат: `Counter({409: 49, 200: 1})` — ровно одна бронь
проходит, остальные корректно отклонены.

## Деплой

Бесплатно, без карты, тремя сервисами:

- **Render** (`render.yaml`) — веб-процесс на gunicorn. Бесплатный
  тариф не даёт отдельный процесс под Celery worker, поэтому worker и
  beat запускаются в фоне того же контейнера (`bin/start-prod.sh`) —
  осознанный компромисс ради $0 хостинга; в `docker-compose.yml` это
  три независимых процесса.
- **Neon** — PostgreSQL, бесплатно навсегда.
- **Upstash** — Redis, бесплатно навсегда.

Порядок:

1. Neon: создать проект → скопировать connection string
   (`postgresql://...?sslmode=require`).
2. Upstash: создать Redis-базу → скопировать TLS-адрес (`rediss://...`).
3. Render: New → Blueprint → подключить репозиторий — Render сам
   найдёт `render.yaml`.
4. В Render Dashboard → Environment задать `DATABASE_URL`, `REDIS_URL`,
   `DJANGO_SUPERUSER_USERNAME` / `_EMAIL` / `_PASSWORD` (суперюзер
   создаётся автоматически при старте — на бесплатном тарифе нет Shell).
5. Deploy. После первого запуска вписать выданный домен в
   `ALLOWED_HOSTS` и `CSRF_TRUSTED_ORIGINS` и передеплоить.

Бесплатный веб-сервис Render засыпает после 15 минут простоя и
просыпается ~30-60 секунд на первый запрос.
