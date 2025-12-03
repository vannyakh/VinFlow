#!/bin/bash

###############################################################################
# VinFlow Database Backup Script
# Run this script via cron for automated backups
###############################################################################

set -e

# Configuration
PROJECT_NAME="vinflow"
PROJECT_DIR="/var/www/${PROJECT_NAME}"
BACKUP_DIR="/var/backups/${PROJECT_NAME}"
RETENTION_DAYS=30  # Keep backups for 30 days

# Load environment variables
if [ -f "${PROJECT_DIR}/.env" ]; then
    export $(cat ${PROJECT_DIR}/.env | grep -v '^#' | xargs)
else
    echo "Error: .env file not found"
    exit 1
fi

# Create backup directory if it doesn't exist
mkdir -p ${BACKUP_DIR}

# Generate timestamp
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/vinflow_${TIMESTAMP}.sql"

# Backup database
echo "Starting database backup..."
pg_dump -U ${DB_USER} -h ${DB_HOST} ${DB_NAME} > ${BACKUP_FILE}

# Compress backup
echo "Compressing backup..."
gzip ${BACKUP_FILE}

# Calculate backup size
BACKUP_SIZE=$(du -h "${BACKUP_FILE}.gz" | cut -f1)
echo "Backup completed: ${BACKUP_FILE}.gz (${BACKUP_SIZE})"

# Remove old backups (older than RETENTION_DAYS)
echo "Removing backups older than ${RETENTION_DAYS} days..."
find ${BACKUP_DIR} -name "vinflow_*.sql.gz" -mtime +${RETENTION_DAYS} -delete

# Count remaining backups
BACKUP_COUNT=$(ls -1 ${BACKUP_DIR}/vinflow_*.sql.gz 2>/dev/null | wc -l)
echo "Total backups: ${BACKUP_COUNT}"

# Optional: Upload to remote storage (uncomment and configure)
# rsync -avz ${BACKUP_FILE}.gz user@backup-server:/backups/vinflow/
# aws s3 cp ${BACKUP_FILE}.gz s3://your-bucket/backups/vinflow/

echo "Backup process completed successfully!"

