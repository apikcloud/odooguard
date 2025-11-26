#!/bin/sh
set -e

# Export all env vars so cron gets them
printenv > /etc/environment

# Log path = stdout of PID 1 (the container)
LOG="/proc/1/fd/1"

# Build cron line (no `root`, format crontab-compatible)
CRON_LINE="${CRON_SCHEDULE} python3 /app/backup.py >> ${LOG} 2>&1"

echo "${CRON_LINE}" > /etc/cron.d/odoo-backup
echo "" >> /etc/cron.d/odoo-backup
chmod 0644 /etc/cron.d/odoo-backup

# Load into user crontab
crontab /etc/cron.d/odoo-backup

echo "[odooguard] cron scheduled: ${CRON_SCHEDULE}" >&1

# Run cron in foreground, logs will naturally appear in stdout
cron -f
