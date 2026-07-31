#!/bin/sh
# Pulls main, rebuilds, and reclaims what the rebuild superseded.
#
# Run from anywhere on the server: sh ~/myinventory/scripts/deploy.sh
#
# Each rebuild of the nginx image leaves the previous one untagged ("dangling")
# and adds BuildKit cache entries. One generation of that is useful — it makes
# the next build fast — but it grows with every deploy if nothing prunes it, and
# this host only has 8GB. So the build keeps its cache and the *previous*
# generation is dropped once the new one is running.
set -eu

cd "$(dirname "$0")/.."
COMPOSE="docker compose -f docker-compose.prod.yml"

echo "==> Fetching main"
git fetch --prune origin
git reset --hard origin/main
echo "    now at $(git rev-parse --short HEAD) — $(git log -1 --pretty=%s)"

echo "==> Building and restarting"
$COMPOSE up -d --build

echo "==> Waiting for containers to settle"
sleep 8
$COMPOSE ps --format "{{.Service}}\t{{.Status}}"

# Only reclaim once the new containers are actually up. Pruning first would
# delete the image the running containers still reference if the build failed.
if [ "$($COMPOSE ps -q | wc -l)" -lt 4 ]; then
  echo "!!  Fewer than 4 services running — skipping cleanup so the previous"
  echo "!!  image stays available to roll back to."
  exit 1
fi

echo "==> Reclaiming superseded layers"
# Dangling only: images still tagged, and every volume, are left alone. Never
# add --volumes or -a here — the Postgres data and the uploaded media live in
# volumes and a full system prune would take them.
docker image prune -f
# Caps the cache instead of emptying it, so the next build still gets a warm
# start while the total stays bounded across many deploys.
docker builder prune -f --keep-storage 512MB >/dev/null

echo "==> Disk after cleanup"
docker system df
df -h / | awk 'NR==2{print "    root filesystem: "$3" used of "$2" ("$5")"}'
