"""Rule-based vulnerability detectors. AI strategies plug in later."""

from __future__ import annotations

from sentinel_core.detectors.auth_misconfig import AuthMisconfigDetector
from sentinel_core.detectors.base import Detector
from sentinel_core.detectors.bola import BolaDetector
from sentinel_core.detectors.excessive_data import ExcessiveDataExposureDetector
from sentinel_core.detectors.mass_assignment import MassAssignmentDetector
from sentinel_core.detectors.rate_limit import RateLimitDetector
from sentinel_core.http_client import SafeClient
from sentinel_core.identity import IdentityProvider
from sentinel_core.models import Endpoint, Finding


def default_detectors() -> list[Detector]:
    """The five Phase 3 detectors, in demo order."""
    return [
        BolaDetector(),
        ExcessiveDataExposureDetector(),
        AuthMisconfigDetector(),
        RateLimitDetector(),
        MassAssignmentDetector(),
    ]


async def run_all_detectors(
    endpoints: list[Endpoint],
    identities: IdentityProvider,
    client: SafeClient,
    detectors: list[Detector] | None = None,
) -> list[Finding]:
    """Run every detector through ``client`` and concatenate findings."""
    findings: list[Finding] = []
    for detector in detectors or default_detectors():
        findings.extend(await detector.run(endpoints, identities, client))
    return findings


__all__ = [
    "AuthMisconfigDetector",
    "BolaDetector",
    "Detector",
    "ExcessiveDataExposureDetector",
    "MassAssignmentDetector",
    "RateLimitDetector",
    "default_detectors",
    "run_all_detectors",
]
