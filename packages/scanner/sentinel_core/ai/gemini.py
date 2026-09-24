"""On-demand Gemini client. Never used by ScanEngine. Never logs the API key."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

from sentinel_core.models import AttackChain, Finding

# Prefer gemini-1.5-flash as specified; Google has retired it for new keys.
MODEL_NAME = "gemini-1.5-flash"
MODEL_FALLBACKS = (MODEL_NAME, "gemini-3.6-flash", "gemini-3.5-flash-lite")
_resolved_model: str | None = None
AI_NOT_CONFIGURED = (
    "AI not configured. Set GEMINI_API_KEY in the repo-root .env to enable "
    "on-demand explanations. The rule-based scanner still works offline."
)
AI_UNAVAILABLE = (
    "AI is unavailable right now (rate limit, network, or provider error). "
    "The rule-based finding is unchanged — try again in a moment."
)
AI_RATE_LIMITED = (
    "Gemini rate-limited this key. Wait a minute and click again. "
    "The rule-based finding is unchanged."
)

_ENV_LOADED = False


def _load_env() -> None:
    """Load repo-root .env once. Does not override an already-exported key."""
    global _ENV_LOADED
    if _ENV_LOADED:
        return
    cursor = Path(__file__).resolve().parent
    seen: list[Path] = []
    for _ in range(6):
        seen.append(cursor / ".env")
        if cursor.parent == cursor:
            break
        cursor = cursor.parent
    seen.append(Path.cwd() / ".env")
    for path in seen:
        if path.is_file():
            load_dotenv(path, override=False)
            break
    _ENV_LOADED = True


def api_key() -> str:
    """Return GEMINI_API_KEY or empty. Never print or log the value."""
    _load_env()
    return (os.environ.get("GEMINI_API_KEY") or "").strip()


def is_configured() -> bool:
    return bool(api_key())


def _truncate(value: str, limit: int = 800) -> str:
    text = (value or "").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def _finding_block(finding: Finding) -> str:
    evidence_lines: list[str] = []
    for item in finding.evidence[:2]:
        req = item.request
        res = item.response
        evidence_lines.append(
            f"  {req.method} {req.url} → {res.status}\n"
            f"  request body: {_truncate(str(req.body), 400)}\n"
            f"  response body: {_truncate(res.body, 600)}"
        )
    evidence = "\n".join(evidence_lines) if evidence_lines else "  (none attached)"
    return (
        f"- id: {finding.id}\n"
        f"- class: {finding.vuln_class}\n"
        f"- endpoint: {finding.endpoint}\n"
        f"- severity: {finding.severity_label} ({finding.severity_score})\n"
        f"- business_impact: {finding.business_impact or '(none)'}\n"
        f"- static_remediation: {_truncate(finding.remediation, 500) or '(none)'}\n"
        f"- evidence:\n{evidence}"
    )


def build_explain_prompt(finding: Finding) -> str:
    return (
        "You are a senior penetration tester briefing a software engineer.\n"
        "Explain ONE finding only.\n\n"
        "Rules:\n"
        "- Reason only from the finding below. Do not invent endpoints, identities, or data.\n"
        "- Be concise (under 280 words).\n"
        "- Use these headings exactly:\n"
        "  1. Why this is exploitable\n"
        "  2. Concrete risk\n"
        "  3. Specific remediation (include a short code or config example)\n"
        "  4. Severity sanity-check (does the given severity fit, and why?)\n\n"
        "Finding:\n"
        f"{_finding_block(finding)}\n"
    )


def build_ask_prompt(
    question: str,
    findings: list[Finding],
    chains: list[AttackChain],
    target: str = "",
) -> str:
    finding_lines = "\n".join(_finding_block(item) for item in findings) or "(no findings)"
    chain_lines = (
        "\n".join(
            f"- {chain.id}: {chain.narrative} "
            f"(severity {chain.max_severity_label}; steps {', '.join(chain.finding_ids)})"
            for chain in chains
        )
        or "(no chains)"
    )
    return (
        "You are a senior penetration tester answering a question about THIS scan only.\n\n"
        "Rules:\n"
        "- Use only the findings and chains below. Do not invent endpoints or findings.\n"
        "- Be concise and actionable.\n"
        "- If the question cannot be answered from this scan, say so.\n\n"
        f"Scan target: {target or '(unknown)'}\n\n"
        f"Findings:\n{finding_lines}\n\n"
        f"Chains:\n{chain_lines}\n\n"
        f"Question: {question.strip()}\n"
    )


class GeminiClient:
    """Thin wrapper around google-generativeai. Failures become fallback strings."""

    def generate(self, prompt: str) -> str:
        key = api_key()
        if not key:
            return AI_NOT_CONFIGURED
        try:
            import google.generativeai as genai
        except ImportError:
            return AI_UNAVAILABLE
        try:
            genai.configure(api_key=key)
            global _resolved_model
            names = (_resolved_model,) if _resolved_model else MODEL_FALLBACKS
            saw_rate_limit = False
            for name in names:
                if not name:
                    continue
                try:
                    model = genai.GenerativeModel(name)
                    response = model.generate_content(
                        prompt,
                        request_options={"timeout": 25},
                    )
                    text = ""
                    try:
                        text = (response.text or "").strip()
                    except Exception:
                        text = ""
                    if text:
                        _resolved_model = name
                        return text
                except Exception as exc:
                    message = str(exc).lower()
                    if "429" in message or "quota" in message or "resource exhausted" in message:
                        saw_rate_limit = True
                        continue
                    if "404" in message or "not found" in message or "no longer available" in message:
                        continue
                    return AI_UNAVAILABLE
            return AI_RATE_LIMITED if saw_rate_limit else AI_UNAVAILABLE
        except Exception:
            return AI_UNAVAILABLE
