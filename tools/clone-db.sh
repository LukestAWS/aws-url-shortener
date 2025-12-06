#!/usr/bin/env bash
set -euo pipefail

# Clone a Postgres database by dumping and restoring.
# This script assumes you have network access to both source and destination DBs
# and that `pg_dump`, `pg_restore` and `psql` are installed.
#
# Usage (recommended - file dump):
#   SRC_DB_URL="postgresql://user:pw@src-host:5432/db?sslmode=require" \
#   DST_DB_URL="postgresql://user:pw@dst-host:5432/db?sslmode=require" \
#   ./tools/clone-db.sh
#
# Usage (streaming plain SQL, may be slower):
#   SRC_DB_URL=... DST_DB_URL=... ./tools/clone-db.sh --stream

if ! command -v pg_dump >/dev/null 2>&1; then
  echo "pg_dump not found; please install postgresql-client or psql tools." >&2
  exit 1
fi

if ! command -v pg_restore >/dev/null 2>&1; then
  echo "pg_restore not found; please install postgresql-client or psql tools." >&2
  exit 1
fi

SRC_DB_URL="${SRC_DB_URL:-}" 
DST_DB_URL="${DST_DB_URL:-}"
STREAM_MODE=0

if [ "${1:-}" = "--stream" ] || [ "${STREAM:-}" = "1" ]; then
  STREAM_MODE=1
fi

if [ -z "$SRC_DB_URL" ] || [ -z "$DST_DB_URL" ]; then
  echo "Missing SRC_DB_URL or DST_DB_URL. See header of this script for usage." >&2
  exit 1
fi

echo "Starting DB clone"
echo "Source:    (masked) ${SRC_DB_URL//://***://}" 
echo "Destination:(masked) ${DST_DB_URL//://***://}"

if [ "$STREAM_MODE" -eq 1 ]; then
  echo "Using streaming (plain SQL) mode. This may be slower and may not preserve owners/roles exactly."
  echo "Running: pg_dump --no-owner --no-acl --format=plain --dbname=SRC | psql DST"
  pg_dump --no-owner --no-acl --format=plain --dbname="$SRC_DB_URL" | psql "$DST_DB_URL"
  echo "Streaming restore finished."
  exit 0
fi

# File-based dump/restore (recommended): create a compressed custom-format dump
TMP_DUMP="/tmp/db-clone-$(date +%s).dump"
echo "Creating custom-format dump to $TMP_DUMP"
pg_dump --format=custom --dbname="$SRC_DB_URL" -f "$TMP_DUMP"

echo "Restoring dump to destination"
# --no-owner and --no-acl are useful when restoring into environments with different roles
pg_restore --dbname="$DST_DB_URL" --no-owner --no-acl --jobs=4 "$TMP_DUMP"

echo "Restore finished. Removing dump file"
rm -f "$TMP_DUMP"

echo "DB clone complete. Verify application and run migrations if needed."
