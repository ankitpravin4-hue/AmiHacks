"""Re-run a stored finding PoC through SafeClient."""

from __future__ import annotations

import json
import re
import shlex
from typing import Any

from sentinel_core.detectors.helpers import collect_sensitive_keys, parse_json
from sentinel_core.http_client import SafeClient
from sentinel_core.models import Evidence, Finding, RequestEvidence
from sentinel_service.schemas import ReplayResult


def parse_poc_curl(poc_curl: str) -> tuple[str, str, dict[str, str], Any | None]:
    """Extract method, URL, headers, and JSON body from a PoC curl."""
    lines: list[str] = []
    for line in poc_curl.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            if lines:
                break
            continue
        if not stripped:
            if lines:
                break
            continue
        lines.append(stripped.rstrip("\\").strip())
    tokens = shlex.split(" ".join(lines))
    method = "GET"
    url = ""
    headers: dict[str, str] = {}
    body: Any | None = None
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token in {"curl", "-i", "-s", "-sS"}:
            index += 1
            continue
        if token == "-X" and index + 1 < len(tokens):
            method = tokens[index + 1].upper()
            index += 2
            continue
        if token == "-H" and index + 1 < len(tokens):
            key, _, value = tokens[index + 1].partition(":")
            headers[key.strip()] = value.strip()
            index += 2
            continue
        if token == "-d" and index + 1 < len(tokens):
            raw = tokens[index + 1]
            try:
                body = json.loads(raw)
            except json.JSONDecodeError:
                body = raw
            index += 2
            continue
        if token.startswith("http://") or token.startswith("https://"):
            url = token
        index += 1
    if not url:
        match = re.search(r"https?://[^\s'\\]+", poc_curl)
        if match:
            url = match.group(0)
    return method, url, headers, body


def request_from_finding(finding: Finding) -> tuple[str, str, dict[str, str], Any | None]:
    """Prefer the copy-paste curl (real token); fall back to stored evidence."""
    if finding.poc_curl:
        method, url, headers, body = parse_poc_curl(finding.poc_curl)
        if url:
            return method, url, headers, body
    if finding.evidence:
        first: RequestEvidence = finding.evidence[0].request
        return first.method, first.url, dict(first.headers), first.body
    raise ValueError(f"Finding {finding.id} has no replayable request")


def still_vulnerable(finding: Finding, evidence: Evidence) -> bool:
    """Interpret the fresh response the same way the detector would."""
    status = evidence.response.status
    if finding.vuln_class == "missing_rate_limit":
        return status != 429
    if not (200 <= status < 300):
        return False
    if finding.vuln_class == "excessive_data_exposure":
        return bool(collect_sensitive_keys(parse_json(evidence.response.body)))
    return True


async def replay_finding(
    finding: Finding,
    *,
    allowed_base_urls: list[str],
    safe_mode: bool,
) -> ReplayResult:
    """Send the PoC through SafeClient (allow-list + safe mode still apply)."""
    method, url, headers, body = request_from_finding(finding)
    kwargs: dict[str, Any] = {"headers": headers}
    if body is not None and method in {"POST", "PUT", "PATCH"}:
        kwargs["json"] = body
    async with SafeClient(allowed_base_urls=allowed_base_urls, safe_mode=safe_mode) as client:
        evidence = await client.request(method, url, **kwargs)
        if method == "PATCH" and isinstance(body, dict) and body.get("is_admin") is True:
            try:
                await client.request(method, url, headers=headers, json={"is_admin": False})
            except Exception:
                pass
    return ReplayResult(
        request=evidence.request,
        response=evidence.response,
        still_vulnerable=still_vulnerable(finding, evidence),
    )
