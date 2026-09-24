"""Stub: autonomous multi-step exploit exploration beyond AttackChainBuilder."""

from __future__ import annotations

from sentinel_core.models import AttackChain, Report


class AgenticExploitAgent:
    """Future agent that chains live API calls to find multi-step bugs.

    # TODO(ai): ``explore`` will take a completed ``Report`` and autonomously
    issue further SafeClient requests (still allow-listed, still safe-mode)
    to discover attack paths the deterministic ``AttackChainBuilder`` cannot
    see. Do not call any LLM provider from this module. Not wired into the
    engine — ``AttackChainBuilder`` remains the only chain source.
    """

    def explore(self, report: Report) -> list[AttackChain]:
        """Not implemented — reserved for a future agentic explorer."""
        raise NotImplementedError(
            "# TODO(ai): AgenticExploitAgent.explore will walk report "
            f"{report.id} and return extra AttackChain rows. "
            "Not wired into ScanEngine."
        )
