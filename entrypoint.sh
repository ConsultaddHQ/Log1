#!/bin/bash

# Collect static files
# echo "Collect static files"
# python manage.py collectstatic --noinput

# Creating migration files
# echo "Appling makemigrations"
# python manage.py makemigrations

# Apply database migrations
echo "Apply database migrations"
python manage.py migrate

# Start Gunicorn processes
# echo "Starting Gunicorn Server"
# gunicorn log1.wsgi:application --bind 0.0.0.0:8000 --workers 4


# Start server
echo "Starting server"
python manage.py runserver 0.0.0.0:8000