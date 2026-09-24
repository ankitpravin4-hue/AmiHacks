# SentinelAPI scanner

In-process core (`sentinel_core`), FastAPI service (`sentinel_service` on :8100),
and CI/CD gate CLI (`sentinel`).

## Install the CLI

```bash
cd packages/scanner
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

ShopAPI must already be running on `http://127.0.0.1:8000` (allow-listed).

## Three commands

**Passing run** — ShopAPI has High findings but no Critical, so the gate stays green:

```bash
sentinel scan --target http://127.0.0.1:8000 --identities shopapi --fail-on critical --format table
```

**Failing gate** — five High findings trip `--fail-on high` (exit 1):

```bash
sentinel scan --target http://127.0.0.1:8000 --identities shopapi --fail-on high --format table
```

**SARIF export** — GitHub code scanning ingest (`docs/ci-example.yml`):

```bash
sentinel scan --target http://127.0.0.1:8000 --identities shopapi --fail-on high --format sarif -o results.sarif
```

Non-allow-listed targets exit 2 without sending a request.
