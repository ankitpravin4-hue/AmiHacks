"""End-to-end scan orchestration: parse → probe → score → chain → persist."""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

from sentinel_core.attack_chain import AttackChainBuilder
from sentinel_core.detectors import run_all_detectors
from sentinel_core.http_client import SafeClient
from sentinel_core.identity import IdentityProvider
from sentinel_core.models import Finding, Report, ScanConfig, SummaryStats
from sentinel_core.scoring import SeverityScorer
from sentinel_core.spec_parser import SpecParser
from sentinel_core.spec_static import (
    LIVE_ONLY_CHECKS,
    SPEC_ONLY_TARGET,
    findings_from_spec,
)
from sentinel_core.storage import configure, get_report, save_report
from sentinel_core.strategies import HeuristicStrategy, TestStrategy

SCANNER_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_IDENTITIES = SCANNER_ROOT / "configs" / "shopapi.identities.yaml"

ProgressCallback = Callable[[int, str], None]


class ScanEngine:
    """Run a full allow-listed scan and persist the report."""

    def __init__(
        self,
        db_path: Path | str | None = None,
        strategy: TestStrategy | None = None,
    ) -> None:
        configure(db_path)
        self.strategy: TestStrategy = strategy or HeuristicStrategy()

    async def run(
        self,
        scan_config: ScanConfig,
        on_progress: ProgressCallback | None = None,
        scan_id: int | None = None,
    ) -> Report:
        """Parse the spec, run detectors, score, chain, and save the report.

        ``scan_id`` updates an existing running placeholder created by the service.
        """
        config = _normalize_config(scan_config)
        started = datetime.now(timezone.utc)
        if scan_id is not None:
            existing = get_report(scan_id)
            if existing is not None and existing.started_at is not None:
                started = existing.started_at
        live = bool(config.target) and config.target != SPEC_ONLY_TARGET
        parser = SpecParser()
        if config.spec_text:
            _emit(on_progress, 5, "Parsing provided OpenAPI spec")
            endpoints = parser.load_from_text(config.spec_text)
        else:
            _emit(on_progress, 5, "Parsing OpenAPI spec")
            spec_url = config.spec_url or f"{config.target.rstrip('/')}/openapi.json"
            endpoints = parser.load_from_url(spec_url, allowed_base_urls=config.allowlist)
        _emit(on_progress, 15, f"Loaded {len(endpoints)} endpoints")

        skipped = []
        if live:
            identities_path = Path(config.identities_file or DEFAULT_IDENTITIES)
            identities = IdentityProvider.from_file(identities_path)
            _emit(on_progress, 20, f"Loaded {len(identities.all())} identities")

            planned = sum(len(self.strategy.generate_test_cases(item)) for item in endpoints)
            _emit(
                on_progress,
                22,
                f"{self.strategy.name} strategy planned {planned} test cases",
            )

            _emit(on_progress, 25, "Running detectors")
            client_bases = _client_allowlist(config)
            async with SafeClient(
                allowed_base_urls=client_bases,
                safe_mode=config.safe_mode,
            ) as client:
                findings = await run_all_detectors(endpoints, identities, client)
            _emit(on_progress, 70, f"Detectors produced {len(findings)} findings")
        else:
            _emit(
                on_progress,
                25,
                "Static spec checks only — live detectors need a reachable target",
            )
            findings = findings_from_spec(endpoints)
            skipped = list(LIVE_ONLY_CHECKS)
            _emit(on_progress, 70, f"Spec checks produced {len(findings)} findings")

        scorer = SeverityScorer()
        for finding in findings:
            scorer.apply(finding)
        _emit(on_progress, 82, "Scored findings")

        chains = AttackChainBuilder().build(findings)
        _emit(on_progress, 90, f"Built {len(chains)} attack chains")

        report = Report(
            id=scan_id,
            target=config.target,
            started_at=started,
            finished_at=datetime.now(timezone.utc),
            status="completed",
            findings=findings,
            chains=chains,
            access_matrix=_lift_access_matrix(findings),
            summary=_summarize(findings),
            scan_config=config,
            skipped_checks=skipped,
        )
        save_report(report)
        _emit(on_progress, 100, "Report persisted")
        return report


def _client_allowlist(config: ScanConfig) -> list[str]:
    """Prefer the scan target so probes do not hit a different allow-listed host."""
    target = (config.target or "").rstrip("/")
    allow = [item.rstrip("/") for item in config.allowlist]
    if target and target != SPEC_ONLY_TARGET:
        rest = [item for item in allow if item != target]
        return [target, *rest]
    return allow or [target]


def _normalize_config(config: ScanConfig) -> ScanConfig:
    """Fill target / spec / allow-list defaults without scanning the world."""
    spec_text = (config.spec_text or "").strip() or None
    target = (config.target or "").rstrip("/")
    identities = config.identities_file or str(DEFAULT_IDENTITIES)
    if spec_text and not target:
        return config.model_copy(
            update={
                "target": SPEC_ONLY_TARGET,
                "spec_url": None,
                "spec_text": spec_text,
                "allowlist": list(config.allowlist),
                "identities_file": identities,
            }
        )
    if not target:
        target = "http://127.0.0.1:8000"
    allowlist = list(config.allowlist) or [target]
    spec_url = None if spec_text else (config.spec_url or f"{target}/openapi.json")
    return config.model_copy(
        update={
            "target": target,
            "spec_url": spec_url,
            "spec_text": spec_text,
            "allowlist": allowlist,
            "identities_file": identities,
        }
    )


def _lift_access_matrix(
    findings: list[Finding],
) -> dict[str, dict[str, str]] | None:
    """Prefer the BOLA detector's identity matrix on the report."""
    for finding in findings:
        if finding.access_matrix:
            return finding.access_matrix
    return None


def _summarize(findings: list[Finding]) -> SummaryStats:
    """Counts by severity label and vuln class."""
    by_severity = Counter(item.severity_label or "Unscored" for item in findings)
    by_class = Counter(item.vuln_class for item in findings)
    return SummaryStats(
        total_findings=len(findings),
        by_severity=dict(by_severity),
        by_vuln_class=dict(by_class),
    )


def _emit(callback: ProgressCallback | None, percent: int, step: str) -> None:
    if callback is not None:
        callback(percent, step)
