"""Detector protocol — the seam later AI detectors plug into."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from sentinel_core.http_client import SafeClient
from sentinel_core.identity import IdentityProvider
from sentinel_core.models import Endpoint, Finding


@runtime_checkable
class Detector(Protocol):
    """One vulnerability class. Rule-based today; LLM strategies later.

    Implementations must only talk to the target through ``client`` so the
    allow-list, safe mode, and rate caps always apply.
    """

    vuln_class: str

    async def run(
        self,
        endpoints: list[Endpoint],
        identities: IdentityProvider,
        client: SafeClient,
    ) -> list[Finding]:
        """Probe ``endpoints`` and return findings (no severity — Phase 4)."""
        ...
