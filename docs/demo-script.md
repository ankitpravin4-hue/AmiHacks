# Demo script — 3 minutes

Everything below runs on `127.0.0.1`. **Fallback if venue wifi dies:** the
stack is local and offline; ShopAPI, the scanner, and the dashboard do not
need the internet after `npm install` / venv setup.

**Prep (before you walk on stage)**

```bash
./run.sh --seed
```

Leave it running. Confirm:

| What | URL |
| --- | --- |
| ShopAPI Swagger | http://127.0.0.1:8000/docs |
| Scanner | http://127.0.0.1:8100/healthz |
| Dashboard | http://localhost:5173 |

---

### 0:00–0:25 — ShopAPI is a real, broken API

1. Open **http://127.0.0.1:8000/docs**.
2. `GET /users/{user_id}` → Try it out → `user_id=2` (Bob).
3. Authorize with `Bearer tok_alice` (or pass the header in curl):

```bash
curl -s http://127.0.0.1:8000/users/2 -H 'Authorization: Bearer tok_alice'
```

Alice's token returns Bob's `password_hash` and `internal_notes`. That is BOLA
plus excessive data — say it out loud. Do **not** linger.

### 0:25–1:05 — New Scan → live progress → Overview

1. Dashboard **New Scan** (`http://localhost:5173/new`).
2. Target stays `http://127.0.0.1:8000`. Identities stay **shopapi**.
3. **Start scan**. Call out the live percent + step.
4. When it completes you land on **Overview**:
   - Headline risk **8.6 / High**
   - Severity donut (5 High, 1 Medium)
   - Cards: **Account takeover** and **Cross-user data theft**

`--seed` already put a report in history if you need to skip the wait.

### 1:05–1:30 — Finding + Replay

1. **Findings** → row **BOLA · GET /orders/{order_id}** (id `bola-get-orders-order-id`).
2. Show redacted request evidence and the copyable `poc_curl`.
3. Hit **Replay attack**. Badge must read **STILL VULNERABLE** with
   `GET …/orders/201 → 200` (Alice reading Bob's order).

### 1:30–1:50 — Identity Access Matrix

**Access Matrix**. Rows = object endpoints, columns = alice / bob / admin /
anonymous. Red = leaked, green = denied. Anonymous is green; customers are
red on each other's objects. This is the BOLA proof.

### 1:50–2:15 — Attack chains

**Attack Chains**. Two graphs:

- Account takeover: mass-assign `is_admin` → open `/admin/stats`
- Cross-user data theft: BOLA on `/users/{user_id}` → excessive fields

Click a node if you have two seconds; otherwise read the narrative cards.

### 2:15–2:40 — CI gate + SARIF

In a second terminal (ShopAPI still up):

```bash
cd packages/scanner
.venv/bin/sentinel scan \
  --target http://127.0.0.1:8000 \
  --identities shopapi \
  --fail-on high \
  --format sarif \
  -o /tmp/sentinel.sarif
echo exit:$?
```

Exit **1**. `--fail-on high` fails the build. Point at
`docs/ci-example.yml` (upload SARIF to GitHub code scanning). A
`--fail-on critical` run exits 0 — ShopAPI has High, not Critical.

### 2:40–3:00 — Fix → re-scan → History / Diff

1. In `packages/vulnerable-api`, add an ownership check on
   `GET /orders/{order_id}` (the `# VULN:` BOLA). Restart is not needed if
   you edit and the process is the one `run.sh` started — restart ShopAPI
   only if the change did not load.
2. Dashboard **New Scan** → run again (or CLI with `--fail-on critical`).
3. **History / Diff**: Scan A = old, Scan B = new. The orders BOLA key
   `bola-get-orders-order-id` lands in **Fixed** (green). Persisting stays
   amber; new would be red.

If you cannot edit live, still open History / Diff on two seeded scans and
explain the same color language.

---

**Close in one sentence:** allow-listed only, explainable scores, one-click
replay, and a CI gate — no cloud, no API keys, no venue wifi.
