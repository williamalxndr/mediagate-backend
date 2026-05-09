#!/bin/sh
set -e

if [ -n "$DATABASE_URL" ]; then
    python - <<'PY'
import os
import sys
import time

import psycopg

dsn = os.environ["DATABASE_URL"]
deadline = time.monotonic() + int(os.environ.get("DB_WAIT_TIMEOUT", "60"))
last_error = None

while time.monotonic() < deadline:
    try:
        with psycopg.connect(dsn, connect_timeout=5):
            break
    except psycopg.OperationalError as exc:
        last_error = exc
        time.sleep(2)
else:
    print("Database did not become ready before startup timeout.", file=sys.stderr)
    if last_error is not None:
        print(last_error, file=sys.stderr)
    sys.exit(1)
PY
fi

python manage.py migrate --noinput
python manage.py collectstatic --noinput

exec gunicorn config.wsgi:application \
    --bind "0.0.0.0:${PORT:-8000}" \
    --workers "${GUNICORN_WORKERS:-3}" \
    --timeout "${GUNICORN_TIMEOUT:-60}" \
    --access-logfile - \
    --error-logfile -
