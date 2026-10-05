#!/bin/sh

set -e

# Migration fayllari git'da saqlanmaydi (.gitignore: src/apps/*/migrations/0*),
# shuning uchun dev'dagi kabi avval yaratiladi. src bind-mount bo'lgani uchun
# yaratilgan fayllar serverda (/root/Forest-Back/src/...) saqlanib qoladi.
# Xato bo'lsa (masalan interaktiv savol kerak bo'lsa) konteyner yiqilmasin:
# migrate baribir ishlaydi, deploy logida "!!!" ko'rinadi.
echo "Making migrations..."
python manage.py makemigrations --noinput || echo "!!! makemigrations FAILED — serverda qo'lda tekshiring"

echo "Running migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Starting application with: $@"
exec "$@"
