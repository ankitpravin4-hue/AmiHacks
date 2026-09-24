"""Live BankAPI scan — distinct fingerprint from ShopAPI; same detectors."""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from sentinel_core.detectors import run_all_detectors
from sentinel_core.http_client import SafeClient
from sentinel_core.identity import IdentityProvider
from sentinel_core.spec_parser import SpecParser

SCANNER_ROOT = Path(__file__).resolve().parent.parent
IDENTITIES = SCANNER_ROOT / "configs" / "bankapi.identities.yaml"
BASE = "http://127.0.0.1:8010"
SAFE_ENDPOINTS = {
    "GET /rates",
    "GET /accounts",
    "GET /transactions",
    "GET /transactions/{transaction_id}",
    "GET /healthz",
    "POST /transfers",
}


def _bankapi_up() -> bool:
    try:
        response = httpx.get(f"{BASE}/healthz", timeout=2.0)
    except httpx.HTTPError:
        return False
    return response.status_code == 200 and "bankapi" in response.text


pytestmark = pytest.mark.skipif(not _bankapi_up(), reason="BankAPI is not running on :8010")


@pytest.mark.asyncio
async def test_bankapi_distinct_findings_and_safe_routes() -> None:
    """BankAPI flags audit/SQLi/account leaks/login; safe routes stay clean."""
    endpoints = SpecParser().load_from_url(f"{BASE}/openapi.json", allowed_base_urls=[BASE])
    identities = IdentityProvider.from_file(IDENTITIES)
    async with SafeClient(allowed_base_urls=[BASE]) as client:
        findings = await run_all_detectors(endpoints, identities, client)

    by_class = {item.vuln_class: item for item in findings}
    flagged = {item.endpoint for item in findings}

    assert by_class["broken_authentication"].endpoint == "GET /admin/audit"
    assert by_class["sql_injection"].endpoint == "GET /transactions/search"
    assert by_class["missing_rate_limit"].endpoint == "POST /login"
    assert "mass_assignment" not in by_class

    account_findings = [item for item in findings if item.endpoint == "GET /accounts/{account_id}"]
    classes = {item.vuln_class for item in account_findings}
    assert "bola" in classes
    assert "excessive_data_exposure" in classes
    assert sum(1 for item in findings if item.vuln_class == "bola") == 1

    leaked = flagged & SAFE_ENDPOINTS
    assert not leaked, f"false positives on safe endpoints: {leaked}"
