#!/usr/bin/env sh
set -eu

if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
  python backend/manage.py migrate --noinput
fi

if [ "${RUN_SEED_DATA:-false}" = "true" ]; then
  python backend/manage.py seed_demo
fi

if [ "${ENSURE_ADMIN:-false}" = "true" ]; then
  python backend/manage.py ensure_admin \
    --username "${DJANGO_ADMIN_USERNAME:-admin}" \
    --password "${DJANGO_ADMIN_PASSWORD:-admin123456}" \
    --email "${DJANGO_ADMIN_EMAIL:-admin@example.com}"
fi

if [ "${RUN_INIT_EXTERNAL:-true}" = "true" ]; then
  python backend/manage.py init_external_services
fi

exec "$@"
