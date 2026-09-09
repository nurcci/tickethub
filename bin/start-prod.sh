#!/bin/sh
# Прод-запуск для бесплатного деплоя (неделя 5, см. README → "Деплой").
#
# Бесплатный тариф Render не даёт отдельный процесс под Celery worker
# (Background Worker там платный, от $7/мес) — поэтому здесь worker и
# beat запускаются в фоне того же контейнера, что и веб-сервер. Это
# осознанный компромисс ради $0 хостинга для пет-проекта: в "настоящем"
# проде (см. docker-compose.yml) это три независимых процесса/контейнера,
# которые масштабируются по отдельности.
set -e

echo "==> Применяю миграции"
python manage.py migrate --noinput

echo "==> Собираю статику"
python manage.py collectstatic --noinput

# Суперюзер для Django Admin создаётся один раз через переменные
# DJANGO_SUPERUSER_USERNAME/EMAIL/PASSWORD (стандартный флаг Django,
# --noinput). Если пользователь уже существует, команда упадёт с
# ошибкой уникальности — не даём этому уронить весь деплой.
if [ -n "$DJANGO_SUPERUSER_USERNAME" ]; then
    echo "==> Создаю суперюзера (если ещё не существует)"
    python manage.py createsuperuser --noinput || true
fi

echo "==> Запускаю Celery worker + beat в фоне"
celery -A tickethub worker -B -l info &

echo "==> Запускаю gunicorn"
exec gunicorn tickethub.wsgi:application --bind 0.0.0.0:10000 --workers 2 --threads 2
