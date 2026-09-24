# BankAPI — second intentionally vulnerable demo target

Local-only banking API used to prove SentinelAPI is not hardcoded to ShopAPI
(`http://127.0.0.1:8010`). **Do not expose this service to the internet.**

## Run

From the repo root (preferred):

```bash
./run.sh
```

Or this package alone:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m app
```

Defaults: `127.0.0.1:8010`.

| URL | Purpose |
| --- | --- |
| http://127.0.0.1:8010/healthz | Liveness |
| http://127.0.0.1:8010/openapi.json | Auto-generated OpenAPI 3 spec |
| http://127.0.0.1:8010/docs | Swagger UI |

## Seeded identities (`bankapi` preset)

| Email | Password | Role | Bearer token | Owns |
| --- | --- | --- | --- | --- |
| alice@bank.test | alice123 | customer | `tok_bank_alice` | account `101`, txns `1001`/`1002` |
| bob@bank.test | bob123 | customer | `tok_bank_bob` | account `201`, txns `2001`/`2002` |
| admin@bank.test | admin123 | admin | `tok_bank_admin` | account `301` |

## Seeded vulnerabilities (`# VULN:`)

1. **`POST /login`** — no rate limiting.
2. **`GET /accounts/{id}`** — BOLA + excessive data (`balance_secret`, `kyc_notes`, `is_frozen`).
3. **`GET /transactions/search?q=`** — SQL injection (SELECT-only).
4. **`GET /admin/audit`** — broken authentication (no token).

No mass assignment — that mix stays on ShopAPI.

## Intentionally safe endpoints

- **`GET /accounts`** — scoped to the caller.
- **`GET /transactions`** and **`GET /transactions/{id}`** — scoped to owned accounts.
- **`POST /transfers`** — source account must belong to the caller.
- **`GET /rates`** — public FX quotes.
- **`GET /healthz`** — liveness only.
