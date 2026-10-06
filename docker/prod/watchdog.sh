#!/usr/bin/env bash
# Sayt qorovuli. Cron (root):
#   */5 * * * * /root/Forest-Back/docker/prod/watchdog.sh >> /var/log/forest-watchdog.log 2>&1
#
# 2026-10-06 reboot'dan keyin host'dagi tizim nginx'i 80-portni egallab,
# docker nginx port bog'lay olmay qoldi; `docker start` buni tuzatmadi,
# faqat konteynerni qayta yaratish tuzatdi. Shu holat takrorlansa, skript
# o'zi tuzatadi: sayt javob bermasa -> band portni egallagan host
# xizmatini to'xtatadi -> nginx konteynerini qayta yaratadi.
set -u
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

COMPOSE="docker-compose -f /root/Forest-Back/docker/prod/docker-compose-prod.yml"
URL="https://stat-urmon.uz/"
LOCK=/run/forest-watchdog.recreate   # 30 daqiqada ko'pi bilan bir marta qayta yaratish

code=$(curl -s -m 15 -o /dev/null -w '%{http_code}' "$URL" 2>/dev/null || echo 000)
if [ "$code" = "200" ]; then
    exit 0
fi

echo "[$(date '+%F %T')] sayt javob bermayapti (HTTP $code)"

if [ -f "$LOCK" ] && [ $(( $(date +%s) - $(stat -c %Y "$LOCK") )) -lt 1800 ]; then
    echo "  oxirgi qayta yaratishdan 30 daqiqa o'tmagan — kutilmoqda"
    exit 1
fi
touch "$LOCK"

# 80/443 ni docker-proxy'dan boshqa kim egallagan bo'lsa to'xtatamiz
for svc in nginx apache2; do
    if systemctl is-active --quiet "$svc"; then
        echo "  host xizmati $svc 80/443 ni egallagan — to'xtatilmoqda"
        systemctl stop "$svc"; systemctl disable "$svc" >/dev/null 2>&1
    fi
done

echo "  forest_nginx qayta yaratilmoqda..."
docker rm -f forest_nginx_prod >/dev/null 2>&1
$COMPOSE up -d --no-deps forest_nginx >/dev/null 2>&1
sleep 5
code=$(curl -s -m 15 -o /dev/null -w '%{http_code}' "$URL" 2>/dev/null || echo 000)
echo "  natija: HTTP $code"
[ "$code" = "200" ]
