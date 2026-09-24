"""Capped burst against login-style endpoints — never a real flood."""

from __future__ import annotations

import httpx

from sentinel_core.detectors.helpers import (
    build_curl,
    join_url,
    looks_like_login,
    slug,
    target_base,
)
from sentinel_core.http_client import AllowlistDeniedError, SafeClient, UnsafeMethodError
from sentinel_core.identity import IdentityProvider
from sentinel_core.models import Endpoint, Evidence, Finding

BURST_SIZE = 15
PROBE_BODY = {"email": "alice@shop.test", "password": "wrong-password"}


class RateLimitDetector:
    """Flag auth endpoints that accept a small burst with no 429."""

    vuln_class = "missing_rate_limit"

    async def run(
        self,
        endpoints: list[Endpoint],
        identities: IdentityProvider,
        client: SafeClient,
    ) -> list[Finding]:
        """Send at most ``BURST_SIZE`` requests; SafeClient caps still apply."""
        _ = identities
        base = target_base(client)
        findings: list[Finding] = []
        for endpoint in endpoints:
            if not looks_like_login(endpoint):
                continue
            url = join_url(base, endpoint.path)
            evidence, saw_throttle = await self._burst(client, endpoint.method, url)
            if not evidence or saw_throttle:
                continue
            findings.append(
                Finding(
                    id=slug(self.vuln_class, endpoint.method, endpoint.path),
                    title=f"No rate limiting on {endpoint.key}",
                    vuln_class=self.vuln_class,
                    endpoint=endpoint.key,
                    evidence=evidence,
                    poc_curl=_burst_poc(endpoint.method, url),
                    remediation=(
                        "Throttle credential endpoints (e.g. 5/min/IP) and lock "
                        "out after repeated failures.\n\n"
                        "```python\n"
                        "# SlowAPI / nginx example\n"
                        "@limiter.limit('5/minute')\n"
                        "@app.post('/login')\n"
                        "def login(...):\n"
                        "    ...\n"
                        "```"
                    ),
                    business_impact=(
                        "An attacker can try passwords as fast as the network allows "
                        "until they walk into a customer account."
                    ),
                    detector_confidence=0.8,
                )
            )
        return findings

    async def _burst(
        self,
        client: SafeClient,
        method: str,
        url: str,
    ) -> tuple[list[Evidence], bool]:
        """Run a hard-capped burst. ``retry=False`` so a 429 is not hidden."""
        collected: list[Evidence] = []
        saw_throttle = False
        for _ in range(BURST_SIZE):
            try:
                evidence = await client.request(
                    method,
                    url,
                    json=PROBE_BODY,
                    retry=False,
                )
            except (httpx.TransportError, AllowlistDeniedError, UnsafeMethodError):
                break
            collected.append(evidence)
            if evidence.response.status == 429:
                saw_throttle = True
                break
        return collected[:3], saw_throttle


def _burst_poc(method: str, url: str) -> str:
    """One request plus a short loop that should have been throttled."""
    single = build_curl(method, url, {}, PROBE_BODY)
    return (
        f"{single}\n\n"
        f"# Repeat {BURST_SIZE} times — ShopAPI never returns 429:\n"
        f"for i in $(seq 1 {BURST_SIZE}); do\n"
        f"  curl -s -o /dev/null -w '%{{http_code}}\\n' -X {method} '{url}' "
        f"-H 'Content-Type: application/json' "
        f"-d '{{\"email\":\"alice@shop.test\",\"password\":\"wrong-password\"}}'\n"
        f"done"
    )
