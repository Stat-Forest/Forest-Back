#!/bin/bash
set -e

SCRIPT_DIR=$(dirname "$(realpath "$0")")
PROJECT_ROOT=$(realpath "$SCRIPT_DIR/../..")
ENV_FILE="$PROJECT_ROOT/.env"

if [ ! -f "$ENV_FILE" ]; then
    echo "❌ .env file not found at $ENV_FILE"
    exit 1
fi

# Read variables safely
DB_NAME=$(grep -E '^POSTGRES_DB=' $ENV_FILE | cut -d '=' -f2)
DB_USER=$(grep -E '^POSTGRES_USER=' $ENV_FILE | cut -d '=' -f2)
DB_PASSWORD=$(grep -E '^POSTGRES_PASSWORD=' $ENV_FILE | cut -d '=' -f2)
DB_HOST=$(grep -E '^POSTGRES_HOST=' $ENV_FILE | cut -d '=' -f2)

DATE=$(date +'%Y-%m-%d_%H-%M')
BACKUP_DIR=$PROJECT_ROOT/backups
PROJECT_NAME="forest_project"

GPG_PASSWORD="SuperSecretBackupKey123"
RETENTION_DAYS=1095

mkdir -p "$BACKUP_DIR"

echo "=== Backup started at $DATE ==="

echo "Dumping PostgreSQL database..."
docker exec forest_postgres_prod \
    bash -c "export PGPASSWORD='$DB_PASSWORD' && pg_dump -U $DB_USER -h localhost $DB_NAME" \
    > "$BACKUP_DIR/db_$DATE.sql"

if [ $? -ne 0 ]; then
    echo "❌ Database dump failed!"
    exit 1
fi

echo "Zipping media files..."
zip -r "$BACKUP_DIR/media_$DATE.zip" "$PROJECT_ROOT/src/media" >/dev/null

cd "$BACKUP_DIR"
zip -r "${PROJECT_NAME}_backup_$DATE.zip" "db_$DATE.sql" "media_$DATE.zip" >/dev/null

echo "Encrypting..."
echo "$GPG_PASSWORD" | gpg --batch --yes --passphrase-fd 0 -c "${PROJECT_NAME}_backup_$DATE.zip"

rm "db_$DATE.sql" "media_$DATE.zip" "${PROJECT_NAME}_backup_$DATE.zip"

find "$BACKUP_DIR" -type f -name "*.gpg" -mtime +$RETENTION_DAYS -exec rm {} \;

echo "✅ Backup completed: ${PROJECT_NAME}_backup_$DATE.zip.gpg"
