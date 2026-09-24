"""SentinelAPI scanner core — spec parsing, identities, detectors, engine."""

from sentinel_core.attack_chain import AttackChainBuilder
from sentinel_core.detectors import (
    AuthMisconfigDetector,
    BolaDetector,
    Detector,
    ExcessiveDataExposureDetector,
    MassAssignmentDetector,
    RateLimitDetector,
    run_all_detectors,
)
from sentinel_core.engine import ScanEngine
from sentinel_core.http_client import (
    AllowlistDeniedError,
    SafeClient,
    UnsafeMethodError,
)
from sentinel_core.identity import CrossAccessCase, IdentityProvider
from sentinel_core.models import (
    AttackChain,
    Endpoint,
    Evidence,
    Finding,
    Identity,
    Report,
    RequestEvidence,
    ResponseEvidence,
    ScanConfig,
    ScoreFactor,
    SeverityBreakdown,
    SummaryStats,
)
from sentinel_core.scoring import SeverityScorer
from sentinel_core.spec_parser import SpecParser
from sentinel_core.storage import (
    get_finding,
    get_report,
    get_storage,
    list_reports,
    save_report,
)

__all__ = [
    "AllowlistDeniedError",
    "AttackChain",
    "AttackChainBuilder",
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
    "ScanEngine",
    "ScoreFactor",
    "SeverityBreakdown",
    "SeverityScorer",
    "SpecParser",
    "SummaryStats",
    "UnsafeMethodError",
    "get_finding",
    "get_report",
    "get_storage",
    "list_reports",
    "run_all_detectors",
    "save_report",
]
