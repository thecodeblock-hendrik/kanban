#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

IMAGE_NAME="pm-app"
CONTAINER_NAME="pm-app"

if docker ps -a --format '{{.Names}}' | grep -Fxq "$CONTAINER_NAME"; then
  echo "Stopping existing container..."
  docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true
fi

EXTRA_ARGS=()
if [[ -f "$ROOT_DIR/.env" ]]; then
  EXTRA_ARGS+=(--env-file "$ROOT_DIR/.env")
fi

mkdir -p "$ROOT_DIR/data"

docker build -t "$IMAGE_NAME" .
docker run --rm -d --name "$CONTAINER_NAME" -p 8000:8000 -v "$ROOT_DIR/data:/app/data" "${EXTRA_ARGS[@]}" "$IMAGE_NAME"

echo "Application started at http://localhost:8000"
