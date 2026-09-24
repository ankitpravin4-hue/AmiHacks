"""Call protected / admin endpoints with no credentials."""

from __future__ import annotations

import httpx
import re

from sentinel_core.detectors.helpers import (
    build_curl,
    fill_path,
    is_success,
    join_url,
    path_is_filled,
    slug,
    target_base,
)
from sentinel_core.http_client import AllowlistDeniedError, SafeClient, UnsafeMethodError
from sentinel_core.identity import IdentityProvider, object_type_from_param
from sentinel_core.models import Endpoint, Finding

_ADMIN_PATH = re.compile(r"/admin(?:/|$)", re.IGNORECASE)
_PUBLIC_SAFE = frozenset({"/products", "/healthz", "/health", "/docs", "/redoc", "/openapi.json"})


class AuthMisconfigDetector:
    """2xx on a spec-protected or /admin/* route without a token is broken auth."""

    vuln_class = "broken_authentication"

    async def run(
        self,
        endpoints: list[Endpoint],
        identities: IdentityProvider,
        client: SafeClient,
    ) -> list[Finding]:
        """Probe sensitive routes anonymously. Public catalog/health are skipped."""
        base = target_base(client)
        sample_ids = _sample_ids(identities)
        findings: list[Finding] = []
        for endpoint in endpoints:
            if not _is_sensitive(endpoint):
                continue
            path = _fill_with_samples(endpoint, sample_ids)
            if path is None or not path_is_filled(path):
                continue
            url = join_url(base, path)
            try:
                evidence = await client.request(endpoint.method, url, headers={})
            except (httpx.TransportError, AllowlistDeniedError, UnsafeMethodError):
                continue
            if not is_success(evidence.response.status):
                continue
            findings.append(
                Finding(
                    id=slug(self.vuln_class, endpoint.method, endpoint.path),
                    title=f"Broken authentication on {endpoint.key}",
                    vuln_class=self.vuln_class,
                    endpoint=endpoint.key,
                    evidence=[evidence],
                    poc_curl=build_curl(endpoint.method, url, {}),
                    remediation=(
                        "Require authentication on every admin and object route. "
                        "Do not rely on an unlisted URL staying secret.\n\n"
                        "```python\n"
                        "@router.get('/admin/stats')\n"
                        "def admin_stats(user: User = Depends(require_admin)):\n"
                        "    ...\n"
                        "```"
                    ),
                    business_impact=(
                        "Anyone on the network can open an internal admin page with "
                        "no login — store metrics and staff-only data are public."
                    ),
                    detector_confidence=0.95 if _ADMIN_PATH.search(endpoint.path) else 0.85,
                )
            )
        return findings


def _is_sensitive(endpoint: Endpoint) -> bool:
    path = endpoint.path.rstrip("/") or "/"
    if path in _PUBLIC_SAFE or path.startswith("/products"):
        return False
    return endpoint.auth_required or bool(_ADMIN_PATH.search(endpoint.path))


def _sample_ids(identities: IdentityProvider) -> dict[str, int | str]:
    """Any known object id per type, for filling protected path templates."""
    samples: dict[str, int | str] = {}
    for identity in identities.all():
        for object_type, ids in identity.owns.items():
            if object_type not in samples and ids:
                samples[object_type] = ids[0]
    return samples


def _fill_with_samples(endpoint: Endpoint, samples: dict[str, int | str]) -> str | None:
    values: dict[str, int | str] = {}
    for param in endpoint.path_params:
        object_type = object_type_from_param(param)
        if object_type in samples:
            values[param] = samples[object_type]
        elif samples:
            values[param] = next(iter(samples.values()))
        else:
            return None
    return fill_path(endpoint.path, values)
