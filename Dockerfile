# pull official base image
FROM python:3.7

# set work directory
WORKDIR /usr/src/log1

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# install psycopg2 dependencies
# RUN apt update && apt add postgresql-dev gcc python3-dev musl-dev

# install dependencies
RUN pip install --upgrade pip
COPY ./requirements/base.txt /usr/src/log1/requirements/prod.txt
RUN pip install -r requirements/prod.txt

# copy project
COPY . /usr/src/log1/

# Docker entry point
COPY entrypoint.sh /entrypoint.sh
ENTRYPOINT ["/usr/src/log1/entrypoint.sh"]
