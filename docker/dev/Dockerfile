# Python base image
FROM python:3.12-slim

# Set workdir
WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Install dependencies needed for psycopg2-binary and other builds
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# ✅ wait-for-it.sh faylni konteynerga nusxalash
COPY docker/dev/wait-for-it.sh /wait-for-it.sh
RUN chmod +x /wait-for-it.sh

# Upgrade pip
RUN pip install --upgrade pip

# Install Python requirements
COPY requirements/ /app
RUN pip install --no-cache-dir -r /app/dev.txt

# Copy project source (will be mounted during docker-compose run)
COPY ../../src/ /app
