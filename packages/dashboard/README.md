# SentinelAPI dashboard

Dark operations console for the Phase 5 scanner service. It does **not** scan
on its own — it calls `http://127.0.0.1:8100`.

## Prerequisites

1. ShopAPI on **http://127.0.0.1:8000**
2. Scanner service on **http://127.0.0.1:8100**
   (`cd packages/scanner && .venv/bin/python -m sentinel_service`)

## Run

```bash
cd packages/dashboard
npm install
npm run dev
```

Open **http://localhost:5173** (or http://127.0.0.1:5173). The Vite dev server
proxies `/scans` and `/healthz` (including the progress WebSocket) to the
scanner on port 8100. CORS is also enabled on the service for the Vite origin
if you set `VITE_API_BASE=http://127.0.0.1:8100`.

If `GET /scans` is empty, use **New Scan** — findings are always live API data,
never hardcoded.
