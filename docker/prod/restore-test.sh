#!/bin/bash
# Zaxiradan tiklash sinovi (TZ §17.3, Q36). Ishchi bazaga TEGMAYDI: vaqtinchalik postgres
# konteyneri va vaqtinchalik media papkasiga tiklaydi, keyin yaxlitlikni tekshiradi va o'chiradi.
#
#   ./docker/prod/restore-test.sh                       # oxirgi soatlik zaxira
#   ./docker/prod/restore-test.sh 2026-11-02_14         # aniq vaqt belgisi
#
# Natija: tiklash vaqti (RTO o'lchovi), zaxira yoshi (RPO), yaxlitlik (hash/imzo/ledger/fayllar)
# va zaxira paytidagi barmoq izlari bilan moslik. Hisobot: backups/hourly/restore-test-<vaqt>.log
set -euo pipefail

ROOT="${ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}"
DEST="${BACKUP_DIR:-$ROOT/backups/hourly}"
APP_IMAGE="${APP_IMAGE:-$(docker inspect --format '{{.Config.Image}}' forest_app_prod)}"
STAMP="${1:-$(ls -1 "$DEST/db" | sed -n 's/^forest_\(.*\)\.dump$/\1/p' | sort | tail -n 1)}"
DUMP="$DEST/db/forest_$STAMP.dump"
SNAP="$DEST/db/forest_$STAMP.integrity.json"
MEDIA="$DEST/media/$STAMP"
[ -f "$DUMP" ] || { echo "Zaxira topilmadi: $DUMP"; exit 1; }
[ -d "$MEDIA" ] || { echo "Media nusxasi topilmadi: $MEDIA"; exit 1; }

RUN="restore_test_$$"
NET="${RUN}_net"
PG="${RUN}_pg"
WORK="$(mktemp -d "$DEST/.${RUN}.XXXX")"
LOG="$DEST/restore-test-$(date +%Y-%m-%d_%H%M).log"
cleanup() {
    docker rm -f "$PG" >/dev/null 2>&1 || true
    docker network rm "$NET" >/dev/null 2>&1 || true
    rm -rf "$WORK"
}
trap cleanup EXIT
exec > >(tee -a "$LOG") 2>&1

echo "=== Tiklash sinovi: $STAMP ($(date -Is)) ==="
BACKUP_AGE_MIN=$(( ( $(date +%s) - $(stat -c %Y "$DUMP") ) / 60 ))
echo "Zaxira yoshi: $BACKUP_AGE_MIN daqiqa (RPO mezoni: <= 60, soatlik cron bilan)"
T0=$(date +%s)

docker network create "$NET" >/dev/null
DBPASS="$(head -c 18 /dev/urandom | base64 | tr -dc 'A-Za-z0-9')"
docker run -d --name "$PG" --network "$NET" -e POSTGRES_DB=forest_restore -e POSTGRES_USER=forest_restore \
    -e POSTGRES_PASSWORD="$DBPASS" postgres:16 >/dev/null
until docker exec "$PG" pg_isready -U forest_restore -d forest_restore >/dev/null 2>&1; do sleep 1; done
sleep 2

echo "→ baza tiklanmoqda..."
docker cp "$DUMP" "$PG:/tmp/restore.dump"
docker exec "$PG" pg_restore -U forest_restore -d forest_restore --no-owner --no-privileges -j 4 /tmp/restore.dump
T_DB=$(date +%s)
echo "  baza: $(( T_DB - T0 )) s"

echo "→ media tiklanmoqda..."
rsync -a "$MEDIA/" "$WORK/media/"
T_MEDIA=$(date +%s)
echo "  media: $(( T_MEDIA - T_DB )) s, $(find "$WORK/media" -type f | wc -l) fayl"

echo "→ yaxlitlik tekshiruvi..."
COMPARE=""
if [ -f "$SNAP" ]; then
    cp "$SNAP" "$WORK/snapshot.json"
    COMPARE="--compare /restore/snapshot.json"
fi
# Skript root sifatida ishlaydi (umask 077), app image esa UID 1000 bilan — tekshiruv konteyneri
# nusxalarni o'qiy olishi uchun ish papkasini image foydalanuvchisiga beramiz
APP_UID="${APP_UID:-$(docker run --rm --entrypoint id "$APP_IMAGE" -u)}"
chown -R "$APP_UID" "$WORK"
set +e
docker run --rm --network "$NET" --env-file "$ROOT/.env" \
    -e DB_HOST="$PG" -e DB_PORT=5432 -e POSTGRES_DB=forest_restore -e POSTGRES_USER=forest_restore -e POSTGRES_PASSWORD="$DBPASS" \
    -e REDIS_HOST=127.0.0.1 -v "$ROOT/src:/app:ro" -v "$WORK/media:/app/media:ro" -v "$WORK:/restore:ro" \
    --entrypoint sh "$APP_IMAGE" -c "python manage.py yashil_integrity_check --strict $COMPARE"
RC=$?
set -e
T_END=$(date +%s)
echo "Umumiy tiklash vaqti: $(( T_END - T0 )) s (RTO mezoni: <= 14400 s)"
if [ $RC -eq 0 ]; then
    echo "NATIJA: O'TDI — baza, hujjat hash'lari, imzolar, ombor harakatlari va fayllar mos"
else
    echo "NATIJA: O'TMADI (kod $RC) — yuqoridagi farqlarni ko'ring"
fi
echo "Hisobot: $LOG"
exit $RC
