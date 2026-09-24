"""SentinelAPI scanner core — spec parsing, identities, and safe HTTP."""

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
    "CrossAccessCase",
    "Endpoint",
    "Evidence",
    "Finding",
    "Identity",
    "IdentityProvider",
    "Report",
    "RequestEvidence",
    "ResponseEvidence",
    "SafeClient",
    "ScanConfig",
    "SpecParser",
    "SummaryStats",
    "UnsafeMethodError",
]
