"""Shared helpers for building URLs, parsing bodies, and PoC curls."""

from __future__ import annotations

import json
import re
from typing import Any

from sentinel_core.http_client import SafeClient
from sentinel_core.models import Endpoint, Evidence

SENSITIVE_KEYS = frozenset(
    {
        "password",
        "password_hash",
        "passwd",
        "token",
        "access_token",
        "refresh_token",
        "secret",
        "ssn",
        "is_admin",
        "is_superuser",
        "is_staff",
    }
)
PRIVILEGED_FIELDS = frozenset(
    {
        "is_admin",
        "is_superuser",
        "is_staff",
        "role",
        "roles",
        "permissions",
        "privileges",
    }
)


def target_base(client: SafeClient) -> str:
    """Scan target = first allow-listed base URL."""
    return client.allowed_base_urls[0].rstrip("/")


def join_url(base: str, path: str) -> str:
    """Join a base URL and a path without dropping the port."""
    return f"{base.rstrip('/')}/{path.lstrip('/')}"


def fill_path(path: str, values: dict[str, int | str]) -> str:
    """Replace ``{param}`` segments. Unresolved braces are left in place."""
    result = path
    for name, value in values.items():
        result = result.replace("{" + name + "}", str(value))
    return result


def path_is_filled(path: str) -> bool:
    """True when no ``{param}`` placeholders remain."""
    return "{" not in path


def slug(*parts: str) -> str:
    """Stable lowercase id from endpoint / identity fragments."""
    raw = "-".join(parts)
    return re.sub(r"[^a-z0-9]+", "-", raw.lower()).strip("-")


def parse_json(text: str) -> Any | None:
    """Parse JSON; return None on junk instead of raising."""
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def is_success(status: int) -> bool:
    """HTTP 2xx."""
    return 200 <= status < 300


def build_curl(
    method: str,
    url: str,
    headers: dict[str, str] | None = None,
    body: Any | None = None,
) -> str:
    """Copy-pasteable curl. Includes real demo tokens on purpose."""
    lines = [f"curl -i -X {method.upper()} '{url}'"]
    headers = dict(headers or {})
    if body is not None and "Content-Type" not in headers and "content-type" not in {
        k.lower() for k in headers
    }:
        headers["Content-Type"] = "application/json"
    for key, value in headers.items():
        escaped = str(value).replace("'", "'\\''")
        lines.append(f"-H '{key}: {escaped}'")
    if body is not None:
        payload = body if isinstance(body, str) else json.dumps(body)
        escaped = payload.replace("'", "'\\''")
        lines.append(f"-d '{escaped}'")
    return " \\\n  ".join(lines)


def curl_from_evidence(
    evidence: Evidence,
    *,
    live_headers: dict[str, str] | None = None,
) -> str:
    """Build a PoC curl; prefer live headers so the token is actually usable."""
    return build_curl(
        evidence.request.method,
        evidence.request.url,
        live_headers if live_headers is not None else evidence.request.headers,
        evidence.request.body,
    )


def collect_sensitive_keys(payload: Any, found: set[str] | None = None) -> set[str]:
    """Walk a JSON value and collect sensitive object keys."""
    found = found if found is not None else set()
    if isinstance(payload, dict):
        for key, value in payload.items():
            name = str(key)
            lowered = name.lower()
            if lowered in SENSITIVE_KEYS or lowered.startswith("internal_"):
                found.add(name)
            collect_sensitive_keys(value, found)
    elif isinstance(payload, list):
        for item in payload:
            collect_sensitive_keys(item, found)
    return found


def schema_property_names(schema: dict[str, Any] | None) -> set[str]:
    """Property names from a (possibly nested) JSON Schema object."""
    if not schema:
        return set()
    names = set(schema.get("properties") or {})
    for key in ("allOf", "anyOf", "oneOf"):
        for item in schema.get(key) or []:
            if isinstance(item, dict):
                names |= schema_property_names(item)
    return names


def looks_like_login(endpoint: Endpoint) -> bool:
    """True for credential-submitting operations (rate-limit targets)."""
    path = endpoint.path.lower()
    if any(token in path for token in ("login", "signin", "sign-in", "token", "auth")):
        return endpoint.method in {"POST", "PUT"}
    props = {name.lower() for name in schema_property_names(endpoint.request_body_schema)}
    return endpoint.method == "POST" and "password" in props


def looks_like_update(endpoint: Endpoint) -> bool:
    """True for object-mutating operations used by mass assignment."""
    return endpoint.method in {"PATCH", "PUT"} and bool(endpoint.request_body_schema)
