#!/bin/bash
set -e

# ====== Settings ======
# Get absolute path of script directory
SCRIPT_DIR=$(dirname "$(realpath "$0")")
PROJECT_ROOT=$(realpath "$SCRIPT_DIR/../..")

# Load .env file from project root
if [ -f "$PROJECT_ROOT/.env" ]; then
    source "$PROJECT_ROOT/.env"
else
    echo "❌ .env file not found at $PROJECT_ROOT/.env"
    exit 1
fi

DATE=$(date +'%Y-%m-%d_%H-%M')
BACKUP_DIR=$PROJECT_ROOT/backups
PROJECT_NAME="forest_project"

DB_NAME=$POSTGRES_DB
DB_USER=$POSTGRES_USER
DB_PASSWORD=$POSTGRES_PASSWORD
DB_HOST=$POSTGRES_HOST

GPG_PASSWORD="***REMOVED***"
RETENTION_DAYS=1095

mkdir -p "$BACKUP_DIR"

echo "=== Backup started at $DATE ==="

# 1️⃣ PostgreSQL backup (hostdan, konteyner ichida)
echo "Dumping PostgreSQL database..."
docker exec forest_postgres_prod \
    bash -c "export PGPASSWORD=$DB_PASSWORD && pg_dump -U $DB_USER $DB_NAME" \
    > "$BACKUP_DIR/db_$DATE.sql"

if [ $? -ne 0 ]; then
    echo "❌ Database dump failed!"
    exit 1
fi

# 2️⃣ Media files zipping
echo "Zipping media files..."
zip -r "$BACKUP_DIR/media_$DATE.zip" "$PROJECT_ROOT/src/media" >/dev/null

# 3️⃣ Combine both
cd "$BACKUP_DIR"
zip -r "${PROJECT_NAME}_backup_$DATE.zip" "db_$DATE.sql" "media_$DATE.zip" >/dev/null

# 4️⃣ Encrypt final zip
echo "Encrypting..."
echo "$GPG_PASSWORD" | gpg --batch --yes --passphrase-fd 0 -c "${PROJECT_NAME}_backup_$DATE.zip"

# 5️⃣ Cleanup temp files
rm "db_$DATE.sql" "media_$DATE.zip" "${PROJECT_NAME}_backup_$DATE.zip"

# 6️⃣ Delete old backups
find "$BACKUP_DIR" -type f -name "*.gpg" -mtime +$RETENTION_DAYS -exec rm {} \;

echo "✅ Backup completed: ${PROJECT_NAME}_backup_$DATE.zip.gpg"
