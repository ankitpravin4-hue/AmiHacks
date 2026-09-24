"""Spec-only and parse-error paths — no live ShopAPI required."""

from __future__ import annotations

from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from sentinel_core.engine import ScanEngine
from sentinel_core.models import ScanConfig
from sentinel_core.spec_parser import SpecParser
from sentinel_core.spec_static import LIVE_ONLY_CHECKS, findings_from_spec
from sentinel_service.app import create_app

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "shopapi.openapi.json"


@pytest.mark.asyncio
async def test_engine_spec_only_is_static_and_honest(tmp_path: Path) -> None:
    """Pasted ShopAPI spec must not invent BOLA or other live findings."""
    engine = ScanEngine(db_path=tmp_path / "spec-only.db")
    report = await engine.run(ScanConfig(spec_text=FIXTURE.read_text(encoding="utf-8")))
    assert report.target == "spec-only"
    assert report.status == "completed"
    classes = {item.vuln_class for item in report.findings}
    assert "bola" not in classes
    assert "mass_assignment" not in classes
    assert "missing_rate_limit" not in classes
    assert "excessive_data_exposure" in classes
    assert "missing_security" in classes
    assert any(item.endpoint == "GET /users/{user_id}" for item in report.findings)
    assert any(item.endpoint == "GET /admin/stats" for item in report.findings)
    skipped = {item.check for item in report.skipped_checks}
    assert skipped == {item.check for item in LIVE_ONLY_CHECKS}
    for finding in report.findings:
        assert "no live request was sent" in finding.poc_curl.lower()


def test_static_findings_from_shopapi_fixture() -> None:
    endpoints = SpecParser().load_from_file(FIXTURE)
    findings = findings_from_spec(endpoints)
    by_endpoint = {item.endpoint: item for item in findings}
    users = by_endpoint["GET /users/{user_id}"]
    assert users.vuln_class == "excessive_data_exposure"
    assert "password_hash" in users.business_impact
    admin = by_endpoint["GET /admin/stats"]
    assert admin.vuln_class == "missing_security"


@pytest.mark.asyncio
async def test_service_spec_text_and_parse_error(tmp_path: Path) -> None:
    app = create_app(db_path=tmp_path / "spec-service.db", allowlist=["http://127.0.0.1:8000"])
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        missing = await client.post("/scans", json={"identities_preset": "shopapi"})
        assert missing.status_code == 400
        assert "spec" in missing.json()["detail"].lower()

        bad = await client.post(
            "/scans",
            json={"spec_text": "[]", "identities_preset": "shopapi"},
        )
        assert bad.status_code == 400
        assert "parse" in bad.json()["detail"].lower()

        created = await client.post(
            "/scans",
            json={"spec_text": FIXTURE.read_text(encoding="utf-8"), "identities_preset": "shopapi"},
        )
        assert created.status_code == 200
        scan_id = created.json()["scan_id"]
        report = await _wait_for_completion(client, scan_id)
        assert report["status"] == "completed"
        assert report["target"] == "spec-only"
        classes = {item["vuln_class"] for item in report["findings"]}
        assert "bola" not in classes
        assert report["skipped_checks"]
        assert any(item["check"] == "BOLA/IDOR" for item in report["skipped_checks"])


@pytest.mark.asyncio
async def test_service_spec_file_upload(tmp_path: Path) -> None:
    app = create_app(db_path=tmp_path / "spec-upload.db", allowlist=["http://127.0.0.1:8000"])
    transport = ASGITransport(app=app)
    spec = FIXTURE.read_bytes()
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        created = await client.post(
            "/scans",
            files={"spec_file": ("shopapi.openapi.json", spec, "application/json")},
            data={"identities_preset": "shopapi"},
        )
        assert created.status_code == 200
        report = await _wait_for_completion(client, created.json()["scan_id"])
        assert report["status"] == "completed"
        assert "bola" not in {item["vuln_class"] for item in report["findings"]}


async def _wait_for_completion(client: AsyncClient, scan_id: int, timeout: float = 20.0) -> dict:
    import asyncio

    deadline = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < deadline:
        response = await client.get(f"/scans/{scan_id}")
        assert response.status_code == 200
        body = response.json()
        if body["status"] in {"completed", "failed"}:
            return body
        await asyncio.sleep(0.05)
    raise AssertionError(f"scan {scan_id} did not finish")
