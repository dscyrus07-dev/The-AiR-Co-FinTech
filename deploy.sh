#!/bin/bash
set -e

echo "========================================"
echo "  Airco Insights — Utho Deploy Script"
echo "========================================"

APP_DIR="/opt/airco-insights"
COMPOSE_FILE="docker-compose.prod.yml"

# 1. Ensure app directory exists
mkdir -p "$APP_DIR"
cd "$APP_DIR"

# 2. Pull latest images from Docker Hub
echo "[1/4] Pulling latest Docker images..."
docker pull theairco/fintech-backend:latest
docker pull theairco/fintech-frontend:latest

# 3. Stop and remove old containers (if running)
echo "[2/4] Stopping existing containers..."
docker compose -f "$COMPOSE_FILE" down --remove-orphans 2>/dev/null || true

# 4. Start services
echo "[3/4] Starting services..."
docker compose -f "$COMPOSE_FILE" up -d

# 5. Health check
echo "[4/4] Waiting for backend health check..."
sleep 10
STATUS=$(docker inspect --format='{{.State.Health.Status}}' fintech_backend 2>/dev/null || echo "unknown")
echo "Backend health: $STATUS"

echo ""
echo "========================================"
echo "  Deploy complete!"
echo "  URL: https://test.theairco.ai"
echo "========================================"

docker compose -f "$COMPOSE_FILE" ps
