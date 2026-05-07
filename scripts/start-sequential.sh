#!/usr/bin/env sh
set -eu

ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
NETWORK_NAME="${NETWORK_NAME:-travel-sharing-net}"
ES_HTTP_PORT="${ES_HTTP_PORT:-9200}"
ES_TRANSPORT_PORT="${ES_TRANSPORT_PORT:-9300}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"
BACKEND_PORT="${BACKEND_PORT:-8000}"

cd "$ROOT_DIR"

echo "Building Docker images..."
docker build -f docker/elasticsearch/Dockerfile -t travel-sharing-elasticsearch:8.17.2 .
docker build -f backend/Dockerfile -t travel-sharing-backend:latest .
docker build -f frontend/Dockerfile --build-arg VITE_API_BASE_URL=/api -t travel-sharing-frontend:latest .

echo "Preparing Docker network and containers..."
docker network inspect "$NETWORK_NAME" >/dev/null 2>&1 || docker network create "$NETWORK_NAME" >/dev/null
docker rm -f travel-sharing-frontend travel-sharing-backend travel-sharing-elasticsearch >/dev/null 2>&1 || true

echo "Starting Elasticsearch..."
docker run -d \
  --name travel-sharing-elasticsearch \
  --network "$NETWORK_NAME" \
  -p "${ES_HTTP_PORT}:9200" \
  -p "${ES_TRANSPORT_PORT}:9300" \
  -e discovery.type=single-node \
  -e xpack.security.enabled=false \
  -e xpack.security.enrollment.enabled=false \
  -e ES_JAVA_OPTS="-Xms512m -Xmx512m" \
  travel-sharing-elasticsearch:8.17.2 >/dev/null

printf "Waiting for Elasticsearch"
for _ in $(seq 1 60); do
  if docker exec travel-sharing-elasticsearch curl -fsS http://127.0.0.1:9200 >/dev/null 2>&1; then
    echo " ready."
    break
  fi
  printf "."
  sleep 2
done

echo "Starting frontend..."
docker run -d \
  --name travel-sharing-frontend \
  --network "$NETWORK_NAME" \
  -p "${FRONTEND_PORT}:80" \
  travel-sharing-frontend:latest >/dev/null

echo "Starting backend..."
docker run -d \
  --name travel-sharing-backend \
  --network "$NETWORK_NAME" \
  --env-file backend/.env \
  -e DJANGO_DB_ENGINE=mysql \
  -e DJANGO_DB_NAME=travel_sharing_platform \
  -e DJANGO_ALLOWED_HOSTS="127.0.0.1,localhost,backend,0.0.0.0" \
  -e DJANGO_CORS_ALLOW_ALL_ORIGINS=True \
  -e ELASTICSEARCH_URL=http://travel-sharing-elasticsearch:9200 \
  -e RUN_MIGRATIONS=true \
  -e RUN_INIT_EXTERNAL=true \
  -e RUN_SEED_DATA=false \
  -e ENSURE_ADMIN=true \
  -e DJANGO_ADMIN_USERNAME=admin \
  -e DJANGO_ADMIN_PASSWORD=admin123456 \
  -e DJANGO_ADMIN_EMAIL=admin@example.com \
  -p "${BACKEND_PORT}:8000" \
  travel-sharing-backend:latest >/dev/null

echo "Started."
echo "Frontend: http://127.0.0.1:${FRONTEND_PORT}/"
echo "Backend API: http://127.0.0.1:${BACKEND_PORT}/api/"
echo "Elasticsearch: http://127.0.0.1:${ES_HTTP_PORT}/"
echo "Demo user: demo / demo123456"
echo "Admin user: admin / admin123456"
