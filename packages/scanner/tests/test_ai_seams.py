"""Phase 8 seams: heuristic strategy is a no-op swap; unused AI stubs stay unimplemented."""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from sentinel_core.ai import AgenticExploitAgent, LLMRemediationAdvisor
from sentinel_core.ai.gemini import AI_NOT_CONFIGURED, GeminiClient
from sentinel_core.engine import ScanEngine
from sentinel_core.models import Endpoint, Finding, Report, ScanConfig
from sentinel_core.strategies import HeuristicStrategy, LLMTestStrategy

SCANNER_ROOT = Path(__file__).resolve().parent.parent
IDENTITIES = SCANNER_ROOT / "configs" / "shopapi.identities.yaml"
BASE = "http://127.0.0.1:8000"


def _shopapi_up() -> bool:
    try:
        response = httpx.get(f"{BASE}/healthz", timeout=2.0)
    except httpx.HTTPError:
        return False
    return response.status_code == 200


def test_llm_test_strategy_is_stub() -> None:
    """LLMTestStrategy must not invent cases or call a provider."""
    endpoint = Endpoint(method="GET", path="/users/{user_id}", path_params=["user_id"])
    with pytest.raises(NotImplementedError, match=r"# TODO\(ai\)"):
        LLMTestStrategy().generate_test_cases(endpoint)


def test_remediation_advisor_graceful_without_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Without GEMINI_API_KEY, advise returns a clean fallback and does not raise."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setattr("sentinel_core.ai.gemini._ENV_LOADED", True)
    finding = Finding(
        id="demo",
        vuln_class="bola",
        endpoint="GET /users/{user_id}",
        severity_label="High",
        business_impact="Cross-user read",
    )
    text = LLMRemediationAdvisor().advise(finding)
    assert "AI not configured" in text
    assert AI_NOT_CONFIGURED in text


def test_remediation_advisor_uses_injected_client() -> None:
    """advise / answer pass the finding or scan context to the client prompt."""

    class _Fake(GeminiClient):
        last = ""

        def generate(self, prompt: str) -> str:
            self.last = prompt
            return "OK"

    finding = Finding(id="demo", vuln_class="bola", endpoint="GET /users/{user_id}")
    fake = _Fake()
    advisor = LLMRemediationAdvisor(client=fake)
    assert advisor.advise(finding) == "OK"
    assert "GET /users/{user_id}" in fake.last
    assert "senior penetration tester" in fake.last
    assert advisor.answer("Which first?", [finding], [], target=BASE) == "OK"
    assert "Which first?" in fake.last


def test_agentic_exploit_agent_is_stub() -> None:
    """AgenticExploitAgent is not wired and must refuse to run."""
    with pytest.raises(NotImplementedError, match=r"# TODO\(ai\)"):
        AgenticExploitAgent().explore(Report(target=BASE))


@pytest.mark.skipif(not _shopapi_up(), reason="ShopAPI is not running on :8000")
@pytest.mark.asyncio
async def test_heuristic_strategy_same_shopapi_result(tmp_path: Path) -> None:
    """Explicit HeuristicStrategy() must still yield 7 findings and both chains."""
    engine = ScanEngine(
        db_path=tmp_path / "sentinel.db",
        strategy=HeuristicStrategy(),
    )
    report = await engine.run(
        ScanConfig(
            target=BASE,
            spec_url=f"{BASE}/openapi.json",
            allowlist=[BASE],
            identities_file=str(IDENTITIES),
            safe_mode=True,
        )
    )
    assert engine.strategy.name == "heuristic"
    assert len(report.findings) == 7
    assert {chain.id for chain in report.chains} == {
        "account-takeover",
        "cross-user-data-theft",
    }
