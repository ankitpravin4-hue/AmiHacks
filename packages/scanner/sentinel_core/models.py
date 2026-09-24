"""Shared Pydantic models for the scanner core.

`Finding` and `Report` are field skeletons here — detectors (Phase 3) and
scoring (Phase 4) populate them. `Endpoint`, `Identity`, and `Evidence`
are used immediately by the parser, identity matrix, and safe client.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class Endpoint(BaseModel):
    """One OpenAPI operation, normalized for detectors."""

    method: str
    path: str
    path_params: list[str] = Field(default_factory=list)
    object_id_params: list[str] = Field(
        default_factory=list,
        description="Path params named `id` or `*_id` — BOLA candidates.",
    )
    request_body_schema: dict[str, Any] | None = None
    response_schema: dict[str, Any] | None = None
    auth_required: bool = False

    @property
    def is_bola_candidate(self) -> bool:
        """True when the path takes an object identifier."""
        return bool(self.object_id_params)

    @property
    def key(self) -> str:
        """Stable `METHOD path` identifier."""
        return f"{self.method} {self.path}"


class Identity(BaseModel):
    """A test principal and the objects it is allowed to access."""

    name: str
    headers: dict[str, str] = Field(default_factory=dict)
    owns: dict[str, list[int | str]] = Field(default_factory=dict)
    is_admin: bool = False


class RequestEvidence(BaseModel):
    """A sent request with secrets stripped from headers."""

    method: str
    url: str
    headers: dict[str, str] = Field(default_factory=dict)
    body: Any | None = None


class ResponseEvidence(BaseModel):
    """A received response; body is truncated for storage."""

    status: int
    body: str = ""


class Evidence(BaseModel):
    """Reproducible request/response pair attached to a finding."""

    request: RequestEvidence
    response: ResponseEvidence


class Finding(BaseModel):
    """One vulnerability finding. Populated by detectors and scoring."""

    id: str = ""
    title: str = ""
    vuln_class: str = ""
    endpoint: str = ""
    severity_score: float = 0.0
    severity_label: str = ""
    confidence: float = 0.0
    evidence: list[Evidence] = Field(default_factory=list)
    poc_curl: str = ""
    remediation: str = ""
    business_impact: str = ""
    chain_id: str | None = None


class SummaryStats(BaseModel):
    """Aggregate counts shown on the report and dashboard."""

    total_findings: int = 0
    by_severity: dict[str, int] = Field(default_factory=dict)
    by_vuln_class: dict[str, int] = Field(default_factory=dict)


class ScanConfig(BaseModel):
    """Inputs that produced a report (target, allow-list, safety flags)."""

    target: str = ""
    spec_url: str | None = None
    allowlist: list[str] = Field(default_factory=list)
    safe_mode: bool = True
    identities_file: str | None = None


class Report(BaseModel):
    """Full scan result. Assembled by the engine in Phase 4."""

    target: str = ""
    started_at: datetime | None = None
    finished_at: datetime | None = None
    findings: list[Finding] = Field(default_factory=list)
    summary: SummaryStats = Field(default_factory=SummaryStats)
    scan_config: ScanConfig = Field(default_factory=ScanConfig)
