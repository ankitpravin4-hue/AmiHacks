"""Stub: richer, context-aware remediations than the static finding strings."""

from __future__ import annotations

from sentinel_core.models import Finding


class LLMRemediationAdvisor:
    """Future AI advisor for per-finding fix text.

    # TODO(ai): ``advise`` will take a scored ``Finding`` (endpoint, evidence,
    PoC, current static remediation) and return a longer, framework-aware
    patch suggestion. Do not call any LLM provider from this module. The
    engine still ships the detector-authored remediation strings.
    """

    def advise(self, finding: Finding) -> str:
        """Not implemented — reserved for a future LLM rewrite of remediations."""
        raise NotImplementedError(
            "# TODO(ai): LLMRemediationAdvisor.advise will generate a richer "
            f"fix for {finding.id or finding.endpoint} than the static string. "
            "Not wired into ScanEngine."
        )
