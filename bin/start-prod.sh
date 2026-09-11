#!/bin/sh
# Прод-запуск для бесплатного деплоя (см. README → «Деплой»).
#
# Free-тариф Render не даёт отдельный процесс под Celery worker, поэтому
# worker и beat живут в фоне того же контейнера, что и веб-сервер — ради
# $0 хостинга. В docker-compose.yml это три независимых процесса.
set -e

echo "==> Применяю миграции"
python manage.py migrate --noinput

echo "==> Собираю статику"
python manage.py collectstatic --noinput

# если пользователь уже есть, команда упадёт с ошибкой уникальности —
# не даём этому уронить весь деплой
if [ -n "$DJANGO_SUPERUSER_USERNAME" ]; then
    echo "==> Создаю суперюзера (если ещё не существует)"
    python manage.py createsuperuser --noinput || true
fi

echo "==> Запускаю Celery worker + beat в фоне"
# Free-тариф Render — всего 512 МБ RAM на контейнер. Дефолтный prefork-пул
# форкает по одному процессу на ядро (тут 8) — на такой памяти это верный
# OOM. --pool=solo держит воркер в одном процессе; для пет-проекта с
# редкими задачами (оплата, PDF) этого хватает с запасом.
celery -A tickethub worker -B -l info --concurrency=1 --pool=solo &

echo "==> Запускаю gunicorn"
exec gunicorn tickethub.wsgi:application --bind 0.0.0.0:10000 --workers 1 --threads 2
