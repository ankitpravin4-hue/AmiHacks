"""Try to set privileged fields on update endpoints as a non-admin."""

from __future__ import annotations

import httpx

from sentinel_core.detectors.helpers import (
    build_curl,
    fill_path,
    is_success,
    join_url,
    looks_like_update,
    parse_json,
    path_is_filled,
    privileged_body_fields,
    slug,
    target_base,
)
from sentinel_core.http_client import (
    DESTRUCTIVE_METHODS,
    AllowlistDeniedError,
    SafeClient,
    UnsafeMethodError,
)
from sentinel_core.identity import IdentityProvider, object_type_from_param
from sentinel_core.models import Endpoint, Finding


class MassAssignmentDetector:
    """PATCH/PUT a privileged field as a customer; revert after the proof."""

    vuln_class = "mass_assignment"

    async def run(
        self,
        endpoints: list[Endpoint],
        identities: IdentityProvider,
        client: SafeClient,
    ) -> list[Finding]:
        """Only run methods safe_mode permits (PATCH is allowed; DELETE is not)."""
        caller = _first_customer(identities)
        if caller is None:
            return []
        base = target_base(client)
        findings: list[Finding] = []
        for endpoint in endpoints:
            if not looks_like_update(endpoint):
                continue
            if client.safe_mode and endpoint.method.upper() in DESTRUCTIVE_METHODS:
                continue
            privileged = privileged_body_fields(endpoint)
            if not privileged:
                continue
            path = _own_path(endpoint, caller)
            if path is None or not path_is_filled(path):
                continue
            field = "is_admin" if "is_admin" in privileged else next(iter(privileged))
            finding = await self._probe_field(
                endpoint, client, base, path, caller.headers, field
            )
            if finding is not None:
                findings.append(finding)
        return findings

    async def _probe_field(
        self,
        endpoint: Endpoint,
        client: SafeClient,
        base: str,
        path: str,
        headers: dict[str, str],
        field: str,
    ) -> Finding | None:
        url = join_url(base, path)
        original = await _read_field(client, url, headers, field)
        applied = False
        evidence_probe = None
        try:
            try:
                evidence_probe = await client.request(
                    endpoint.method,
                    url,
                    headers=headers,
                    json={field: True},
                )
            except (httpx.TransportError, AllowlistDeniedError, UnsafeMethodError):
                return None
            if not is_success(evidence_probe.response.status):
                return None
            payload = parse_json(evidence_probe.response.body)
            applied = isinstance(payload, dict) and payload.get(field) is True
            if not applied:
                applied = await _read_field(client, url, headers, field) is True
            if not applied:
                return None
            return Finding(
                id=slug(self.vuln_class, endpoint.method, endpoint.path, field),
                title=f"Mass assignment of `{field}` on {endpoint.key}",
                vuln_class=self.vuln_class,
                endpoint=endpoint.key,
                evidence=[evidence_probe],
                poc_curl=build_curl(endpoint.method, url, headers, {field: True}),
                remediation=(
                    "Allow-list writable fields. Never bind privileged properties "
                    "from the client body.\n\n"
                    "```python\n"
                    "class UserUpdate(BaseModel):\n"
                    "    email: str | None = None\n"
                    "    phone: str | None = None\n"
                    "    # is_admin is intentionally absent\n"
                    "```"
                ),
                business_impact=(
                    "A regular customer can turn themselves into an admin and "
                    "take over the store — no exploit kit required, just a JSON field."
                ),
                detector_confidence=0.95,
            )
        finally:
            revert_to = False if original is None else bool(original)
            if applied or original is True:
                try:
                    await client.request(
                        endpoint.method,
                        url,
                        headers=headers,
                        json={field: revert_to},
                    )
                except (httpx.TransportError, AllowlistDeniedError, UnsafeMethodError):
                    pass


def _first_customer(identities: IdentityProvider):
    for identity in identities.all():
        if identity.headers and not identity.is_admin:
            return identity
    return None


def _own_path(endpoint: Endpoint, caller) -> str | None:
    values: dict[str, int | str] = {}
    for param in endpoint.object_id_params or endpoint.path_params:
        owned = caller.owns.get(object_type_from_param(param), [])
        if not owned:
            return None
        values[param] = owned[0]
    return fill_path(endpoint.path, values)


async def _read_field(
    client: SafeClient,
    url: str,
    headers: dict[str, str],
    field: str,
) -> bool | None:
    """Best-effort GET of the same URL to learn the current privileged value."""
    try:
        evidence = await client.request("GET", url, headers=headers)
    except (httpx.TransportError, AllowlistDeniedError, UnsafeMethodError):
        return None
    payload = parse_json(evidence.response.body)
    if isinstance(payload, dict) and field in payload:
        return bool(payload[field])
    return None
