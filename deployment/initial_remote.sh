#!/bin/sh

venv=$2
branch=$3
git_url=$4

sudo add-apt-repository ppa:maxmind/ppa -y
sudo apt update && sudo apt upgrade -y
sudo apt autoremove -y
sudo apt install build-essential -y

# Nginx and Gunicorn Installation
sudo apt install nginx
sudo apt-get install gunicorn

sudo mkdir -p /var/www/cainc.com/html
sudo chown -R ubuntu:ubuntu /var/www/cainc.com/html
sudo chmod -R 755 /var/www/cainc.com
echo " <html><head><title>Welcome to Consultadd.com!</title></head><body> <h1>Success!  The Consultadd.com server block is working!</h1></body></html>" > /var/www/cainc.com/html/index.html

# Postgres Installation
sudo apt install postgresql postgresql-contrib postgis
sudo apt install python3-pip

cd /home/ubuntu/ || exit

git clone "$git_url"


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


cd $(echo "$git_url"| cut -f2 -d"." | cut -f3 -d "/") || exist

git checkout "$branch"

if [ -d "logs" ]
then
    echo "Log folder exists."
else
    mkdir logs
    touch logs/debug.log
fi

sudo chmod -R 777 logs

git pull origin "$branch"


echo "Installation and project cloning is complete"

exit