# ShopAPI — intentionally vulnerable demo target

Local-only e-commerce API used as SentinelAPI's allow-listed scan target.
**Do not expose this service to the internet. Do not point the scanner at
any host that is not this demo.**

## Run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m app
```

Defaults: `127.0.0.1:8000`. Override with `HOST` / `PORT` / `DATABASE_URL`.

| URL | Purpose |
| --- | --- |
| http://127.0.0.1:8000/healthz | Liveness |
| http://127.0.0.1:8000/openapi.json | Auto-generated OpenAPI 3 spec (scanner input) |
| http://127.0.0.1:8000/docs | Swagger UI |

Re-seed from scratch:

```bash
rm -f data/shop.db
python seed.py
```

## Seeded identities

| Email | Password | Role | Bearer token |
| --- | --- | --- | --- |
| alice@shop.test | alice123 | customer | `tok_alice` |
| bob@shop.test | bob123 | customer | `tok_bob` |
| admin@shop.test | admin123 | admin | `tok_admin` |

Tokens are **predictable on purpose** (stored in a simple token→user map).

Owned objects after seed:

- Alice owns orders `101`, `102`
- Bob owns orders `201`, `202`

## Seeded vulnerabilities (demo / judges only)

These comments also appear in source as `# VULN:`.

1. **`POST /login`** — no rate limiting (brute-forceable).
2. **`GET /users/{id}`** — BOLA: any authenticated user can read any other user.
3. **`GET /users/{id}`** — excessive data exposure: `password_hash`, `internal_notes`, `is_admin`.
4. **`PATCH /users/{id}`** — mass assignment: body may set `is_admin`.
5. **`GET /orders/{id}`** — BOLA: no ownership check.
6. **`GET /admin/stats`** — broken authentication: no auth required.
7. **Tokens** — issued as guessable static strings (`tok_alice`, `tok_bob`).

## Intentionally safe endpoints

The scanner must distinguish these from the flawed ones:

- **`GET /orders`** — correctly scoped to the authenticated caller.
- **`GET /products`** — public catalog, no sensitive fields.
- **`GET /healthz`** — liveness only.
