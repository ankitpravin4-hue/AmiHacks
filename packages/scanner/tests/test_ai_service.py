"""On-demand AI endpoints — no live Gemini, no ShopAPI required."""

from __future__ import annotations

from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from sentinel_core.models import Finding, Report
from sentinel_core.storage import get_storage
from sentinel_service.app import create_app


@pytest.mark.asyncio
async def test_explain_and_ask_with_mocked_gemini(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-not-a-real-key")
    monkeypatch.setattr("sentinel_core.ai.gemini._ENV_LOADED", True)
    monkeypatch.setattr(
        "sentinel_core.ai.gemini.GeminiClient.generate",
        lambda self, prompt: f"GEMINI::{prompt.splitlines()[-1][:60]}",
    )

    app = create_app(db_path=tmp_path / "ai.db", allowlist=["http://127.0.0.1:8000"])
    storage = get_storage()
    finding = Finding(
        id="bola-demo",
        vuln_class="bola",
        endpoint="GET /users/{user_id}",
        severity_label="High",
        severity_score=8.2,
        business_impact="Cross-user read",
    )
    report = storage.save_report(
        Report(target="http://127.0.0.1:8000", status="completed", findings=[finding])
    )
    assert report.id is not None

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        missing = await client.post("/scans/999/findings/nope/explain")
        assert missing.status_code == 404

        explained = await client.post(f"/scans/{report.id}/findings/bola-demo/explain")
        assert explained.status_code == 200
        body = explained.json()
        assert body["configured"] is True
        assert body["ai_generated"] is True
        assert body["text"].startswith("GEMINI::")

        blank = await client.post(f"/scans/{report.id}/ask", json={"question": "   "})
        assert blank.status_code == 400

        asked = await client.post(
            f"/scans/{report.id}/ask",
            json={"question": "Which finding should I fix first?"},
        )
        assert asked.status_code == 200
        ask_body = asked.json()
        assert ask_body["ai_generated"] is True
        assert "Which finding should I fix first?" in ask_body["text"]


@pytest.mark.asyncio
async def test_explain_without_key(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setattr("sentinel_core.ai.gemini._ENV_LOADED", True)

    app = create_app(db_path=tmp_path / "ai-nokey.db", allowlist=["http://127.0.0.1:8000"])
    storage = get_storage()
    finding = Finding(id="demo", endpoint="GET /admin/stats", vuln_class="broken_authentication")
    report = storage.save_report(Report(target="http://127.0.0.1:8000", findings=[finding]))
    assert report.id is not None

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        explained = await client.post(f"/scans/{report.id}/findings/demo/explain")
        assert explained.status_code == 200
        body = explained.json()
        assert body["configured"] is False
        assert body["ai_generated"] is False
        assert "AI not configured" in body["text"]
