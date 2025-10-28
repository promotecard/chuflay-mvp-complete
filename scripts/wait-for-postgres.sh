#!/usr/bin/env bash
# Usage: ./wait-for-postgres.sh [host] [port] [timeout]
HOST=${1:-localhost}
PORT=${2:-5432}
TIMEOUT=${3:-60}

echo "Waiting for postgres at ${HOST}:${PORT} (timeout ${TIMEOUT}s)..."
for i in $(seq 1 $TIMEOUT); do
  pg_isready -h ${HOST} -p ${PORT} -U postgres >/dev/null 2>&1 && { echo "Postgres is ready"; exit 0; }
  sleep 1
done
echo "Timed out waiting for Postgres" >&2
exit 1
