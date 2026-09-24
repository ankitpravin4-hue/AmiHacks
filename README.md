# SentinelAPI

Zero-Trust API vulnerability scanner. Ingests an OpenAPI spec, probes
authorization flaws first (BOLA/IDOR, broken auth, mass assignment, data
exposure), and produces severity-ranked findings with a reproducible PoC.

This repo is built **phase by phase**. Phase 1 is the intentionally
vulnerable demo target. Later phases add the scanner core, detectors,
dashboard, and CI gate.

## Phase 1 — Vulnerable demo API

A local e-commerce/SaaS API used as the **only** allow-listed scan target.
It is seeded with known flaws so detectors can be graded against ground truth.

```bash
cd packages/vulnerable-api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m app
```

- API: http://127.0.0.1:8000
- Health: http://127.0.0.1:8000/healthz
- OpenAPI: http://127.0.0.1:8000/openapi.json

Demo credentials and the seeded vulnerability list live in
[`packages/vulnerable-api/README.md`](packages/vulnerable-api/README.md)
(for humans/judges — not shipped into the scanner).

## Ethics

The scanner will only test hosts on an explicit allow-list. Never point it
at a real production system.
