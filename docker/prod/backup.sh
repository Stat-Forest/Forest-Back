#!/bin/bash

# ====== Settings ======
source ../../.env  # Load DB info from .env

DATE=$(date +'%Y-%m-%d_%H-%M')
BACKUP_DIR=/backups
PROJECT_NAME="forest_project"

DB_NAME=$POSTGRES_DB
DB_USER=$POSTGRES_USER
DB_PASSWORD=$POSTGRES_PASSWORD
DB_HOST=$DB_HOST

# GPG encryption key
GPG_PASSWORD="SuperSecretBackupKey123"

# Eski fayllarni o‘chirish muddati (kun) → 3 yil = 1095 kun
RETENTION_DAYS=1095

# Create backup directory if not exists
mkdir -p $BACKUP_DIR

echo "=== Backup started at $DATE ==="

# 1️⃣ PostgreSQL database backup
echo "Dumping PostgreSQL database..."
docker exec forest_postgres_prod \
    bash -c "export PGPASSWORD=$DB_PASSWORD && pg_dump -U $DB_USER -h localhost $DB_NAME" \
    > $BACKUP_DIR/db_$DATE.sql

if [ $? -ne 0 ]; then
    echo "❌ Database dump failed!"
    exit 1
fi

# 2️⃣ Media zipping
echo "Zipping media files..."
zip -r $BACKUP_DIR/media_$DATE.zip ../../media >/dev/null

# 3️⃣ Creating final backup archive
cd $BACKUP_DIR
zip -r ${PROJECT_NAME}_backup_$DATE.zip db_$DATE.sql media_$DATE.zip >/dev/null

# 4️⃣ Encrypt final zip file with GPG
echo "Encrypting backup..."
echo $GPG_PASSWORD | gpg --batch --yes --passphrase-fd 0 -c ${PROJECT_NAME}_backup_$DATE.zip

# 5️⃣ Remove unencrypted files
rm db_$DATE.sql media_$DATE.zip ${PROJECT_NAME}_backup_$DATE.zip

# 6️⃣ Delete old backups (older than RETENTION_DAYS)
find $BACKUP_DIR -type f -name "*.gpg" -mtime +$RETENTION_DAYS -exec rm {} \;

echo "✅ Backup completed: ${PROJECT_NAME}_backup_$DATE.zip.gpg"
echo "==========================="
