#!/usr/bin/env bash
# Cron (root, har kuni 03:00):
#   0 3 * * * /root/Forest-Back/docker/prod/ssl_renew.sh >> /var/log/ssl_renew.log 2>&1
# certbot faqat muddati 30 kundan kam qolgan sertifikatlarni yangilaydi, shuning
# uchun har kuni ishga tushirish xavfsiz.

# cron'da PATH qisqa bo'ladi — docker-compose /usr/local/bin da bo'lishi mumkin
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

COMPOSE="docker-compose -f /root/Forest-Back/docker/prod/docker-compose-prod.yml"

# 📅 log for date
echo "[$(date)] SSL renew started"

# ✅ Certbot update
$COMPOSE run --rm forest_certbot renew

# 🔁 NGINX reload (-T: cron'da TTY yo'q)
$COMPOSE exec -T forest_nginx nginx -s reload

echo "[$(date)] SSL renew completed"
