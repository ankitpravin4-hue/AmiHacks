"""Static spec checks. Does not replace live detectors and never invents BOLA."""

from __future__ import annotations

from sentinel_core.detectors.helpers import (
    SENSITIVE_KEYS,
    is_public_ops,
    schema_property_names,
    slug,
)
from sentinel_core.models import Endpoint, Finding, SkippedCheck

LIVE_ONLY_CHECKS: tuple[SkippedCheck, ...] = (
    SkippedCheck(
        check="BOLA/IDOR",
        reason="Requires a live allow-listed target and identities to probe object access.",
    ),
    SkippedCheck(
        check="Broken Auth (live probe)",
        reason="Requires a live allow-listed target to confirm anonymous 2xx on protected routes.",
    ),
    SkippedCheck(
        check="Rate Limiting",
        reason="Requires a live allow-listed target to send a login burst.",
    ),
    SkippedCheck(
        check="Mass Assignment",
        reason="Requires a live allow-listed target to PATCH a privileged field.",
    ),
    SkippedCheck(
        check="SQL Injection",
        reason="Requires a live allow-listed target to compare baseline vs probe responses.",
    ),
)

SPEC_ONLY_TARGET = "spec-only"


def findings_from_spec(endpoints: list[Endpoint]) -> list[Finding]:
    """Findings that can be read from the spec itself — no HTTP is sent."""
    findings: list[Finding] = []
    findings.extend(_excessive_from_schemas(endpoints))
    findings.extend(_missing_security(endpoints))
    return findings


def _excessive_from_schemas(endpoints: list[Endpoint]) -> list[Finding]:
    findings: list[Finding] = []
    for endpoint in endpoints:
        if endpoint.method != "GET" or is_public_ops(endpoint):
            continue
        leaked = _sensitive_schema_fields(endpoint.response_schema)
        if not leaked:
            continue
        listed = ", ".join(sorted(leaked))
        findings.append(
            Finding(
                id=slug("excessive_data_exposure", "spec", endpoint.method, endpoint.path),
                title=f"Response schema exposes sensitive fields on {endpoint.key}",
                vuln_class="excessive_data_exposure",
                endpoint=endpoint.key,
                poc_curl=(
                    "# Spec-only — no live request was sent.\n"
                    f"# {endpoint.key} response schema declares: {listed}"
                ),
                remediation=(
                    "Drop secrets from the documented response schema and return a public DTO.\n\n"
                    "```python\n"
                    "class UserPublic(BaseModel):\n"
                    "    id: int\n"
                    "    email: str\n"
                    "```"
                ),
                business_impact=(
                    f"The spec advertises sensitive fields ({listed}) on {endpoint.key}. "
                    "This is a schema finding, not a confirmed live leak."
                ),
                detector_confidence=0.8,
            )
        )
    return findings


def _missing_security(endpoints: list[Endpoint]) -> list[Finding]:
    findings: list[Finding] = []
    for endpoint in endpoints:
        if endpoint.auth_required or is_public_ops(endpoint):
            continue
        path = endpoint.path.lower()
        if "/admin" not in path and not path.rstrip("/").endswith("/admin"):
            continue
        findings.append(
            Finding(
                id=slug("missing_security", endpoint.method, endpoint.path),
                title=f"Spec omits security on {endpoint.key}",
                vuln_class="missing_security",
                endpoint=endpoint.key,
                poc_curl=(
                    "# Spec-only — no live request was sent.\n"
                    f"# {endpoint.key} has no security requirement in the OpenAPI document."
                ),
                remediation=(
                    "Declare a security scheme on admin and object routes.\n\n"
                    "```yaml\n"
                    "security:\n"
                    "  - HTTPBearer: []\n"
                    "```"
                ),
                business_impact=(
                    f"{endpoint.key} is an admin-scoped operation with no security "
                    "requirement in the spec. Confirm with a live probe before treating "
                    "this as a confirmed broken-auth exploit."
                ),
                detector_confidence=0.75,
            )
        )
    return findings


def _sensitive_schema_fields(schema: dict[str, object] | None) -> set[str]:
    names: set[str] = set()
    for name in schema_property_names(schema):
        lowered = name.lower()
        if lowered in SENSITIVE_KEYS or lowered.startswith("internal_"):
            names.add(name)
    return names
