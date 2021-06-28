FROM python:3.8-alpine

WORKDIR /app

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# install source packages dependencies
RUN apk update && apk upgrade && \
    apk add --no-cache git gcc musl-dev postgresql-dev

# Install dependencies
COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

COPY . .
