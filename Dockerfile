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

# Локально (docker-compose.yml) команда для каждого сервиса (web/worker/
# beat) переопределяется явно — эта CMD ниже реально используется только
# при деплое (неделя 5, см. render.yaml → dockerCommand и bin/start-prod.sh),
# либо если образ запустить напрямую через `docker run` без compose.
CMD ["sh", "bin/start-prod.sh"]
