#!/usr/bin/env python3
"""Parse the live ShopAPI spec and print every detector finding."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

SCANNER_ROOT = Path(__file__).resolve().parent.parent
if str(SCANNER_ROOT) not in sys.path:
    sys.path.insert(0, str(SCANNER_ROOT))

from sentinel_core.detectors import run_all_detectors
from sentinel_core.http_client import SafeClient
from sentinel_core.identity import IdentityProvider
from sentinel_core.spec_parser import SpecParser

DEFAULT_SPEC = "http://127.0.0.1:8000/openapi.json"
DEFAULT_BASE = "http://127.0.0.1:8000"
DEFAULT_IDENTITIES = SCANNER_ROOT / "configs" / "shopapi.identities.yaml"


async def _run(spec: str, base: str, identities_path: Path) -> int:
    parser = SpecParser()
    endpoints = parser.load_from_url(spec, allowed_base_urls=[base])
    identities = IdentityProvider.from_file(identities_path)
    async with SafeClient(allowed_base_urls=[base]) as client:
        findings = await run_all_detectors(endpoints, identities, client)

    print(f"{len(findings)} findings against {base}\n")
    for finding in findings:
        print("=" * 72)
        print(f"[{finding.vuln_class}] {finding.endpoint}")
        print(f"id:          {finding.id}")
        print(f"confidence:  {finding.detector_confidence}")
        print(f"impact:      {finding.business_impact}")
        print("poc_curl:")
        print(finding.poc_curl)
        print()
    return 0


def main() -> None:
    """CLI: run all Phase 3 detectors against the allow-listed target."""
    parser = argparse.ArgumentParser(description="Run SentinelAPI rule-based detectors")
    parser.add_argument("--spec", default=DEFAULT_SPEC)
    parser.add_argument("--base-url", default=DEFAULT_BASE)
    parser.add_argument("--identities", type=Path, default=DEFAULT_IDENTITIES)
    args = parser.parse_args()
    raise SystemExit(asyncio.run(_run(args.spec, args.base_url, args.identities)))


if __name__ == "__main__":
    main()
