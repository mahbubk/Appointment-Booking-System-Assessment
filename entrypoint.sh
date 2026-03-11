#!/bin/sh
set -e

echo "Waiting for PostgreSQL..."
until nc -z "$DB_HOST" "$DB_PORT"; do
    sleep 1
done
echo "PostgreSQL ready."

echo "Waiting for Redis..."
until nc -z "$REDIS_HOST" "$REDIS_PORT"; do
    sleep 1
done
echo "Redis ready."

if [ "$RUN_MIGRATIONS" = "true" ]; then
    python manage.py migrate --noinput
fi

exec "$@"