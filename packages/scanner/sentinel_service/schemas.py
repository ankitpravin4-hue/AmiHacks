"""HTTP request/response models for the scanner service."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from sentinel_core.models import (
    AttackChain,
    Finding,
    RequestEvidence,
    ResponseEvidence,
    SummaryStats,
)


class ScanCreate(BaseModel):
    """Body for POST /scans."""

    target_base_url: str
    spec_url: str | None = None
    identities_preset: str | None = "shopapi"
    identities_config: dict[str, Any] | list[dict[str, Any]] | None = None
    safe_mode: bool = True


class ScanAccepted(BaseModel):
    """Immediate response after queueing a background scan."""

    scan_id: int
    status: Literal["running"] = "running"


class ScanListItem(BaseModel):
    """Compact row for history / diff pickers."""

    id: int
    target: str
    started_at: datetime | None = None
    finished_at: datetime | None = None
    status: str
    summary: SummaryStats = Field(default_factory=SummaryStats)
    error: str | None = None


class ScanDetail(BaseModel):
    """Full report plus lifecycle status."""

    id: int
    target: str
    started_at: datetime | None = None
    finished_at: datetime | None = None
    status: str
    error: str | None = None
    findings: list[Finding] = Field(default_factory=list)
    chains: list[AttackChain] = Field(default_factory=list)
    access_matrix: dict[str, dict[str, str]] | None = None
    summary: SummaryStats = Field(default_factory=SummaryStats)


class ReplayResult(BaseModel):
    """Fresh SafeClient execution of a stored PoC."""

    request: RequestEvidence
    response: ResponseEvidence
    still_vulnerable: bool


class ScanDiff(BaseModel):
    """Finding-key comparison between two reports."""

    a: int
    b: int
    new: list[str] = Field(default_factory=list)
    fixed: list[str] = Field(default_factory=list)
    persisting: list[str] = Field(default_factory=list)


class ProgressEvent(BaseModel):
    """One WebSocket progress frame."""

    percent: int
    step: str
    status: str | None = None


class AskQuestion(BaseModel):
    """Body for POST /scans/{id}/ask."""

    question: str = Field(..., min_length=1)


class AIAnswer(BaseModel):
    """On-demand Gemini text. ``ai_generated`` is false for fallbacks."""

    text: str
    configured: bool
    ai_generated: bool
