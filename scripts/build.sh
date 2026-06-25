#!/bin/bash
set -e

echo "=== Stopping and removing containers ==="
docker compose down --remove-orphans

echo "=== Removing legacy images ==="
docker compose images -q | xargs -r docker rmi -f 2>/dev/null || true

echo "=== Removing dangling images ==="
docker image prune -f

echo "=== Rebuilding and starting ==="
docker compose up --build -d

echo "=== Done ==="
docker ps -a
