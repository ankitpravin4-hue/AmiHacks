"""On-demand Gemini advisor. Not called by ScanEngine — scans stay rule-based."""

from __future__ import annotations

from sentinel_core.ai.gemini import GeminiClient, build_ask_prompt, build_explain_prompt
from sentinel_core.models import AttackChain, Finding


class LLMRemediationAdvisor:
    """Explain a single finding, or answer a question about one scan.

    The engine still ships detector-authored remediation strings. Call
    ``advise`` / ``answer`` only from the on-demand service endpoints.
    """

    def __init__(self, client: GeminiClient | None = None) -> None:
        self._client = client or GeminiClient()

    def advise(self, finding: Finding) -> str:
        """Return an AI explanation of one finding, or a graceful fallback."""
        try:
            return self._client.generate(build_explain_prompt(finding))
        except Exception:
            return (
                "AI is unavailable right now (rate limit, network, or provider error). "
                "The rule-based finding is unchanged — try again in a moment."
            )

    def answer(
        self,
        question: str,
        findings: list[Finding],
        chains: list[AttackChain],
        target: str = "",
    ) -> str:
        """Answer a free-form question using this scan's findings and chains."""
        try:
            return self._client.generate(build_ask_prompt(question, findings, chains, target))
        except Exception:
            return (
                "AI is unavailable right now (rate limit, network, or provider error). "
                "The rule-based report is unchanged — try again in a moment."
            )
