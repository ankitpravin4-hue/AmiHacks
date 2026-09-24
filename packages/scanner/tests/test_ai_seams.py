"""Phase 8 seams: heuristic strategy is a no-op swap; AI stubs stay unimplemented."""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from sentinel_core.ai import AgenticExploitAgent, LLMRemediationAdvisor
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


def test_remediation_advisor_is_stub() -> None:
    """LLMRemediationAdvisor is not wired and must refuse to run."""
    finding = Finding(id="demo", endpoint="GET /users/{user_id}")
    with pytest.raises(NotImplementedError, match=r"# TODO\(ai\)"):
        LLMRemediationAdvisor().advise(finding)


def test_agentic_exploit_agent_is_stub() -> None:
    """AgenticExploitAgent is not wired and must refuse to run."""
    with pytest.raises(NotImplementedError, match=r"# TODO\(ai\)"):
        AgenticExploitAgent().explore(Report(target=BASE))


@pytest.mark.skipif(not _shopapi_up(), reason="ShopAPI is not running on :8000")
@pytest.mark.asyncio
async def test_heuristic_strategy_same_shopapi_result(tmp_path: Path) -> None:
    """Explicit HeuristicStrategy() must still yield 6 findings and both chains."""
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
    assert len(report.findings) == 6
    assert {chain.id for chain in report.chains} == {
        "account-takeover",
        "cross-user-data-theft",
    }
