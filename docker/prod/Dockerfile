FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    gcc \
    netcat \
    && rm -rf /var/lib/apt/lists/*

COPY docker/prod/wait-for-it.sh /wait-for-it.sh
COPY docker/prod/entrypoint.sh /entrypoint.sh
RUN chmod +x /wait-for-it.sh /entrypoint.sh

COPY requirements/ /app/requirements/
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r /app/requirements/prod.txt

COPY src /app

RUN python manage.py collectstatic --noinput
