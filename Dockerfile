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

# в docker-compose.yml команда каждого сервиса переопределяется явно —
# эта CMD используется только при деплое (см. render.yaml) или при
# запуске образа напрямую
CMD ["sh", "bin/start-prod.sh"]
