#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

API_URL="http://localhost:8000"

echo "Checking backend health..."
curl -fsS "$API_URL/api/health" || {
  echo "Backend is not running. Start it with:"
  echo "  python3 -m uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000"
  exit 1
}

echo "Fetching current board..."
curl -fsS "$API_URL/api/board?user=user" | python3 -m json.tool

echo ""
echo "Sending AI board update request..."
RESPONSE=$(curl -fsS -X POST "$API_URL/api/ai/board?user=user" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Rename the backlog to Launch Queue.",
    "history": [
      {"role": "user", "content": "hello"},
      {"role": "assistant", "content": "hi"}
    ]
  }')

echo "$RESPONSE" | python3 -m json.tool

echo ""
echo "Fetching board after AI update..."
curl -fsS "$API_URL/api/board?user=user" | python3 -m json.tool
