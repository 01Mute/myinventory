#!/bin/sh
# Installs a daily nginx reload so renewed certificates take effect.
#
# nginx reads its certificate once at startup and holds it in memory. The
# certbot service renews on disk, but the running nginx keeps serving the old
# certificate until reloaded, so without this the certificate silently expires
# from a visitor's point of view while looking fine on disk.
#
# This lives on the host rather than as a loop inside the nginx container
# because overriding that container's command stops the image from rendering
# its config template. Run once; re-running just rewrites the same entry.
set -eu

APP_DIR=$(cd "$(dirname "$0")/.." && pwd)
MARKER="# myinventory-nginx-reload"
LINE="17 4 * * * cd $APP_DIR && docker compose -f docker-compose.prod.yml exec -T nginx nginx -s reload >/dev/null 2>&1 $MARKER"

# Daily at 04:17 — off the hour because certbot's own renewal checks cluster on
# round times, and this only needs to land sometime after one of them.
crontab -l 2>/dev/null | grep -v "$MARKER" | { cat; echo "$LINE"; } | crontab -

echo "Installed:"
crontab -l | grep "$MARKER"
