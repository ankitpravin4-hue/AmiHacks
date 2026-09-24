"""Transparent, CVSS-inspired severity scoring."""

from __future__ import annotations

from sentinel_core.models import Finding, ScoreFactor, SeverityBreakdown

IMPACT_MAX = 6.0
EXPLOIT_MAX = 4.0


def severity_label(score: float) -> str:
    """Map a 0–10 score onto Critical / High / Medium / Low."""
    if score >= 9:
        return "Critical"
    if score >= 7:
        return "High"
    if score >= 4:
        return "Medium"
    return "Low"


class SeverityScorer:
    """Score a finding from impact + exploitability and expose the breakdown.

    Severity and confidence are independent: a High finding can still be a
    slightly less certain detector result, and vice versa.
    """

    def apply(self, finding: Finding) -> Finding:
        """Fill severity, label, breakdown, and final confidence on ``finding``."""
        breakdown = self.breakdown(finding)
        finding.severity_score = breakdown.score
        finding.severity_label = breakdown.label
        finding.severity_breakdown = breakdown
        finding.confidence = self.final_confidence(finding)
        return finding

    def breakdown(self, finding: Finding) -> SeverityBreakdown:
        """Compute impact (0–6) + exploitability (0–4) with per-factor reasons."""
        impact_factors = [
            self._data_sensitivity(finding),
            self._privilege_gained(finding),
        ]
        exploit_factors = [
            self._auth_required(finding),
            self._complexity(finding),
        ]
        impact = round(min(IMPACT_MAX, sum(factor.score for factor in impact_factors)), 2)
        exploit = round(min(EXPLOIT_MAX, sum(factor.score for factor in exploit_factors)), 2)
        score = round(min(10.0, max(0.0, impact + exploit)), 1)
        return SeverityBreakdown(
            impact=impact,
            exploitability=exploit,
            score=score,
            label=severity_label(score),
            factors=impact_factors + exploit_factors,
        )

    def final_confidence(self, finding: Finding) -> float:
        """Blend detector_confidence with how deterministic the evidence is."""
        evidence_quality = 0.5
        if finding.evidence:
            successes = [
                item for item in finding.evidence if 200 <= item.response.status < 300
            ]
            if successes:
                evidence_quality = 0.95
            elif finding.evidence:
                evidence_quality = 0.7
        if finding.poc_curl:
            evidence_quality = min(1.0, evidence_quality + 0.05)
        detector = max(0.0, min(1.0, finding.detector_confidence))
        return round(max(0.0, min(1.0, 0.65 * detector + 0.35 * evidence_quality)), 2)

    def _data_sensitivity(self, finding: Finding) -> ScoreFactor:
        vuln = finding.vuln_class
        path = finding.endpoint.lower()
        if vuln == "bola" and "user" in path:
            return ScoreFactor(
                name="data_sensitivity",
                score=3.2,
                max_score=3.5,
                reason="Cross-user profile disclosure (identity + contact data).",
            )
        if vuln == "bola":
            return ScoreFactor(
                name="data_sensitivity",
                score=3.0,
                max_score=3.5,
                reason="Cross-user object disclosure (order / PII).",
            )
        if vuln == "excessive_data_exposure":
            return ScoreFactor(
                name="data_sensitivity",
                score=3.0,
                max_score=3.5,
                reason="Response includes secrets (hashes, admin flags, internal notes).",
            )
        if vuln == "broken_authentication" and "admin" in path:
            return ScoreFactor(
                name="data_sensitivity",
                score=2.4,
                max_score=3.5,
                reason="Admin-scoped metrics and staff-only data are exposed.",
            )
        if vuln == "mass_assignment":
            return ScoreFactor(
                name="data_sensitivity",
                score=2.0,
                max_score=3.5,
                reason="Privileged identity fields are writable by the client.",
            )
        if vuln == "missing_rate_limit":
            return ScoreFactor(
                name="data_sensitivity",
                score=1.0,
                max_score=3.5,
                reason="No data leaked yet — impact is unconstrained password guessing.",
            )
        return ScoreFactor(
            name="data_sensitivity",
            score=1.2,
            max_score=3.5,
            reason="Generic data exposure without a more specific class.",
        )

    def _privilege_gained(self, finding: Finding) -> ScoreFactor:
        vuln = finding.vuln_class
        path = finding.endpoint.lower()
        if vuln == "mass_assignment":
            return ScoreFactor(
                name="privilege_gained",
                score=2.5,
                max_score=2.5,
                reason="A customer can grant themselves admin.",
            )
        if vuln == "broken_authentication" and "admin" in path:
            return ScoreFactor(
                name="privilege_gained",
                score=2.4,
                max_score=2.5,
                reason="Anonymous caller reaches admin functionality.",
            )
        if vuln == "bola":
            return ScoreFactor(
                name="privilege_gained",
                score=2.0,
                max_score=2.5,
                reason="Horizontal privilege: identity A reads identity B's object.",
            )
        if vuln == "excessive_data_exposure":
            return ScoreFactor(
                name="privilege_gained",
                score=1.3,
                max_score=2.5,
                reason="Caller learns admin flags and credential material.",
            )
        if vuln == "missing_rate_limit":
            return ScoreFactor(
                name="privilege_gained",
                score=0.8,
                max_score=2.5,
                reason="Lowers the cost of walking into an account.",
            )
        return ScoreFactor(
            name="privilege_gained",
            score=1.0,
            max_score=2.5,
            reason="Limited privilege change.",
        )

    def _auth_required(self, finding: Finding) -> ScoreFactor:
        if _is_anonymous_reachable(finding):
            return ScoreFactor(
                name="auth_required",
                score=2.0,
                max_score=2.0,
                reason="Anonymous-reachable — no stolen token required.",
            )
        if finding.vuln_class == "missing_rate_limit":
            return ScoreFactor(
                name="auth_required",
                score=1.6,
                max_score=2.0,
                reason="Unauthenticated login surface; anyone can hammer it.",
            )
        return ScoreFactor(
            name="auth_required",
            score=1.2,
            max_score=2.0,
            reason="Any valid customer token is enough.",
        )

    def _complexity(self, finding: Finding) -> ScoreFactor:
        if finding.vuln_class == "missing_rate_limit":
            return ScoreFactor(
                name="complexity",
                score=1.0,
                max_score=2.0,
                reason="Needs a burst of guesses — simple, but not a one-shot.",
            )
        if finding.vuln_class == "mass_assignment":
            return ScoreFactor(
                name="complexity",
                score=1.5,
                max_score=2.0,
                reason="Single PATCH with one privileged JSON field.",
            )
        return ScoreFactor(
            name="complexity",
            score=1.8,
            max_score=2.0,
            reason="Single request, no extra conditions.",
        )


def _is_anonymous_reachable(finding: Finding) -> bool:
    """True when a 2xx was obtained without presenting a credential."""
    if finding.vuln_class == "broken_authentication":
        return True
    if finding.access_matrix:
        for row in finding.access_matrix.values():
            if row.get("anonymous") == "allowed":
                return True
    for item in finding.evidence:
        headers = {key.lower(): value for key, value in item.request.headers.items()}
        has_auth = bool(headers.get("authorization"))
        if 200 <= item.response.status < 300 and not has_auth:
            return True
    return False
