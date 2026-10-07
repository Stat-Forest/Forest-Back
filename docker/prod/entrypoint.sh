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

# Ijara billing ma'lumotnomasi (idempotent) va GIS xo'jalik konturlari
# (faqat jadval bo'sh bo'lsa — 8 MB fixture har deploy'da qayta o'qilmasin).
echo "Seeding billing reference data..."
python manage.py seed_billing || echo "!!! seed_billing FAILED"
python manage.py import_xojalik_locations --if-empty || echo "!!! import_xojalik_locations FAILED"

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Starting application with: $@"
exec "$@"
