#!/usr/bin/env python3
"""Run the full SentinelAPI engine against ShopAPI and print the report."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

SCANNER_ROOT = Path(__file__).resolve().parent.parent
if str(SCANNER_ROOT) not in sys.path:
    sys.path.insert(0, str(SCANNER_ROOT))

from sentinel_core.engine import ScanEngine
from sentinel_core.models import ScanConfig

DEFAULT_BASE = "http://127.0.0.1:8000"
DEFAULT_IDENTITIES = SCANNER_ROOT / "configs" / "shopapi.identities.yaml"


def _progress(percent: int, step: str) -> None:
    print(f"[{percent:3d}%] {step}")


async def _run(base: str, spec: str, identities: Path) -> int:
    engine = ScanEngine()
    report = await engine.run(
        ScanConfig(
            target=base,
            spec_url=spec,
            allowlist=[base],
            identities_file=str(identities),
            safe_mode=True,
        ),
        on_progress=_progress,
    )

    print()
    print(f"=== Scan report #{report.id} ===")
    print(f"Target:   {report.target}")
    print(f"Findings: {report.summary.total_findings}")
    print(f"Severity: {report.summary.by_severity}")
    print(f"Classes:  {report.summary.by_vuln_class}")
    print()
    print("--- Findings ---")
    for finding in report.findings:
        breakdown = finding.severity_breakdown
        extra = ""
        if breakdown is not None:
            extra = f"  impact={breakdown.impact} exploitability={breakdown.exploitability}"
        print(
            f"[{finding.severity_label} {finding.severity_score}] "
            f"{finding.vuln_class}  {finding.endpoint}  "
            f"confidence={finding.confidence}{extra}"
        )
        print(f"  {finding.business_impact}")
        if breakdown is not None:
            for factor in breakdown.factors:
                print(f"    - {factor.name}: {factor.score}/{factor.max_score} — {factor.reason}")
        print()

    print("--- Chains ---")
    if not report.chains:
        print("(none)")
    for chain in report.chains:
        print(
            f"{chain.id}  [{chain.max_severity_label} {chain.max_severity_score}]"
        )
        print(f"  {chain.narrative}")
        print(f"  steps: {' → '.join(chain.finding_ids)}")
        print()
    return 0


def main() -> None:
    """CLI: full engine run with scoring, chains, and SQLite persist."""
    parser = argparse.ArgumentParser(description="Run a full SentinelAPI scan")
    parser.add_argument("--base-url", default=DEFAULT_BASE)
    parser.add_argument("--spec", default=f"{DEFAULT_BASE}/openapi.json")
    parser.add_argument("--identities", type=Path, default=DEFAULT_IDENTITIES)
    args = parser.parse_args()
    raise SystemExit(asyncio.run(_run(args.base_url, args.spec, args.identities)))


if __name__ == "__main__":
    main()
