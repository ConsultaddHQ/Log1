FROM python:3.12-slim

# Set work directory
RUN mkdir -p /home/app

# create the app user
RUN groupadd --system app && useradd --system --gid app app

# create the appropriate directories
ENV HOME=/home/app
ENV APP_HOME=/home/app/web
RUN mkdir $APP_HOME
WORKDIR $APP_HOME

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install psycopg2 dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq-dev gcc python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY ./requirements.txt $APP_HOME/requirements.txt
RUN pip install --upgrade "pip<24.1"
RUN pip install -r requirements.txt

# copy entrypoint.prod.sh
COPY ./entrypoint.sh .
RUN sed -i 's/\r$//g'  $APP_HOME/entrypoint.sh

# copy project
COPY . $APP_HOME
RUN sed -i 's/\r$//g'  $APP_HOME/entrypoint.sh
RUN chmod +x  $APP_HOME/entrypoint.sh

# chown all the files to the app user
RUN chown -R app:app $APP_HOME

# change to the app user
USER app

# run entrypoint.prod.sh
ENTRYPOINT ["/home/app/web/entrypoint.sh"]
