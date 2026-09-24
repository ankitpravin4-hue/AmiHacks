#!/usr/bin/env bash
# Phase 1: boot the vulnerable demo API only.
# Later phases will also start the scanner service and dashboard.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
API_DIR="$ROOT/packages/vulnerable-api"

cd "$API_DIR"
if [[ ! -d .venv ]]; then
  python3 -m venv .venv
  .venv/bin/pip install -r requirements.txt
fi

echo "ShopAPI listening on http://127.0.0.1:8000"
exec .venv/bin/python -m app
