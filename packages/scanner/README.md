# SentinelAPI scanner

In-process core (`sentinel_core`), FastAPI service (`sentinel_service` on
**http://127.0.0.1:8100**), and CI/CD gate CLI (`sentinel`).

Reports persist to `packages/scanner/data/sentinel.db` (gitignored). The
CLI and the service share that file, so `./run.sh --seed` from the repo
root fills the dashboard on first load.

Identities preset: **`shopapi`** → `configs/shopapi.identities.yaml`
(alice / bob / admin / anonymous). ShopAPI must be on
`http://127.0.0.1:8000` (the only default allow-list entry).

## Install the CLI

```bash
cd packages/scanner
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

Or boot everything from the repo root: `./run.sh --seed`.

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

## Service

```bash
.venv/bin/python -m sentinel_service
```

CORS is open for `http://localhost:5173` and `http://127.0.0.1:5173`.
The dashboard proxies `/scans` to this origin in dev.

## Tests

```bash
.venv/bin/pytest
```

ShopAPI on :8000 is required for the live engine / detector tests.
