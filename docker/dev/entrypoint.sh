#!/bin/sh

/wait-for-it.sh forest_postgres:5432 --timeout=30 --strict -- \
&& /wait-for-it.sh forest_redis:6379 --timeout=30 --strict -- \
&& python manage.py makemigrations --noinput \
&& python manage.py migrate --noinput \
&& (python manage.py seed_billing || echo "!!! seed_billing FAILED") \
&& (python manage.py import_xojalik_locations --if-empty || echo "!!! import_xojalik_locations FAILED") \
&& python manage.py collectstatic --noinput \
&& python manage.py runserver 0.0.0.0:8000