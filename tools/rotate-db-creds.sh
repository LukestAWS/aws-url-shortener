#!/usr/bin/env bash
set -euo pipefail

# Rotate DB credentials by creating a new role, updating the Fly app secret,
# and (optionally) dropping the old role once verified.
#
# Requirements:
# - `psql` (Postgres client) available and network-accessible admin connection
# - `flyctl` authenticated locally or via CI (for `fly secrets set`)
#
# Usage:
#   ADMIN_DB_URL="postgresql://admin:pw@host:5432/postgres?sslmode=require" \
#   FLY_APP=aws-url-shortener ./tools/rotate-db-creds.sh

ADMIN_DB_URL="${ADMIN_DB_URL:-}"
FLY_APP="${FLY_APP:-}"
DB_NAME="${DB_NAME:-postgres}"
DB_HOST="${DB_HOST:-}"
HEALTHCHECK_URL="${HEALTHCHECK_URL:-}" # optional: https://your-app.fly.dev/health

if [ -z "$ADMIN_DB_URL" ] || [ -z "$FLY_APP" ]; then
  echo "ADMIN_DB_URL and FLY_APP must be set. Example: ADMIN_DB_URL=... FLY_APP=aws-url-shortener ./tools/rotate-db-creds.sh" >&2
  exit 1
fi

if ! command -v psql >/dev/null 2>&1; then
  echo "psql not found; please install postgresql-client." >&2
  exit 1
fi

if ! command -v fly >/dev/null 2>&1; then
  echo "flyctl not found; please install flyctl and authenticate (fly auth login)." >&2
  exit 1
fi

NEW_USER="appuser_$(date +%s)"
NEW_PASS="$(openssl rand -base64 32 | tr -d '/+=' | cut -c1-24)"

echo "Creating new DB role: $NEW_USER"

psql "$ADMIN_DB_URL" <<SQL
CREATE ROLE ${NEW_USER} WITH LOGIN PASSWORD '${NEW_PASS}';
GRANT CONNECT ON DATABASE ${DB_NAME} TO ${NEW_USER};
\c ${DB_NAME}
GRANT USAGE ON SCHEMA public TO ${NEW_USER};
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO ${NEW_USER};
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO ${NEW_USER};
SQL

if [ -z "$DB_HOST" ]; then
  # try to extract host from ADMIN_DB_URL
  DB_HOST=$(python - <<PY
from urllib.parse import urlparse, parse_qs
u = urlparse("$ADMIN_DB_URL")
print(u.hostname or "")
PY)
fi

NEW_DATABASE_URL="postgresql://${NEW_USER}:${NEW_PASS}@${DB_HOST}:5432/${DB_NAME}?sslmode=require"

echo "Updating Fly secret for app ${FLY_APP}"
fly secrets set DATABASE_URL="$NEW_DATABASE_URL" -a "$FLY_APP"

echo "Waiting for app to pick up the new secret and restart (sleep 15s)"
sleep 15

if [ -n "$HEALTHCHECK_URL" ]; then
  echo "Running healthcheck against $HEALTHCHECK_URL"
  if curl -fsS "$HEALTHCHECK_URL"; then
    echo "Healthcheck OK"
  else
    echo "Healthcheck failed; do not drop old credentials yet." >&2
    exit 1
  fi
else
  echo "No HEALTHCHECK_URL provided. Please verify the app is healthy before removing old credentials."
fi

echo "Rotation done. New database user: $NEW_USER"
echo "To drop an old role (once verified), run as admin: DROP ROLE <old_user>;"
