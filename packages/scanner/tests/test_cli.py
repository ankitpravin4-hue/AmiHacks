"""CLI gate exit codes and SARIF shape against live ShopAPI."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
from typer.testing import CliRunner

from sentinel_cli.formatters import validate_sarif
from sentinel_cli.main import app

BASE = "http://127.0.0.1:8000"
runner = CliRunner()


def _shopapi_up() -> bool:
    try:
        response = httpx.get(f"{BASE}/healthz", timeout=2.0)
    except httpx.HTTPError:
        return False
    return response.status_code == 200


def test_non_allowlisted_target_exits_2() -> None:
    """Foreign hosts are rejected before ScanEngine runs."""
    result = runner.invoke(
        app,
        ["scan", "--target", "https://example.com", "--identities", "shopapi"],
    )
    assert result.exit_code == 2
    assert "allow-list" in (result.stderr or result.output)


@pytest.mark.skipif(not _shopapi_up(), reason="ShopAPI is not running on :8000")
def test_fail_on_high_exits_1() -> None:
    """ShopAPI has High findings — the default CI gate must fail."""
    result = runner.invoke(
        app,
        [
            "scan",
            "--target",
            BASE,
            "--identities",
            "shopapi",
            "--fail-on",
            "high",
            "--format",
            "table",
        ],
    )
    assert result.exit_code == 1
    combined = (result.stdout or "") + (result.stderr or "")
    assert "GATE FAILED" in combined
    assert ">= high" in combined


@pytest.mark.skipif(not _shopapi_up(), reason="ShopAPI is not running on :8000")
def test_fail_on_critical_exits_0() -> None:
    """No Critical scores on ShopAPI — --fail-on critical is a passing run."""
    result = runner.invoke(
        app,
        [
            "scan",
            "--target",
            BASE,
            "--identities",
            "shopapi",
            "--fail-on",
            "critical",
            "--format",
            "table",
        ],
    )
    assert result.exit_code == 0
    combined = (result.stdout or "") + (result.stderr or "")
    assert "GATE PASSED" in combined


@pytest.mark.skipif(not _shopapi_up(), reason="ShopAPI is not running on :8000")
def test_sarif_is_valid_with_seven_results(tmp_path: Path) -> None:
    """SARIF 2.1.0 JSON with one result per ShopAPI finding."""
    dest = tmp_path / "results.sarif"
    result = runner.invoke(
        app,
        [
            "scan",
            "--target",
            BASE,
            "--identities",
            "shopapi",
            "--fail-on",
            "critical",
            "--format",
            "sarif",
            "-o",
            str(dest),
        ],
    )
    assert result.exit_code == 0
    document = json.loads(dest.read_text(encoding="utf-8"))
    validate_sarif(document)
    results = document["runs"][0]["results"]
    assert len(results) == 7
    assert {item["ruleId"] for item in results} >= {
        "bola",
        "broken_authentication",
        "excessive_data_exposure",
        "missing_rate_limit",
        "mass_assignment",
        "sql_injection",
    }
    for item in results:
        assert "endpoint" in item["properties"]
        assert "poc_curl" in item["properties"]
        assert item["level"] in {"error", "warning", "note"}
