###########
# BUILDER #
###########

# pull official base image
FROM python:3.8-alpine as builder

# set work directory
WORKDIR /usr/src/app

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# install source packages dependencies
RUN apk update && apk upgrade && \
    apk add --no-cache gcc musl-dev postgresql-dev

# Install dependencies
COPY ./requirements.txt .
RUN pip install --upgrade pip
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /usr/src/app/wheels -r requirements.txt


#########
# FINAL #
#########

# pull official base image
FROM python:3.8-alpine

# create directory for the app user
ENV APP_HOME=/home/app
WORKDIR $APP_HOME

# create the app user
RUN addgroup -S app && adduser -S app -G app

# install dependencies
RUN apk update && apk add libpq
COPY --from=builder /usr/src/app/wheels /wheels
COPY --from=builder /usr/src/app/requirements.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache /wheels/*
RUN rm -rf /wheels

# copy project
COPY . $APP_HOME

# chown all the files to the app user
RUN chown -R app:app $APP_HOME

# change to the app user
USER app

# run entrypoint.prod.sh
# ENTRYPOINT ["python", "/home/app/server.py"]
