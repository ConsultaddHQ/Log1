#!/bin/sh

env=$1
venv=$2
branch=$3

echo "VENV name: $venv"

if [ -d "$venv" ]
then
    . "$venv"/bin/activate
    echo "Virtual environment activate"
    echo "Python virtual environment exists."
else
    python3 -m venv venv
    . "$venv"/bin/activate
    echo "Virtual environment activate"
    pip install -r log1/requirements.txt
fi

cd log1/ || exit

if [ -d "logs" ]
then
    echo "Log folder exists."
else
    mkdir logs
    touch logs/debug.log
fi

sudo chmod -R 777 logs

branch=$(git branch | sed -n -e 's/^\* \(.*\)/\1/p')

git pull origin "$branch"

echo "Running Makemigrations command"
python manage.py makemigrations

echo "Running migrate command"
python manage.py migrate

if [ "$env" = "dev" ]
then
    echo "Restarting django server"
else
    echo "Restarting Gunicorn server"
    sudo systemctl restart gunicorn
fi

echo "Deployment is completed "

exit