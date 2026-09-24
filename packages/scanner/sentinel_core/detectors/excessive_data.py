"""Flag responses that return fields a caller should never see."""

from __future__ import annotations

import httpx

from sentinel_core.detectors.helpers import (
    build_curl,
    collect_sensitive_keys,
    fill_path,
    is_public_ops,
    is_success,
    join_url,
    parse_json,
    path_is_filled,
    slug,
    target_base,
)
from sentinel_core.http_client import AllowlistDeniedError, SafeClient, UnsafeMethodError
from sentinel_core.identity import IdentityProvider, object_type_from_param
from sentinel_core.models import Endpoint, Finding


class ExcessiveDataExposureDetector:
    """Inspect GET responses for password hashes, admin flags, internal notes."""

    vuln_class = "excessive_data_exposure"

    async def run(
        self,
        endpoints: list[Endpoint],
        identities: IdentityProvider,
        client: SafeClient,
    ) -> list[Finding]:
        """GET each readable endpoint as a normal user and scan JSON keys."""
        caller = _first_customer(identities)
        if caller is None:
            return []
        base = target_base(client)
        findings: list[Finding] = []
        for endpoint in endpoints:
            if endpoint.method != "GET":
                continue
            if is_public_ops(endpoint):
                continue
            path = _own_path(endpoint, caller)
            if path is None or not path_is_filled(path):
                continue
            url = join_url(base, path)
            headers = dict(caller.headers)
            try:
                evidence = await client.request("GET", url, headers=headers)
            except (httpx.TransportError, AllowlistDeniedError, UnsafeMethodError):
                continue
            if not is_success(evidence.response.status):
                continue
            leaked = collect_sensitive_keys(parse_json(evidence.response.body))
            if not leaked:
                continue
            findings.append(
                Finding(
                    id=slug(self.vuln_class, endpoint.method, endpoint.path),
                    title=f"Excessive data exposure on {endpoint.key}",
                    vuln_class=self.vuln_class,
                    endpoint=endpoint.key,
                    evidence=[evidence],
                    poc_curl=build_curl("GET", url, headers),
                    remediation=(
                        "Return a public DTO — never the ORM row. Drop hash, "
                        "admin, and internal fields from the response schema.\n\n"
                        "```python\n"
                        "class UserPublic(BaseModel):\n"
                        "    id: int\n"
                        "    email: str\n"
                        "    phone: str\n"
                        "```"
                    ),
                    business_impact=(
                        f"The API hands callers sensitive fields ({', '.join(sorted(leaked))}) "
                        "that make account takeover and privilege guessing much easier."
                    ),
                    detector_confidence=_confidence(leaked),
                )
            )
        return findings


def _first_customer(identities: IdentityProvider):
    for identity in identities.all():
        if identity.headers and not identity.is_admin:
            return identity
    return None


def _own_path(endpoint: Endpoint, caller) -> str | None:
    """Fill object-id params with ids the caller legitimately owns."""
    values: dict[str, int | str] = {}
    for param in endpoint.object_id_params:
        owned = caller.owns.get(object_type_from_param(param), [])
        if not owned:
            return None
        values[param] = owned[0]
    return fill_path(endpoint.path, values)


def _confidence(leaked: set[str]) -> float:
    lowered = {name.lower() for name in leaked}
    if lowered & {"password", "password_hash", "ssn", "secret"}:
        return 0.95
    if any(name.startswith("internal_") for name in lowered) or "is_admin" in lowered:
        return 0.9
    return 0.75
