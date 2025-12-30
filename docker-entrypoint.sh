#!/bin/bash
set -e

# Wait for database to be ready (if using external database)
# Uncomment and modify if needed:
# while ! python manage.py dbshell --command "SELECT 1" > /dev/null 2>&1; do
#   echo "Waiting for database..."
#   sleep 1
# done

# Run migrations
echo "Running migrations..."
python manage.py migrate --noinput

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput || true

# Start Django-Q cluster in background
echo "Starting Django-Q cluster..."
python manage.py qcluster &

# Start Django development server
echo "Starting Django server..."
exec python manage.py runserver 0.0.0.0:8000

