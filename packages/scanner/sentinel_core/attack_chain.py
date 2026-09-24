"""Deterministic attack-chain linking from vuln class + endpoint."""

from __future__ import annotations

from sentinel_core.models import AttackChain, Finding
from sentinel_core.scoring import severity_label


class AttackChainBuilder:
    """Link findings into short, judge-readable attacker stories."""

    def build(self, findings: list[Finding]) -> list[AttackChain]:
        """Return chains and set ``finding.chain_id`` for members.

        Findings that do not match a rule stay standalone (``chain_id`` is None).
        A finding is assigned to at most one chain.
        """
        chains: list[AttackChain] = []
        takeover = self._account_takeover(findings)
        if takeover is not None:
            chains.append(takeover)
        theft = self._cross_user_theft(findings)
        if theft is not None:
            chains.append(theft)
        return chains

    def _account_takeover(self, findings: list[Finding]) -> AttackChain | None:
        mass = _first(
            findings,
            vuln_class="mass_assignment",
            endpoint_contains="/users/",
        )
        admin = _first(
            findings,
            vuln_class="broken_authentication",
        ) or _first(findings, endpoint_contains="/admin")
        if mass is None or admin is None:
            return None
        if mass.chain_id or admin.chain_id:
            return None
        return _bind(
            chain_id="account-takeover",
            members=[mass, admin],
            narrative=(
                "A normal user promotes themselves to admin, then reads the admin dashboard."
            ),
        )

    def _cross_user_theft(self, findings: list[Finding]) -> AttackChain | None:
        bola = _first(
            findings,
            vuln_class="bola",
            endpoint_contains="/users/{user_id}",
        )
        exposure = _first(
            findings,
            vuln_class="excessive_data_exposure",
            endpoint_contains="/users/{user_id}",
        )
        if bola is None or exposure is None:
            return None
        if bola.chain_id or exposure.chain_id:
            return None
        return _bind(
            chain_id="cross-user-data-theft",
            members=[bola, exposure],
            narrative=(
                "Any logged-in user can pull another user's full record including secrets."
            ),
        )


def _first(
    findings: list[Finding],
    *,
    vuln_class: str | None = None,
    endpoint_contains: str | None = None,
) -> Finding | None:
    for finding in findings:
        if vuln_class and finding.vuln_class != vuln_class:
            continue
        if endpoint_contains and endpoint_contains not in finding.endpoint:
            continue
        return finding
    return None


def _bind(chain_id: str, members: list[Finding], narrative: str) -> AttackChain:
    for finding in members:
        finding.chain_id = chain_id
    max_score = max(item.severity_score for item in members)
    return AttackChain(
        id=chain_id,
        finding_ids=[item.id for item in members],
        narrative=narrative,
        max_severity_score=max_score,
        max_severity_label=severity_label(max_score),
    )
