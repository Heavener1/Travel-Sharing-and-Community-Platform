#!/usr/bin/env sh
set -eu

ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$ROOT_DIR"

docker compose up --build -d

echo "Started with Docker Compose."
echo "Frontend: http://127.0.0.1:${FRONTEND_PORT:-5173}/"
echo "Backend API: http://127.0.0.1:${BACKEND_PORT:-8000}/api/"
echo "Elasticsearch: http://127.0.0.1:${ES_HTTP_PORT:-9200}/"
echo "Demo user: demo / demo123456"
echo "Admin user: admin / admin123456"
