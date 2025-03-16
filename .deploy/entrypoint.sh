#!/bin/bash

mkdir -p staticfiles static

# Run migrations
echo "Running migrations"
python manage.py migrate
python manage.py create_paycom_user

# Collect static files
echo "Collecting static files"
python manage.py collectstatic --no-input

# Start Django server
echo "Starting Django server"
gunicorn core.wsgi:application --bind 0.0.0.0:8000 --workers 2
