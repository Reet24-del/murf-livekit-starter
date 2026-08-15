#!/usr/bin/env bash

set -u

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$PROJECT_DIR/backend"
FRONTEND_DIR="$PROJECT_DIR/frontend"
BACKEND_PYTHON="$BACKEND_DIR/.venv/bin/python"
NEXT_BIN="$FRONTEND_DIR/node_modules/.bin/next"
FRONTEND_PORT="${KISAN_FRONTEND_PORT:-3001}"
AGENT_NAME="${KISAN_AGENT_NAME:-kisan-sahayak-primary}"
LOG_DIR="${KISAN_LOG_DIR:-/private/tmp}"
BACKEND_LOG="$LOG_DIR/kisan-sahayak-backend.log"
FRONTEND_LOG="$LOG_DIR/kisan-sahayak-frontend.log"

if [[ ! -x "$BACKEND_PYTHON" ]]; then
  echo "Backend environment is missing: $BACKEND_PYTHON"
  exit 1
fi

if [[ ! -x "$NEXT_BIN" ]]; then
  echo "Frontend dependencies are missing: $NEXT_BIN"
  exit 1
fi

if lsof -nP -iTCP:"$FRONTEND_PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "Frontend port $FRONTEND_PORT is already in use."
  echo "Set KISAN_FRONTEND_PORT to a free port or stop the existing process."
  exit 1
fi

echo "Starting Kisan Sahayak from $PROJECT_DIR"
echo "Frontend: http://localhost:$FRONTEND_PORT"
echo "Backend log: $BACKEND_LOG"
echo "Frontend log: $FRONTEND_LOG"

(
  cd "$BACKEND_DIR"
  KISAN_AGENT_NAME="$AGENT_NAME" exec "$BACKEND_PYTHON" src/agent.py dev
) >"$BACKEND_LOG" 2>&1 &
BACKEND_PID=$!

(
  cd "$FRONTEND_DIR"
  AGENT_NAME="$AGENT_NAME" exec "$NEXT_BIN" dev --hostname 0.0.0.0 --port "$FRONTEND_PORT"
) >"$FRONTEND_LOG" 2>&1 &
FRONTEND_PID=$!

cleanup() {
  kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
}

trap cleanup EXIT INT TERM
wait "$BACKEND_PID" "$FRONTEND_PID"
