"""Full engine run: 7 findings, expected severity bands, chains, SQLite round-trip."""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from sentinel_core.engine import ScanEngine
from sentinel_core.models import ScanConfig
from sentinel_core.storage import get_finding, get_report

SCANNER_ROOT = Path(__file__).resolve().parent.parent
IDENTITIES = SCANNER_ROOT / "configs" / "shopapi.identities.yaml"
BASE = "http://127.0.0.1:8000"
HIGH_OR_CRITICAL = {"High", "Critical"}
HIGH_CLASSES = {
    "bola",
    "broken_authentication",
    "mass_assignment",
    "excessive_data_exposure",
    "sql_injection",
}


def _shopapi_up() -> bool:
    try:
        response = httpx.get(f"{BASE}/healthz", timeout=2.0)
    except httpx.HTTPError:
        return False
    return response.status_code == 200


pytestmark = pytest.mark.skipif(not _shopapi_up(), reason="ShopAPI is not running on :8000")


@pytest.mark.asyncio
async def test_engine_scores_chains_and_round_trips(tmp_path: Path) -> None:
    """Live ShopAPI scan must score 7 findings, build both chains, and persist."""
    engine = ScanEngine(db_path=tmp_path / "sentinel.db")
    progress: list[tuple[int, str]] = []
    report = await engine.run(
        ScanConfig(
            target=BASE,
            spec_url=f"{BASE}/openapi.json",
            allowlist=[BASE],
            identities_file=str(IDENTITIES),
            safe_mode=True,
        ),
        on_progress=lambda percent, step: progress.append((percent, step)),
    )

    assert report.id is not None
    assert len(report.findings) == 7
    assert progress and progress[-1][0] == 100

    endpoints = {item.endpoint for item in report.findings}
    assert "GET /users/{user_id}" in endpoints
    assert "GET /orders/{order_id}" in endpoints
    assert "GET /admin/stats" in endpoints
    assert "POST /login" in endpoints
    assert "PATCH /users/{user_id}" in endpoints
    assert "GET /products/search" in endpoints

    for finding in report.findings:
        assert finding.severity_breakdown is not None
        assert finding.severity_label == finding.severity_breakdown.label
        assert 0 <= finding.confidence <= 1
        if finding.vuln_class in HIGH_CLASSES:
            assert finding.severity_label in HIGH_OR_CRITICAL, (
                f"{finding.vuln_class} {finding.endpoint} scored "
                f"{finding.severity_label} {finding.severity_score}"
            )
        if finding.vuln_class == "missing_rate_limit":
            assert finding.severity_label == "Medium"

    chain_ids = {chain.id for chain in report.chains}
    assert chain_ids == {"account-takeover", "cross-user-data-theft"}
    takeover = next(chain for chain in report.chains if chain.id == "account-takeover")
    theft = next(chain for chain in report.chains if chain.id == "cross-user-data-theft")
    assert "promotes themselves to admin" in takeover.narrative
    assert "full record including secrets" in theft.narrative

    chained = {item.chain_id for item in report.findings if item.chain_id}
    assert chained == chain_ids
    standalone = [item for item in report.findings if item.chain_id is None]
    standalone_keys = {(item.vuln_class, item.endpoint) for item in standalone}
    assert ("bola", "GET /orders/{order_id}") in standalone_keys
    assert ("missing_rate_limit", "POST /login") in standalone_keys
    assert ("sql_injection", "GET /products/search") in standalone_keys

    loaded = get_report(report.id)
    assert loaded is not None
    assert {item.id for item in loaded.findings} == {item.id for item in report.findings}
    assert {chain.id for chain in loaded.chains} == chain_ids
    assert {item.severity_label for item in loaded.findings} == {
        item.severity_label for item in report.findings
    }
    sample = report.findings[0]
    fetched = get_finding(report.id, sample.id)
    assert fetched is not None
    assert fetched.id == sample.id
    assert fetched.severity_score == sample.severity_score
    assert fetched.chain_id == sample.chain_id
