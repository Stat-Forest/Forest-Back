#!/bin/bash
# backup.sh yaratgan arxivni tiklaydi:
#   /backups/YYYY/MM/DD/forest_project_backup_<DATE>.zip  (ichida db.sql, media.zip)
# Ishlatish (host'da, /root/Forest-Back ichida):
#   ./docker/prod/restore.sh 2026/10/05/forest_project_backup_2026-10-05_03-00-00.zip
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
ENV_FILE="$ROOT/.env"
BACKUP_DIR="$ROOT/backups"
RESTORE_FILE="${1:-}"

if [ -z "$RESTORE_FILE" ]; then
    echo "❌ Usage: $0 YYYY/MM/DD/forest_project_backup_<DATE>.zip"
    exit 1
fi
[ -f "$ENV_FILE" ] || { echo "❌ .env topilmadi: $ENV_FILE"; exit 1; }
[ -f "$BACKUP_DIR/$RESTORE_FILE" ] || { echo "❌ Backup topilmadi: $BACKUP_DIR/$RESTORE_FILE"; exit 1; }

get_env () { grep -E "^$1=" "$ENV_FILE" | cut -d '=' -f2-; }
POSTGRES_DB=$(get_env POSTGRES_DB); POSTGRES_USER=$(get_env POSTGRES_USER); POSTGRES_PASSWORD=$(get_env POSTGRES_PASSWORD)

read -r -p "DIQQAT: '$POSTGRES_DB' bazasi va media fayllar backup bilan ALMASHTIRILADI. Davom etasizmi? [yes/NO] " ans
[ "$ans" = "yes" ] || { echo "Bekor qilindi."; exit 1; }

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

echo "=== [$(date)] Restore boshlandi: $RESTORE_FILE ==="
unzip -o "$BACKUP_DIR/$RESTORE_FILE" -d "$TMP" >/dev/null

SQL_FILE=$(find "$TMP" -type f -name "db.sql" | head -n 1)
[ -n "$SQL_FILE" ] || { echo "❌ Arxivda db.sql yo'q."; exit 1; }

echo "→ PostgreSQL tiklanmoqda..."
docker exec -i -e PGPASSWORD="$POSTGRES_PASSWORD" forest_postgres_prod \
    psql -v ON_ERROR_STOP=0 -U "$POSTGRES_USER" -d "$POSTGRES_DB" < "$SQL_FILE" >/dev/null

MEDIA_ZIP=$(find "$TMP" -type f -name "media.zip" | head -n 1)
if [ -n "$MEDIA_ZIP" ]; then
    echo "→ Media tiklanmoqda..."
    unzip -o "$MEDIA_ZIP" -d "$TMP/media_extract" >/dev/null
    # backup.sh konteyner ichidagi /app/media ni ziplagan -> app/media/...
    SRC="$TMP/media_extract/app/media"
    [ -d "$SRC" ] || SRC="$TMP/media_extract"
    mkdir -p "$ROOT/media"
    cp -a "$SRC/." "$ROOT/media/"
fi

echo "✅ Restore tugadi. Konteynerlarni qayta ishga tushiring:"
echo "   docker-compose -f docker/prod/docker-compose-prod.yml restart forest_app forest_celery_worker"
