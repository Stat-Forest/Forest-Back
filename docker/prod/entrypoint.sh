#!/bin/sh

set -e

echo "Waiting for Postgres..."
/wait-for-it.sh forest_postgres:5432 --timeout=30 --strict -- echo "Postgres is up"

echo "Waiting for Redis..."
/wait-for-it.sh forest_redis:6379 --timeout=30 --strict -- echo "Redis is up"

echo "Running migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Starting application with: $@"
exec "$@"
