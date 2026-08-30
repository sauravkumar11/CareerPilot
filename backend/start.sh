#!/bin/sh
# Runs on every container start for the web service. Applies any pending
# Alembic migrations before starting the API server.
#
# This exists specifically because Render's free tier has no Shell/exec
# access to run migrations manually after deploy — the standard advice of
# "just run alembic upgrade head from the dashboard" isn't available there.
# Running migrations as part of container startup is also just good
# practice generally (Heroku release phase, Railway pre-deploy commands,
# etc. all do the same thing) so this isn't a Render-specific hack.
#
# set -e: any failing command aborts the script with a non-zero exit code,
# so a broken migration shows up as a failed Render deploy (loud, visible)
# rather than a container that starts "successfully" and then 500s on
# every database-touching request (quiet, confusing).
#
# Only ever invoked via the Dockerfile's default CMD. docker-compose.yml's
# celery_worker/celery_beat services override the command entirely (their
# own `command:` replaces CMD, doesn't run this script), so migrations
# only ever run from exactly one place per docker-compose/Render stack —
# no risk of two services racing to apply migrations concurrently.
set -e

echo "Running database migrations..."
python -m alembic upgrade head

echo "Starting server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
