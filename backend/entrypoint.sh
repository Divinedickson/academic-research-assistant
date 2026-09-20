#!/bin/sh
set -eu

python manage.py migrate --noinput
python manage.py check_pgvector

exec gunicorn config.wsgi:application \
    --bind "0.0.0.0:${PORT:-10000}" \
    --workers 1 \
    --threads 1 \
    --timeout "${GUNICORN_TIMEOUT:-180}" \
    --graceful-timeout "${GUNICORN_GRACEFUL_TIMEOUT:-30}" \
    --access-logfile - \
    --error-logfile -
