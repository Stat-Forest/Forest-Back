#!/bin/bash
set -euo pipefail

echo "===== BACKUP STARTED ====="

# ========================
# Paths
# ========================
APP_ROOT="/app"
MEDIA_DIR="$APP_ROOT/media"
ENV_FILE="$APP_ROOT/.env"
BACKUP_ROOT="/backups"

# ========================
# ENV file tekshirish
# ========================
if [ ! -f "$ENV_FILE" ]; then
  echo "❌ .env file not found at $ENV_FILE"
  exit 1
fi

# ========================
# .env dan FAQAT kerakli DB ma’lumotlarni o‘qish
# ========================
get_env () {
  grep -E "^$1=" "$ENV_FILE" | cut -d '=' -f2-
}

POSTGRES_DB=$(get_env POSTGRES_DB)
POSTGRES_USER=$(get_env POSTGRES_USER)
POSTGRES_PASSWORD=$(get_env POSTGRES_PASSWORD)
DB_HOST=$(get_env DB_HOST)
DB_PORT=$(get_env DB_PORT)

# ========================
# Tekshiruv
# ========================
for var in POSTGRES_DB POSTGRES_USER POSTGRES_PASSWORD DB_HOST DB_PORT; do
  if [ -z "${!var}" ]; then
    echo "❌ ENV variable $var is missing"
    exit 1
  fi
done

# ========================
# Date & dirs
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
# 4️⃣ CLEANUP
# ========================
rm -f db.sql media.zip

# ========================
# 5️⃣ RETENTION (3 yil)
# ========================
find "$BACKUP_ROOT" -type f -name "*.zip" -mtime +1095 -delete

echo "✅ BACKUP COMPLETED SUCCESSFULLY"
echo "📦 $BACKUP_DIR/${PROJECT_NAME}_backup_$DATE.zip"
