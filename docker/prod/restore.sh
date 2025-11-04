#!/bin/bash

set -e  # stop on any error

# ====== Restore Settings ======
ENV_FILE="$(dirname "$0")/../../.env"
if [ ! -f "$ENV_FILE" ]; then
    echo "❌ .env file not found at $ENV_FILE"
    exit 1
fi

source "$ENV_FILE"

BACKUP_DIR=/backups
GPG_PASSWORD="***REMOVED***"
PROJECT_NAME="forest_project"
RESTORE_FILE=$1

if [ -z "$RESTORE_FILE" ]; then
    echo "❌ Usage: ./restore.sh project_backup_YYYY-MM-DD_HH-MM.zip.gpg"
    exit 1
fi

cd "$BACKUP_DIR"

if [ ! -f "$RESTORE_FILE" ]; then
    echo "❌ Backup file not found: $BACKUP_DIR/$RESTORE_FILE"
    exit 1
fi

echo "=== [$(date)] Starting restore ==="
echo "→ Decrypting backup..."
echo "$GPG_PASSWORD" | gpg --batch --yes --passphrase-fd 0 -o decrypted.zip -d "$RESTORE_FILE"

# 2️⃣ Unzip files
echo "→ Extracting backup files..."
unzip -o decrypted.zip -d ./restore_tmp >/dev/null
rm decrypted.zip

# 3️⃣ Restore database
SQL_FILE=$(find ./restore_tmp -type f -name "db_*.sql" | head -n 1)
if [ -z "$SQL_FILE" ]; then
    echo "❌ No SQL file found in backup."
    rm -rf ./restore_tmp
    exit 1
fi

echo "→ Restoring PostgreSQL database..."
docker exec -i forest_postgres_prod \
    bash -c "export PGPASSWORD=$POSTGRES_PASSWORD && psql -U $POSTGRES_USER -d $POSTGRES_DB" \
    < "$SQL_FILE"

# 4️⃣ Restore media
MEDIA_FILE=$(find ./restore_tmp -type f -name "media_*.zip" | head -n 1)
if [ -n "$MEDIA_FILE" ]; then
    echo "→ Restoring media files..."
    unzip -o "$MEDIA_FILE" -d "$(dirname "$0")/../../media" >/dev/null
fi

# 5️⃣ Cleanup
rm -rf ./restore_tmp

echo "✅ Restore completed successfully!"
echo "==============================================================="
