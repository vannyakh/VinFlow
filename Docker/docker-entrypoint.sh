#!/bin/bash
set -e

echo "Starting VinFlow Docker entrypoint..."

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL..."
while ! nc -z $DB_HOST $DB_PORT; do
  sleep 0.1
done
echo "PostgreSQL is ready!"

# Wait for Redis to be ready
echo "Waiting for Redis..."
REDIS_HOST=$(echo $CELERY_BROKER_URL | sed -n 's#.*://\([^:]*\).*#\1#p')
while ! nc -z $REDIS_HOST 6379; do
  sleep 0.1
done
echo "Redis is ready!"

# Run migrations
echo "Running database migrations..."
python manage.py migrate --noinput

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Compile translation files
echo "Compiling translation files..."
python manage.py compilemessages || true

echo "Starting application..."
exec "$@"

