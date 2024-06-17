#!/usr/bin/env sh

export FLASK_DEBUG=True
export FLASK_APP=application
flask init-db
#flask run --host 0.0.0.0 -p 5555
uwsgi --http 0.0.0.0:5555 --master -p 6 --uid 33 --gid 33 -w wsgi:app
