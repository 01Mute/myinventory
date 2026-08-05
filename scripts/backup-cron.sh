#!/bin/sh
# Installs a daily backup of the demo account.
#
# The demo account is the one anybody can log into, so it is the one strangers
# edit and the one worth keeping copies of. backup_demo writes a dated
# directory holding the account's rows and the images they reference, then
# drops directories past the retention window.
#
# Backups land on the host through a bind mount rather than in a named volume,
# because the point of them is to be copied off this box. Run once; re-running
# just rewrites the same entry.
set -eu

APP_DIR=$(cd "$(dirname "$0")/.." && pwd)
KEEP_DAYS=${KEEP_DAYS:-14}
BACKUP_DIR=${BACKUP_DIR:-$APP_DIR/backups}

mkdir -p "$BACKUP_DIR"

# Amazon Linux 2023's minimal image ships without cron at all, so this is not
# the safe assumption it looks like on a normal distro.
if ! command -v crontab >/dev/null 2>&1; then
  echo "cron is not installed — installing cronie"
  sudo dnf install -y cronie >/dev/null 2>&1 || sudo apt-get install -y -qq cron
  sudo systemctl enable --now crond 2>/dev/null || sudo systemctl enable --now cron
fi

MARKER="# myinventory-demo-backup"
COMMAND="docker compose -f docker-compose.prod.yml exec -T backend python manage.py backup_demo --keep-days $KEEP_DAYS"
LINE="41 3 * * * cd $APP_DIR && $COMMAND >>$BACKUP_DIR/backup.log 2>&1 $MARKER"

# Daily at 03:41 — before the 04:17 nginx reload so the two never overlap, and
# off the hour because scheduled jobs cluster on round times.
crontab -l 2>/dev/null | grep -v "$MARKER" | { cat; echo "$LINE"; } | crontab -

echo "Installed:"
crontab -l | grep "$MARKER"
echo
echo "Backups: $BACKUP_DIR (keeping $KEEP_DAYS days)"
echo "Restore: docker compose -f docker-compose.prod.yml exec -T backend \\"
echo "           python manage.py seed_demo --fixture backups/<이름>/data.json"
