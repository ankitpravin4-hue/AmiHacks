"""In-process scanner service tests against live ShopAPI."""

from __future__ import annotations

import asyncio
from pathlib import Path

import httpx
import pytest
from httpx import ASGITransport, AsyncClient

from sentinel_service.app import create_app

BASE = "http://127.0.0.1:8000"


def _shopapi_up() -> bool:
    try:
        response = httpx.get(f"{BASE}/healthz", timeout=2.0)
    except httpx.HTTPError:
        return False
    return response.status_code == 200


pytestmark = pytest.mark.skipif(not _shopapi_up(), reason="ShopAPI is not running on :8000")


@pytest.mark.asyncio
async def test_service_scan_report_replay_and_allowlist(tmp_path: Path) -> None:
    """POST starts a scan, report has 7 findings, BOLA replay still works, foreign hosts 400."""
    app = create_app(db_path=tmp_path / "service.db", allowlist=[BASE])
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        denied = await client.post(
            "/scans",
            json={"target_base_url": "https://example.com", "identities_preset": "shopapi"},
        )
        assert denied.status_code == 400
        assert "allow-list" in denied.json()["detail"]

        created = await client.post(
            "/scans",
            json={
                "target_base_url": BASE,
                "spec_url": f"{BASE}/openapi.json",
                "identities_preset": "shopapi",
            },
        )
        assert created.status_code == 200
        body = created.json()
        assert body["status"] == "running"
        scan_id = body["scan_id"]
        assert isinstance(scan_id, int)

        report = await _wait_for_completion(client, scan_id)
        assert report["status"] == "completed"
        assert len(report["findings"]) == 7
        assert report["access_matrix"]
        assert len(report["chains"]) == 2

        listed = await client.get("/scans")
        assert listed.status_code == 200
        assert any(item["id"] == scan_id for item in listed.json())

        order_bola = next(
            item
            for item in report["findings"]
            if item["vuln_class"] == "bola" and item["endpoint"] == "GET /orders/{order_id}"
        )
        replay = await client.post(
            f"/scans/{scan_id}/findings/{order_bola['id']}/replay"
        )
        assert replay.status_code == 200
        replay_body = replay.json()
        assert replay_body["still_vulnerable"] is True
        assert replay_body["response"]["status"] == 200
        assert "201" in replay_body["request"]["url"]


async def _wait_for_completion(client: AsyncClient, scan_id: int, timeout: float = 60.0) -> dict:
    """Poll GET /scans/{id} until the background engine finishes."""
    deadline = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < deadline:
        response = await client.get(f"/scans/{scan_id}")
        assert response.status_code == 200
        payload = response.json()
        if payload["status"] == "completed":
            return payload
        if payload["status"] == "failed":
            raise AssertionError(f"scan failed: {payload.get('error')}")
        await asyncio.sleep(0.4)
    raise AssertionError(f"scan {scan_id} did not complete within {timeout}s")
