"""SentinelAPI scanner core — spec parsing, identities, safe HTTP, detectors."""

from sentinel_core.detectors import (
    AuthMisconfigDetector,
    BolaDetector,
    Detector,
    ExcessiveDataExposureDetector,
    MassAssignmentDetector,
    RateLimitDetector,
    run_all_detectors,
)
from sentinel_core.http_client import (
    AllowlistDeniedError,
    SafeClient,
    UnsafeMethodError,
)
from sentinel_core.identity import CrossAccessCase, IdentityProvider
from sentinel_core.models import (
    Endpoint,
    Evidence,
    Finding,
    Identity,
    Report,
    RequestEvidence,
    ResponseEvidence,
    ScanConfig,
    SummaryStats,
)
from sentinel_core.spec_parser import SpecParser

__all__ = [
    "AllowlistDeniedError",
    "AuthMisconfigDetector",
    "BolaDetector",
    "CrossAccessCase",
    "Detector",
    "Endpoint",
    "Evidence",
    "ExcessiveDataExposureDetector",
    "Finding",
    "Identity",
    "IdentityProvider",
    "MassAssignmentDetector",
    "RateLimitDetector",
    "Report",
    "RequestEvidence",
    "ResponseEvidence",
    "SafeClient",
    "ScanConfig",
    "SpecParser",
    "SummaryStats",
    "UnsafeMethodError",
    "run_all_detectors",
]
