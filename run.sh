#!/usr/bin/env bash
# Boot ShopAPI, the scanner service, and the dashboard console.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
API_DIR="$ROOT/packages/vulnerable-api"
SCAN_DIR="$ROOT/packages/scanner"
DASH_DIR="$ROOT/packages/dashboard"

if [[ ! -d "$API_DIR/.venv" ]]; then
  python3 -m venv "$API_DIR/.venv"
  "$API_DIR/.venv/bin/pip" install -r "$API_DIR/requirements.txt"
fi
if [[ ! -d "$SCAN_DIR/.venv" ]]; then
  python3 -m venv "$SCAN_DIR/.venv"
  "$SCAN_DIR/.venv/bin/pip" install -r "$SCAN_DIR/requirements.txt"
  "$SCAN_DIR/.venv/bin/pip" install -e "$SCAN_DIR"
fi
if [[ ! -d "$DASH_DIR/node_modules" ]]; then
  (cd "$DASH_DIR" && npm install)
fi

cleanup() {
  kill "${PIDS[@]:-}" 2>/dev/null || true
}
PIDS=()
trap cleanup EXIT INT TERM

echo "ShopAPI        http://127.0.0.1:8000"
(cd "$API_DIR" && .venv/bin/python -m app) &
PIDS+=($!)

echo "Scanner        http://127.0.0.1:8100"
(cd "$SCAN_DIR" && .venv/bin/python -m sentinel_service) &
PIDS+=($!)

echo "Dashboard      http://127.0.0.1:5173"
(cd "$DASH_DIR" && npm run dev) &
PIDS+=($!)

wait
