"""Fail-on threshold and process exit codes for the CI gate."""

from __future__ import annotations

from sentinel_core.models import Finding

SEVERITY_RANK: dict[str, int] = {
    "low": 1,
    "medium": 2,
    "high": 3,
    "critical": 4,
}

EXIT_CLEAN = 0
EXIT_GATE_FAILED = 1
EXIT_ERROR = 2


def findings_at_or_above(findings: list[Finding], fail_on: str) -> list[Finding]:
    """Return findings whose label meets or exceeds ``fail_on``."""
    threshold = SEVERITY_RANK[fail_on.lower()]
    return [
        item
        for item in findings
        if SEVERITY_RANK.get(item.severity_label.lower(), 0) >= threshold
    ]


def gate_message(breaches: list[Finding], fail_on: str) -> str:
    """One-line verdict printed after the report."""
    if not breaches:
        return f"GATE PASSED: 0 findings >= {fail_on.lower()}"
    return f"GATE FAILED: {len(breaches)} findings >= {fail_on.lower()}"
