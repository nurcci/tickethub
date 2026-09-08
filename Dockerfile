FROM python:3.12-slim

WORKDIR /app

# psycopg2-binary собирается из исходников без libpq-dev, но на всякий
# случай (и для будущих зависимостей) держим базовые build-инструменты.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Прод-запуск через gunicorn появится на неделе 5 (CI/CD и эксплуатация).
# Пока — dev-сервер Django, его же переопределяет docker-compose.yml.
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
