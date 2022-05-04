#!/bin/bash

mkdir -p media
mkdir -p logs
touch logs/debug.log
touch logs/address.log

# Collect static files
echo "Collect static files"
python manage.py collectstatic --noinput

# Creating migration files
echo "Applying makemigrations"
python manage.py makemigrations

# Apply database migrations
echo "Applying migrate"
python manage.py migrate

# Start Gunicorn processes
echo "Starting Gunicorn Server"
gunicorn log1.wsgi:application --bind 0.0.0.0:5000 --workers 8
