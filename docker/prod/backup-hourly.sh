#!/bin/bash
# Soatlik zaxira (TZ §17.3: RPO <= 1 soat). Host'da cron bilan ishlaydi:
#   5 * * * *  /root/Forest-Back/docker/prod/backup-hourly.sh >> /root/Forest-Back/backups/hourly/backup.log 2>&1
#
# Nima saqlanadi (bir-biriga mos, bitta vaqt belgisi bilan):
#   db/forest_<YYYY-mm-dd_HH>.dump           pg_dump -Fc (siqilgan, pg_restore bilan tiklanadi)
#   db/forest_<YYYY-mm-dd_HH>.integrity.json yashil_integrity_check natijasi (tiklash sinovida solishtiriladi)
#   media/<YYYY-mm-dd_HH>/                    media nusxasi (rsync --link-dest: faqat o'zgargan fayllar joy oladi)
#   config/<YYYY-mm-dd>/                      kuniga bir marta: e-imzo kalitlari, .env fayllari, migratsiyalar (chmod 600)
# Saqlash: soatlik — KEEP_HOURS (48) soat, har kungi 00 nusxa — KEEP_DAYS (30) kun.
# Tashqi nusxa: OFFSITE_TARGET="user@host:/path" (rsync over ssh) — bo'lsa oxirgi nusxa yuboriladi.
set -euo pipefail

ROOT="${ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}"
DEST="${BACKUP_DIR:-$ROOT/backups/hourly}"
PG_CONTAINER="${PG_CONTAINER:-forest_postgres_prod}"
APP_CONTAINER="${APP_CONTAINER:-forest_app_prod}"
KEEP_HOURS="${KEEP_HOURS:-48}"
KEEP_DAYS="${KEEP_DAYS:-30}"
OFFSITE_TARGET="${OFFSITE_TARGET:-}"

STAMP="$(date +%Y-%m-%d_%H)"
DAY="$(date +%Y-%m-%d)"
umask 077
mkdir -p "$DEST/db" "$DEST/media" "$DEST/config"

# Bir vaqtda ikki nusxa ishlamasin
exec 9>"$DEST/.lock"
if ! flock -n 9; then
    echo "[$(date -Is)] oldingi zaxira hali tugamagan — o'tkazib yuborildi"
    exit 0
fi

START=$(date +%s)
echo "[$(date -Is)] zaxira boshlandi: $STAMP"

# 1) Baza: vaqtinchalik faylga, tekshirib keyin nomini o'zgartirish (yarim fayl qolmasin)
DUMP="$DEST/db/forest_$STAMP.dump"
docker exec "$PG_CONTAINER" sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc -Z 6' > "$DUMP.tmp"
docker exec -i "$PG_CONTAINER" pg_restore -l < "$DUMP.tmp" > /dev/null
mv "$DUMP.tmp" "$DUMP"
echo "  baza: $(du -h "$DUMP" | cut -f1)"

# 2) Yaxlitlik barmoq izi (dump'dan keyin darhol; tiklashda solishtiriladi)
if docker exec "$APP_CONTAINER" python manage.py yashil_integrity_check --json --no-files > "$DEST/db/forest_$STAMP.integrity.json.tmp" 2>/dev/null; then
    mv "$DEST/db/forest_$STAMP.integrity.json.tmp" "$DEST/db/forest_$STAMP.integrity.json"
else
    rm -f "$DEST/db/forest_$STAMP.integrity.json.tmp"
    echo "  ogohlantirish: yashil_integrity_check ishlamadi"
fi

# 3) Media: oldingi nusxaga hardlink, faqat o'zgarganlar ko'chiriladi
LINK=""
[ -d "$DEST/media/latest" ] && LINK="--link-dest=$DEST/media/latest"
rsync -a --delete $LINK "$ROOT/media/" "$DEST/media/$STAMP.tmp/"
rm -rf "$DEST/media/$STAMP"
mv "$DEST/media/$STAMP.tmp" "$DEST/media/$STAMP"
# rsync -a papkaga asl media/ ning eski mtime'ini yozadi — saqlash muddati (5-qadam) mtime bo'yicha
# hisoblanadi, shuning uchun nusxa vaqtini hozirgi vaqtga o'rnatamiz, aks holda yangi nusxa darhol o'chadi
touch "$DEST/media/$STAMP"
ln -sfn "$DEST/media/$STAMP" "$DEST/media/latest"
echo "  media: $(find "$DEST/media/$STAMP" -type f | wc -l) fayl"

# 4) Konfiguratsiya (kuniga bir marta): imzo xizmati kalitlari va muhit fayllari
if [ ! -d "$DEST/config/$DAY" ]; then
    mkdir -p "$DEST/config/$DAY"
    [ -d "$ROOT/e-imzo-server/keys" ] && cp -a "$ROOT/e-imzo-server/keys" "$DEST/config/$DAY/e-imzo-keys"
    [ -d "$ROOT/keys" ] && cp -a "$ROOT/keys" "$DEST/config/$DAY/keys"
    for f in .env .env.postgres .env.eimzo; do
        [ -f "$ROOT/$f" ] && cp -a "$ROOT/$f" "$DEST/config/$DAY/$f"
    done
    # Migratsiyalar gitda yo'q (entrypoint serverda yaratadi) — yangi serverga tiklashda aynan shular kerak
    (cd "$ROOT/src" && find apps -path '*/migrations/0*.py' -print0 | tar --null -czf "$DEST/config/$DAY/migrations.tgz" -T -)
    chmod -R go-rwx "$DEST/config/$DAY"
fi

# 5) Saqlash muddati: soatlik nusxalar KEEP_HOURS, kunlik (00) KEEP_DAYS
find "$DEST/db" -maxdepth 1 -type f -name 'forest_*' ! -name 'forest_*_00.*' -mmin +$((KEEP_HOURS * 60)) -delete
find "$DEST/db" -maxdepth 1 -type f -name 'forest_*_00.*' -mtime +"$KEEP_DAYS" -delete
find "$DEST/media" -mindepth 1 -maxdepth 1 -type d ! -name '*_00' ! -name 'latest' -mmin +$((KEEP_HOURS * 60)) -exec rm -rf {} +
find "$DEST/media" -mindepth 1 -maxdepth 1 -type d -name '*_00' -mtime +"$KEEP_DAYS" -exec rm -rf {} +
find "$DEST/config" -mindepth 1 -maxdepth 1 -type d -mtime +"$KEEP_DAYS" -exec rm -rf {} +

# 6) Tashqi nusxa (zaxira joyi ajratilgach — Q-14)
if [ -n "$OFFSITE_TARGET" ]; then
    rsync -a "$DUMP" "$DEST/db/forest_$STAMP.integrity.json" "$OFFSITE_TARGET/db/" 2>/dev/null || echo "  ogohlantirish: tashqi nusxa (db) yuborilmadi"
    rsync -a --delete "$DEST/media/$STAMP/" "$OFFSITE_TARGET/media/" || echo "  ogohlantirish: tashqi nusxa (media) yuborilmadi"
fi

echo "[$(date -Is)] zaxira tugadi: $(( $(date +%s) - START )) s"
