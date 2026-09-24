"""Broken Object-Level Authorization detector (the identity matrix)."""

from __future__ import annotations

import httpx

from sentinel_core.detectors.helpers import (
    build_curl,
    fill_path,
    is_bola_probe,
    is_success,
    join_url,
    parse_json,
    path_is_filled,
    slug,
    target_base,
)
from sentinel_core.http_client import AllowlistDeniedError, SafeClient, UnsafeMethodError
from sentinel_core.identity import IdentityProvider, object_type_from_param
from sentinel_core.models import Endpoint, Evidence, Finding, Identity


class BolaDetector:
    """Cross-identity object access: A reads an object that B owns.

    Also records ``access_matrix`` (endpoint → identity → allowed|denied)
    for the dashboard Identity Matrix view.
    """

    vuln_class = "bola"

    def __init__(self) -> None:
        self.access_matrix: dict[str, dict[str, str]] = {}

    async def run(
        self,
        endpoints: list[Endpoint],
        identities: IdentityProvider,
        client: SafeClient,
    ) -> list[Finding]:
        """GET each BOLA-candidate object as every non-owner identity."""
        self.access_matrix = {}
        findings: list[Finding] = []
        base = target_base(client)

        for endpoint in endpoints:
            if not is_bola_probe(endpoint):
                continue
            leaked, matrix_row = await self._probe_endpoint(
                endpoint, identities, client, base
            )
            self.access_matrix[endpoint.key] = matrix_row
            if leaked:
                findings.append(self._to_finding(endpoint, leaked))

        for finding in findings:
            finding.access_matrix = self.access_matrix
        return findings

    async def _probe_endpoint(
        self,
        endpoint: Endpoint,
        identities: IdentityProvider,
        client: SafeClient,
        base: str,
    ) -> tuple[list[tuple[Identity, Identity, int | str, Evidence, dict[str, str]]], dict[str, str]]:
        leaked: list[tuple[Identity, Identity, int | str, Evidence, dict[str, str]]] = []
        matrix_row: dict[str, str] = {}
        param = endpoint.object_id_params[0]
        object_type = object_type_from_param(param)

        for case in identities.cross_access_cases(object_type):
            path = fill_path(endpoint.path, {param: case.object_id})
            if not path_is_filled(path):
                continue
            url = join_url(base, path)
            headers = dict(case.attacker.headers)
            try:
                evidence = await client.request(endpoint.method, url, headers=headers)
            except (httpx.TransportError, AllowlistDeniedError, UnsafeMethodError):
                continue

            if case.attacker.name not in matrix_row:
                matrix_row[case.attacker.name] = (
                    "allowed" if is_success(evidence.response.status) else "denied"
                )

            if case.attacker.is_admin:
                continue
            if not is_success(evidence.response.status):
                continue
            if not _contains_owner_object(evidence.response.body, case.object_id, case.owner):
                continue
            leaked.append((case.attacker, case.owner, case.object_id, evidence, headers))

        return leaked, matrix_row

    def _to_finding(
        self,
        endpoint: Endpoint,
        leaked: list[tuple[Identity, Identity, int | str, Evidence, dict[str, str]]],
    ) -> Finding:
        attacker, owner, object_id, evidence, headers = _prefer_alice_bob(leaked)
        pairs = sorted({f"{a.name}→{b.name}" for a, b, *_ in leaked})
        return Finding(
            id=slug(self.vuln_class, endpoint.method, endpoint.path),
            title=f"Broken object-level authorization on {endpoint.key}",
            vuln_class=self.vuln_class,
            endpoint=endpoint.key,
            evidence=[item[3] for item in leaked],
            poc_curl=build_curl(endpoint.method, evidence.request.url, headers),
            remediation=(
                "Enforce object-level authorization: load the object, then reject "
                "the request unless the caller owns it (or is an admin).\n\n"
                "```python\n"
                "order = db.get(Order, order_id)\n"
                "if order.user_id != current_user.id and not current_user.is_admin:\n"
                "    raise HTTPException(status_code=403, detail='Forbidden')\n"
                "```"
            ),
            business_impact=(
                f"Any logged-in customer can open someone else's "
                f"{object_type_label(endpoint)} "
                f"(for example {attacker.name} reading {owner.name}'s {object_id}) — "
                "the same class of bug behind many data breaches."
            ),
            detector_confidence=0.95 if len(pairs) else 0.0,
        )


def object_type_label(endpoint: Endpoint) -> str:
    """Human object name from the first identifier param."""
    return object_type_from_param(endpoint.object_id_params[0])


def _prefer_alice_bob(
    leaked: list[tuple[Identity, Identity, int | str, Evidence, dict[str, str]]],
) -> tuple[Identity, Identity, int | str, Evidence, dict[str, str]]:
    for item in leaked:
        if item[0].name == "alice" and item[1].name == "bob":
            return item
    return leaked[0]


def _contains_owner_object(body: str, object_id: int | str, owner: Identity) -> bool:
    """True when the JSON body is the owner's object, not an empty/error shell."""
    data = parse_json(body)
    if not isinstance(data, dict):
        return False
    if "id" not in data or str(data["id"]) != str(object_id):
        return False
    owner_user_ids = {str(item) for item in owner.owns.get("user", [])}
    if "user_id" in data and owner_user_ids:
        return str(data["user_id"]) in owner_user_ids
    return True
