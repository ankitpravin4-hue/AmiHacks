#!/usr/bin/env bash
# Boot ShopAPI (:8000), the scanner service (:8100), and the dashboard (:5173).
# Usage: ./run.sh [--seed]
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
API_DIR="$ROOT/packages/vulnerable-api"
SCAN_DIR="$ROOT/packages/scanner"
DASH_DIR="$ROOT/packages/dashboard"
LOGDIR="$ROOT/.run"
SEED=0

for arg in "$@"; do
  case "$arg" in
    --seed) SEED=1 ;;
    -h|--help)
      echo "Usage: ./run.sh [--seed]"
      echo "  --seed   Run one CLI scan against ShopAPI so the dashboard has data."
      exit 0
      ;;
    *)
      echo "Unknown flag: $arg" >&2
      echo "Usage: ./run.sh [--seed]" >&2
      exit 2
      ;;
  esac
done

mkdir -p "$LOGDIR"
: >"$LOGDIR/shopapi.log"
: >"$LOGDIR/scanner.log"
: >"$LOGDIR/dashboard.log"

kill_port() {
  local port="$1"
  local pids
  pids="$(lsof -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null || true)"
  if [[ -n "${pids}" ]]; then
    echo "Freeing :$port (pids ${pids//$'\n'/ })"
    # shellcheck disable=SC2086
    kill ${pids} 2>/dev/null || true
    sleep 0.3
    pids="$(lsof -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null || true)"
    if [[ -n "${pids}" ]]; then
      # shellcheck disable=SC2086
      kill -9 ${pids} 2>/dev/null || true
    fi
  fi
}

wait_http() {
  local url="$1" name="$2" tries="${3:-60}"
  local i
  for i in $(seq 1 "$tries"); do
    if curl -sf "$url" >/dev/null 2>&1; then
      echo "  $name ready ($url)"
      return 0
    fi
    sleep 0.25
  done
  echo "ERROR: $name did not become ready at $url" >&2
  return 1
}

PIDS=()
cleanup() {
  trap - EXIT INT TERM
  echo ""
  echo "Stopping ShopAPI, scanner, and dashboard…"
  if [[ ${#PIDS[@]} -gt 0 ]]; then
    kill "${PIDS[@]}" 2>/dev/null || true
    sleep 0.4
    kill -9 "${PIDS[@]}" 2>/dev/null || true
  fi
  kill_port 8000
  kill_port 8100
  kill_port 5173
}
trap cleanup EXIT INT TERM

echo "Preparing environments…"
if [[ ! -d "$API_DIR/.venv" ]]; then
  python3 -m venv "$API_DIR/.venv"
  "$API_DIR/.venv/bin/pip" install -r "$API_DIR/requirements.txt"
fi
if [[ ! -d "$SCAN_DIR/.venv" ]]; then
  python3 -m venv "$SCAN_DIR/.venv"
  "$SCAN_DIR/.venv/bin/pip" install -r "$SCAN_DIR/requirements.txt"
  "$SCAN_DIR/.venv/bin/pip" install -e "$SCAN_DIR"
fi
if [[ ! -x "$SCAN_DIR/.venv/bin/sentinel" ]]; then
  "$SCAN_DIR/.venv/bin/pip" install -e "$SCAN_DIR"
fi
if [[ ! -d "$DASH_DIR/node_modules" ]]; then
  (cd "$DASH_DIR" && npm install)
fi

echo "Clearing stale listeners…"
kill_port 8000
kill_port 8100
kill_port 5173

echo ""
echo "  ShopAPI     http://127.0.0.1:8000   (Swagger /docs)"
echo "  Scanner     http://127.0.0.1:8100   (REST + WebSocket)"
echo "  Dashboard   http://localhost:5173"
echo ""

(cd "$API_DIR" && .venv/bin/python -m app >>"$LOGDIR/shopapi.log" 2>&1) &
PIDS+=($!)
wait_http "http://127.0.0.1:8000/healthz" "ShopAPI"

if [[ "$SEED" -eq 1 ]]; then
  echo "Seeding one ShopAPI scan via the CLI (identities preset: shopapi)…"
  (
    cd "$SCAN_DIR"
    .venv/bin/sentinel scan \
      --target http://127.0.0.1:8000 \
      --identities shopapi \
      --fail-on critical \
      --format table
  ) | tee -a "$LOGDIR/seed.log"
  echo "Seed scan stored in packages/scanner/data/sentinel.db"
fi

(cd "$SCAN_DIR" && .venv/bin/python -m sentinel_service >>"$LOGDIR/scanner.log" 2>&1) &
PIDS+=($!)
wait_http "http://127.0.0.1:8100/healthz" "Scanner"

(cd "$DASH_DIR" && npm run dev >>"$LOGDIR/dashboard.log" 2>&1) &
PIDS+=($!)
wait_http "http://127.0.0.1:5173/" "Dashboard"

echo ""
echo "All three are up. Ctrl+C stops them together."
echo "Streaming logs from $LOGDIR …"
echo ""
tail -n +1 -F "$LOGDIR/shopapi.log" "$LOGDIR/scanner.log" "$LOGDIR/dashboard.log"
