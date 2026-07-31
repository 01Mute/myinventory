#!/bin/sh
# Issues the first Let's Encrypt certificate for $DOMAIN, then hands renewal
# over to the certbot service in docker-compose.prod.yml.
#
# Run this once, from the repo root on the server, after DOMAIN is set in .env
# and its DNS record points at this host. Re-running is harmless: certbot keeps
# the existing certificate unless it is close to expiring.
#
# There is a startup ordering problem this script exists to solve. nginx refuses
# to start when a configured ssl_certificate file is missing, but certbot needs
# nginx already serving /.well-known/acme-challenge to answer the HTTP-01
# challenge. Neither can go first. The fix is a throwaway self-signed
# certificate that gets nginx up, after which the real one replaces it.
set -eu

cd "$(dirname "$0")/.."
COMPOSE="docker compose -f docker-compose.prod.yml"

[ -f .env ] || { echo "No .env in $(pwd)" >&2; exit 1; }
DOMAIN=$(grep -E '^DOMAIN=' .env | cut -d= -f2- | tr -d '"'"'"' ' | head -1)
EMAIL=$(grep -E '^LETSENCRYPT_EMAIL=' .env | cut -d= -f2- | tr -d '"'"'"' ' | head -1)
[ -n "$DOMAIN" ] || { echo "DOMAIN is empty in .env" >&2; exit 1; }

LIVE="/etc/letsencrypt/live/$DOMAIN"
echo "==> Domain: $DOMAIN"

# Without an address Let's Encrypt cannot warn you when renewal has been
# failing and the certificate is about to lapse.
if [ -n "$EMAIL" ]; then
  EMAIL_ARG="--email $EMAIL"
else
  echo "    (no LETSENCRYPT_EMAIL — registering without expiry notifications)"
  EMAIL_ARG="--register-unsafely-without-email"
fi

# --no-deps on every one-off run below: the certbot service depends_on nginx for
# normal operation, but compose would then try to start nginx first — which is
# exactly what cannot happen yet on a first issuance, because the certificate
# nginx is configured to load does not exist until these commands have run.
echo "==> Placing a temporary self-signed certificate so nginx can start"
$COMPOSE run --rm --no-deps --entrypoint /bin/sh certbot -c "
  set -e
  if [ ! -f $LIVE/fullchain.pem ]; then
    command -v openssl >/dev/null 2>&1 || apk add --no-cache openssl >/dev/null 2>&1
    mkdir -p $LIVE
    openssl req -x509 -nodes -newkey rsa:2048 -days 1 \
      -keyout $LIVE/privkey.pem -out $LIVE/fullchain.pem -subj '/CN=$DOMAIN'
  fi
"

echo "==> Starting nginx with the placeholder"
$COMPOSE up -d --force-recreate nginx
sleep 5

# nginx has the placeholder open already, so removing it now costs nothing and
# keeps certbot from treating the hand-made directory as one of its lineages.
echo "==> Removing the placeholder and requesting the real certificate"
$COMPOSE run --rm --no-deps --entrypoint /bin/sh certbot -c "rm -rf $LIVE /etc/letsencrypt/archive/$DOMAIN /etc/letsencrypt/renewal/$DOMAIN.conf"

$COMPOSE run --rm --no-deps --entrypoint certbot certbot certonly \
  --webroot -w /var/www/certbot \
  -d "$DOMAIN" \
  $EMAIL_ARG \
  --agree-tos --no-eff-email --non-interactive

echo "==> Reloading nginx onto the real certificate"
$COMPOSE up -d
$COMPOSE exec nginx nginx -s reload

echo "==> Done. Certificate:"
$COMPOSE run --rm --no-deps --entrypoint certbot certbot certificates
