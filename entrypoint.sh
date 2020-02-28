#!/bin/bash

mkdir -p media

echo "Exporting env variables"

export ENV=local DEBUG=True

export DB_HOST=13.126.170.15 DB_PORT=5432 DB_NAME=log1_db DB_USER=log1_user DB_PASSWORD=consultadd@505!

export EMAIL_PORT=587 EMAIL_HOST_USER=apikey EMAIL_HOST='smtp.sendgrid.net' DEFAULT_FROM_EMAIL=Log1@consultadd.com EMAIL_API_KEY=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

export AWS_REGION_NAME=ap-south-1 AWS_STORAGE_BUCKET_NAME=log1-demo AWS_STORAGE_BACKUP_BUCKET_NAME=log1-demo AWS_ACCESS_KEY_ID=AKIA37EQCWV5HGQYHWOS AWS_SECRET_ACCESS_KEY=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

export FCM_SERVER_KEY=AAAAng1WH_g:APA91bFHTBHoCTCnNZeOfUgua5QKawMt9q1dmQaa_Yuw7LsVLasLCUIvLlkE4bfbP9e_Y7SFTrKJKk5zeF2vtZ7Yx7HyfTANClEcYgasi_E9TAgSbiQzExhcEt91v0aAoUvWt8l8x02M

# Collect static files
echo "Collect static files"
python manage.py collectstatic --noinput

# Creating migration files
echo "Appling makemigrations"
# python manage.py makemigrations

# Apply database migrations
echo "Apply database migrations"
python manage.py migrate

# Start Gunicorn processes
echo "Starting Gunicorn Server"
gunicorn log1.wsgi:application --bind 0.0.0.0:8000 --workers 4


# Start server
# echo "Starting server"
# python manage.py runserver 0.0.0.0:8000
