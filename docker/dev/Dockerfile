FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY docker/dev/wait-for-it.sh /wait-for-it.sh
COPY docker/dev/entrypoint.sh /entrypoint.sh
RUN chmod +x /wait-for-it.sh /entrypoint.sh

RUN pip install --upgrade pip

COPY requirements/ /app/requirements/
RUN pip install --no-cache-dir -r /app/requirements/dev.txt