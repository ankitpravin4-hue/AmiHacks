"""Shared Pydantic models for the scanner core."""

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


class ScoreFactor(BaseModel):
    """One scoring input the dashboard can explain."""

    name: str
    score: float
    max_score: float
    reason: str


class SeverityBreakdown(BaseModel):
    """CVSS-inspired split: impact + exploitability = 0–10 score."""

    impact: float = 0.0
    exploitability: float = 0.0
    score: float = 0.0
    label: str = ""
    factors: list[ScoreFactor] = Field(default_factory=list)


class Finding(BaseModel):
    """One vulnerability finding. Detectors fill evidence; the scorer fills severity."""

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
    detector_confidence: float = 0.0
    access_matrix: dict[str, dict[str, str]] | None = None
    severity_breakdown: SeverityBreakdown | None = None


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


class AttackChain(BaseModel):
    """Ordered findings that combine into a single attacker story."""

    id: str
    finding_ids: list[str] = Field(default_factory=list)
    narrative: str = ""
    max_severity_score: float = 0.0
    max_severity_label: str = ""


class Report(BaseModel):
    """Full scan result. Assembled by the engine and persisted to SQLite."""

    id: int | None = None
    target: str = ""
    started_at: datetime | None = None
    finished_at: datetime | None = None
    status: str = "completed"
    error: str | None = None
    findings: list[Finding] = Field(default_factory=list)
    chains: list[AttackChain] = Field(default_factory=list)
    access_matrix: dict[str, dict[str, str]] | None = None
    summary: SummaryStats = Field(default_factory=SummaryStats)
    scan_config: ScanConfig = Field(default_factory=ScanConfig)
