#!/bin/bash

# Backup script for Railway magicchat project
echo "Starting backup process..."

# Create backup directory
BACKUP_DIR="/tmp/railway_backup"
mkdir -p $BACKUP_DIR

# Backup PostgreSQL
echo "Backing up PostgreSQL..."
pg_dump $DATABASE_URL > $BACKUP_DIR/postgres_backup.sql
echo "PostgreSQL backup completed: $(wc -l $BACKUP_DIR/postgres_backup.sql)"

# Backup Redis
echo "Backing up Redis..."
redis-cli -u $REDIS_URL BGSAVE
echo "Redis BGSAVE initiated"

# Wait for Redis save to complete
sleep 5

# Copy Redis dump file
cp /data/dump.rdb $BACKUP_DIR/redis_dump.rdb 2>/dev/null || echo "Redis dump file not found at /data/dump.rdb"

# List backup files
echo "Backup files created:"
ls -la $BACKUP_DIR/

# Create tar archive
cd /tmp
tar -czf railway_backup.tar.gz railway_backup/
echo "Backup archive created: railway_backup.tar.gz"

echo "Backup process completed!"
