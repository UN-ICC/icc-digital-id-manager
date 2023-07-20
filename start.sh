#!/bin/bash

if [ "$DEBUG" == "True" ]; then
    sleep 15
fi
python3 manage.py migrate
python3 manage.py collectstatic --no-input

if [ "$DEBUG" == "True" ]; then
    python manage.py runserver 0.0.0.0:8082
else
   mod_wsgi-express start-server id_manager/wsgi.py \
  --port 8082 \
  --limit-request-body 4294967296 \
  --log-level info \
  --access-log \
  --log-to-terminal \
  --locale C.UTF-8
fi
