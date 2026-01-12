#!/bin/bash
set -euo pipefail

echo "===== BACKUP STARTED ====="

# ========================
# Paths (container ichida)
# ========================
APP_ROOT="/app"
MEDIA_DIR="$APP_ROOT/media"
ENV_FILE="$APP_ROOT/.env"
BACKUP_ROOT="/backups"

# ========================
# ENV tekshirish
# ========================
if [ ! -f "$ENV_FILE" ]; then
  echo "❌ .env file not found at $ENV_FILE"
  exit 1
fi

# ========================
# ENV yuklash
# ========================
set -o allexport
source "$ENV_FILE"
set +o allexport

# ========================
# Kerakli ENV larni tekshirish
# ========================
REQUIRED_VARS=(
  POSTGRES_DB
  POSTGRES_USER
  POSTGRES_PASSWORD
  DB_HOST
  DB_PORT
)

for var in "${REQUIRED_VARS[@]}"; do
  if [ -z "${!var:-}" ]; then
    echo "❌ ENV variable $var is missing"
    exit 1
  fi
done

# ========================
# Date va papkalar
# ========================
DATE=$(date +"%Y-%m-%d_%H-%M-%S")
YEAR=$(date +"%Y")
MONTH=$(date +"%m")
DAY=$(date +"%d")

PROJECT_NAME="forest_project"
BACKUP_DIR="$BACKUP_ROOT/$YEAR/$MONTH/$DAY"

mkdir -p "$BACKUP_DIR"

# ========================
# 1️⃣ PostgreSQL BACKUP
# ========================
echo "▶ Dumping PostgreSQL database..."

export PGPASSWORD="$POSTGRES_PASSWORD"

pg_dump \
  -h "$DB_HOST" \
  -p "$DB_PORT" \
  -U "$POSTGRES_USER" \
  "$POSTGRES_DB" \
  > "$BACKUP_DIR/db.sql"

echo "✔ Database dumped successfully"

# ========================
# 2️⃣ MEDIA BACKUP
# ========================
if [ ! -d "$MEDIA_DIR" ]; then
  echo "❌ Media directory not found at $MEDIA_DIR"
  exit 1
fi

echo "▶ Zipping media files..."
zip -r "$BACKUP_DIR/media.zip" "$MEDIA_DIR" >/dev/null
echo "✔ Media zipped"

# ========================
# 3️⃣ FINAL ZIP
# ========================
echo "▶ Creating final backup archive..."

cd "$BACKUP_DIR"
zip -r "${PROJECT_NAME}_backup_$DATE.zip" db.sql media.zip >/dev/null

# ========================
# 4️⃣ TEMP FILES CLEANUP
# ========================
rm -f db.sql media.zip

# ========================
# 5️⃣ OLD BACKUPS CLEANUP (3 yil)
# ========================
find "$BACKUP_ROOT" -type f -name "*.zip" -mtime +1095 -delete

echo "✅ BACKUP COMPLETED SUCCESSFULLY"
echo "📦 Backup file:"
echo "$BACKUP_DIR/${PROJECT_NAME}_backup_$DATE.zip"
