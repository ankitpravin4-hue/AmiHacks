"""Detect classic SQL injection on string query parameters. SELECT-only probes."""

from __future__ import annotations

import httpx

from sentinel_core.detectors.helpers import (
    build_curl,
    is_public_ops,
    parse_json,
    path_is_filled,
    slug,
    target_base,
    join_url,
)
from sentinel_core.http_client import AllowlistDeniedError, SafeClient, UnsafeMethodError
from sentinel_core.models import Endpoint, Evidence, Finding

# Read-only boolean / syntax probes only. Never DROP, DELETE, UPDATE, INSERT.
BASELINE_VALUE = "sentinel-baseline"
BOOLEAN_PAYLOAD = "' OR '1'='1"
BROKEN_QUOTE = "'"

SQL_ERROR_MARKERS = (
    "operationalerror",
    "programmingerror",
    "syntax error",
    "sqlite3",
    "unclosed quotation",
    "sql syntax",
    "mysql",
    "psycopg",
    "ora-0",
    "you have an error in your sql",
)


class SqlInjectionDetector:
    """Compare a benign query to non-destructive SQLi payloads on string params."""

    vuln_class = "sql_injection"

    async def run(
        self,
        endpoints: list[Endpoint],
        identities,
        client: SafeClient,
    ) -> list[Finding]:
        """Probe query-string endpoints; skip routes with no string query params."""
        del identities
        base = target_base(client)
        findings: list[Finding] = []
        for endpoint in endpoints:
            if endpoint.method != "GET" or is_public_ops(endpoint):
                continue
            if not endpoint.query_params or not path_is_filled(endpoint.path):
                continue
            finding = await _probe_endpoint(endpoint, base, client)
            if finding is not None:
                findings.append(finding)
        return findings


async def _probe_endpoint(
    endpoint: Endpoint,
    base: str,
    client: SafeClient,
) -> Finding | None:
    param = endpoint.query_params[0]
    url = join_url(base, endpoint.path)
    baseline = await _get(client, url, param, BASELINE_VALUE)
    if baseline is None:
        return None
    boolean = await _get(client, url, param, BOOLEAN_PAYLOAD)
    quote = await _get(client, url, param, BROKEN_QUOTE)
    more_rows = boolean is not None and _returns_markedly_more(baseline, boolean)
    sql_error = (quote is not None and _sql_error(quote)) or (
        boolean is not None and _sql_error(boolean)
    )
    if not more_rows and not sql_error:
        return None
    injected = boolean if more_rows and boolean is not None else (quote or boolean)
    if injected is None:
        return None
    evidence = [baseline, injected]
    poc_url = injected.request.url
    return Finding(
        id=slug("sql_injection", endpoint.method, endpoint.path, param),
        title=f"SQL injection on {endpoint.key} ({param})",
        vuln_class="sql_injection",
        endpoint=endpoint.key,
        evidence=evidence,
        poc_curl=build_curl("GET", poc_url),
        remediation=(
            "Bind the search term with a parameterized query / prepared statement. "
            "Never concatenate request input into SQL.\n\n"
            "```python\n"
            "db.execute(\n"
            "    text(\"SELECT id, name FROM products WHERE name LIKE :needle\"),\n"
            "    {\"needle\": f\"%{q}%\"},\n"
            ")\n"
            "```"
        ),
        business_impact=(
            f"{endpoint.key} builds a raw SQL query from the `{param}` parameter. "
            "An unauthenticated caller can bypass the filter and read every matching "
            "table row, and the same flaw often leads to broader database disclosure."
        ),
        detector_confidence=0.95 if more_rows else 0.8,
    )


async def _get(
    client: SafeClient,
    url: str,
    param: str,
    value: str,
) -> Evidence | None:
    try:
        return await client.request("GET", url, params={param: value})
    except (httpx.TransportError, AllowlistDeniedError, UnsafeMethodError):
        return None


def _row_count(evidence: Evidence) -> int | None:
    data = parse_json(evidence.response.body)
    if isinstance(data, list):
        return len(data)
    if isinstance(data, dict):
        for key in ("items", "results", "data"):
            value = data.get(key)
            if isinstance(value, list):
                return len(value)
    return None


def _returns_markedly_more(baseline: Evidence, injected: Evidence) -> bool:
    if not (200 <= injected.response.status < 300):
        return False
    base_count = _row_count(baseline)
    inj_count = _row_count(injected)
    if base_count is None or inj_count is None:
        return False
    return inj_count >= max(base_count + 2, 2) and inj_count > base_count


def _sql_error(evidence: Evidence) -> bool:
    body = evidence.response.body.lower()
    if not any(marker in body for marker in SQL_ERROR_MARKERS):
        return False
    return evidence.response.status >= 400 or "error" in body
