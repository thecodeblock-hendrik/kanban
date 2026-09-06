#!/usr/bin/env bash
set -euo pipefail

CONTAINER_NAME="pm-app"

if docker ps -a --format '{{.Names}}' | grep -Fxq "$CONTAINER_NAME"; then
  docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true
  echo "Stopped container: $CONTAINER_NAME"
else
  echo "Container not running: $CONTAINER_NAME"
fi
