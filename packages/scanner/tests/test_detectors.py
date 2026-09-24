"""Live ShopAPI detector tests — BOLA must fire; safe routes must not."""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from sentinel_core.detectors import BolaDetector, run_all_detectors
from sentinel_core.http_client import SafeClient
from sentinel_core.identity import IdentityProvider
from sentinel_core.spec_parser import SpecParser

SCANNER_ROOT = Path(__file__).resolve().parent.parent
FIXTURE = Path(__file__).resolve().parent / "fixtures" / "shopapi.openapi.json"
IDENTITIES = SCANNER_ROOT / "configs" / "shopapi.identities.yaml"
BASE = "http://127.0.0.1:8000"
SAFE_ENDPOINTS = {"GET /products", "GET /orders", "GET /healthz"}


def _shopapi_up() -> bool:
    try:
        response = httpx.get(f"{BASE}/healthz", timeout=2.0)
    except httpx.HTTPError:
        return False
    return response.status_code == 200


pytestmark = pytest.mark.skipif(not _shopapi_up(), reason="ShopAPI is not running on :8000")


def _endpoints():
    parser = SpecParser()
    if FIXTURE.is_file():
        return parser.load_from_file(FIXTURE)
    return parser.load_from_url(f"{BASE}/openapi.json")


def _identities() -> IdentityProvider:
    return IdentityProvider.from_file(IDENTITIES)


@pytest.mark.asyncio
async def test_bola_alice_reads_bob_order() -> None:
    """Alice GET /orders/201 (Bob's) must produce a BOLA finding."""
    async with SafeClient(allowed_base_urls=[BASE]) as client:
        findings = await BolaDetector().run(_endpoints(), _identities(), client)

    order_findings = [item for item in findings if item.endpoint == "GET /orders/{order_id}"]
    assert order_findings, "BolaDetector missed GET /orders/{order_id}"
    finding = order_findings[0]
    assert finding.vuln_class == "bola"
    assert finding.severity_score == 0.0
    assert finding.severity_label == ""
    assert "201" in finding.poc_curl
    assert "tok_alice" in finding.poc_curl
    bodies = " ".join(ev.response.body for ev in finding.evidence)
    assert "201" in bodies
    assert finding.access_matrix is not None
    assert finding.access_matrix["GET /orders/{order_id}"]["alice"] == "allowed"
    assert finding.access_matrix["GET /orders/{order_id}"]["anonymous"] == "denied"


@pytest.mark.asyncio
async def test_no_detector_flags_safe_endpoints() -> None:
    """GET /products, scoped GET /orders, and /healthz must stay clean."""
    async with SafeClient(allowed_base_urls=[BASE]) as client:
        findings = await run_all_detectors(_endpoints(), _identities(), client)

    flagged = {item.endpoint for item in findings}
    leaked = flagged & SAFE_ENDPOINTS
    assert not leaked, f"false positives on safe endpoints: {leaked}"


@pytest.mark.asyncio
async def test_seeded_flaws_are_caught() -> None:
    """Each ShopAPI seeded class must appear at least once."""
    async with SafeClient(allowed_base_urls=[BASE]) as client:
        findings = await run_all_detectors(_endpoints(), _identities(), client)

    by_class = {item.vuln_class: item for item in findings}
    assert "excessive_data_exposure" in by_class
    assert by_class["excessive_data_exposure"].endpoint == "GET /users/{user_id}"
    assert "broken_authentication" in by_class
    assert by_class["broken_authentication"].endpoint == "GET /admin/stats"
    assert "missing_rate_limit" in by_class
    assert by_class["missing_rate_limit"].endpoint == "POST /login"
    assert "mass_assignment" in by_class
    assert by_class["mass_assignment"].endpoint == "PATCH /users/{user_id}"
    assert any(item.endpoint == "GET /users/{user_id}" and item.vuln_class == "bola" for item in findings)
