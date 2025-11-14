#!/bin/bash
set -e

# ====== Settings ======
SCRIPT_DIR=$(dirname "$(realpath "$0")")
PROJECT_ROOT=$(realpath "$SCRIPT_DIR/../..")
ENV_FILE="$PROJECT_ROOT/.env"

if [ ! -f "$ENV_FILE" ]; then
    echo "❌ .env file not found at $ENV_FILE"
    exit 1
fi

# Read DB info from .env safely
DB_NAME=$(grep -E '^POSTGRES_DB=' "$ENV_FILE" | cut -d '=' -f2)
DB_USER=$(grep -E '^POSTGRES_USER=' "$ENV_FILE" | cut -d '=' -f2)
DB_PASSWORD=$(grep -E '^POSTGRES_PASSWORD=' "$ENV_FILE" | cut -d '=' -f2)
DB_HOST=$(grep -E '^DB_HOST=' "$ENV_FILE" | cut -d '=' -f2)
DB_PORT=$(grep -E '^DB_PORT=' "$ENV_FILE" | cut -d '=' -f2)

DATE=$(date +'%Y-%m-%d_%H-%M')
YEAR=$(date +'%Y')
MONTH=$(date +'%m')
DAY=$(date +'%d')

PROJECT_NAME="forest_project"
BACKUP_ROOT=/backups
BACKUP_DIR="$BACKUP_ROOT/$YEAR/$MONTH/$DAY"

RETENTION_DAYS=1095

mkdir -p "$BACKUP_DIR"

echo "=== Backup started at $DATE ==="

# 1️⃣ Database dump
echo "Dumping PostgreSQL database..."
export PGPASSWORD="$DB_PASSWORD"
pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" "$DB_NAME" > "$BACKUP_DIR/db_$DATE.sql"

if [ $? -ne 0 ]; then
    echo "❌ Database dump failed!"
    exit 1
fi

# 2️⃣ Media zipping
echo "Zipping media files..."
zip -r "$BACKUP_DIR/media_$DATE.zip" "$PROJECT_ROOT/src/media" >/dev/null 2>&1 || true

# 3️⃣ Create final zip
cd "$BACKUP_DIR"
zip -r "${PROJECT_NAME}_backup_$DATE.zip" "db_$DATE.sql" "media_$DATE.zip" >/dev/null

# 4️⃣ Cleanup temp files (leave only final zip)
rm -f "db_$DATE.sql" "media_$DATE.zip"

# 5️⃣ Delete old backups
find "$BACKUP_ROOT" -type f -name "*.zip" -mtime +$RETENTION_DAYS -exec rm {} \;

echo "✅ Backup completed successfully: ${BACKUP_DIR}/${PROJECT_NAME}_backup_$DATE.zip"
