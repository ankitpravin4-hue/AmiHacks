# SentinelAPI dashboard

Dark operations console for the scanner service. It does **not** scan on
its own — it calls **http://127.0.0.1:8100**.

## Prerequisites

From the repo root the one-command path is:

```bash
./run.sh --seed
```

That boots ShopAPI **:8000**, the scanner **:8100**, and this app **:5173**,
then runs one CLI scan (`--identities shopapi`) so Overview is not empty.

To run the console alone:

1. ShopAPI on **http://127.0.0.1:8000**
2. Scanner service on **http://127.0.0.1:8100**
   (`cd packages/scanner && .venv/bin/python -m sentinel_service`)

```bash
cd packages/dashboard
npm install
npm run dev
```

Open **http://localhost:5173** (or http://127.0.0.1:5173). The Vite dev
server proxies `/scans` and `/healthz` (including the progress WebSocket)
to the scanner on port 8100. CORS is also enabled on the service for the
Vite origin if you set `VITE_API_BASE=http://127.0.0.1:8100`.

New Scan defaults: target `http://127.0.0.1:8000`, identities preset
**`shopapi`**. If `GET /scans` is empty, use New Scan — findings are
always live API data, never hardcoded.
