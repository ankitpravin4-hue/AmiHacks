"""Normalize OpenAPI 3 / Swagger specs into `Endpoint` records."""

from __future__ import annotations

import json
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

import httpx
import yaml

from sentinel_core.http_client import AllowlistDeniedError, default_allowlist, url_is_allowed
from sentinel_core.models import Endpoint

HTTP_METHODS = frozenset({"get", "put", "post", "delete", "options", "head", "patch", "trace"})
SUCCESS_CODES = ("200", "201", "202", "204")


def is_object_id_param(name: str) -> bool:
    """True for path params named ``id`` or ending in ``_id`` (case-insensitive)."""
    lowered = name.lower()
    return lowered == "id" or lowered.endswith("_id")


def _lookup_ref(spec: dict[str, Any], ref: str) -> Any:
    """Resolve a local JSON pointer such as ``#/components/schemas/User``."""
    if not ref.startswith("#/"):
        raise ValueError(f"Only local $ref values are supported, got {ref!r}")
    node: Any = spec
    for part in ref[2:].split("/"):
        key = part.replace("~1", "/").replace("~0", "~")
        if not isinstance(node, dict) or key not in node:
            raise KeyError(f"Unresolvable $ref {ref}")
        node = node[key]
    return node


def resolve_refs(node: Any, spec: dict[str, Any], seen: set[str] | None = None) -> Any:
    """Recursively expand local ``$ref`` nodes. Cycles are left unresolved."""
    seen = seen if seen is not None else set()
    if isinstance(node, dict):
        ref = node.get("$ref")
        if isinstance(ref, str):
            if ref in seen:
                return node
            seen.add(ref)
            return resolve_refs(_lookup_ref(spec, ref), spec, seen)
        return {key: resolve_refs(value, spec, seen) for key, value in node.items()}
    if isinstance(node, list):
        return [resolve_refs(item, spec, seen) for item in node]
    return node


def _iter_parameters(
    operation: dict[str, Any],
    path_item: dict[str, Any],
    spec: dict[str, Any],
) -> list[dict[str, Any]]:
    """Merge path-level and operation-level parameters, resolving $refs."""
    merged: list[dict[str, Any]] = []
    for raw in list(path_item.get("parameters") or []) + list(operation.get("parameters") or []):
        if not isinstance(raw, dict):
            continue
        param = resolve_refs(raw, spec) if "$ref" in raw else raw
        if isinstance(param, dict):
            merged.append(param)
    return merged


def _path_param_names(path: str, parameters: Sequence[dict[str, Any]]) -> list[str]:
    """Declared path params, falling back to ``{name}`` segments in the template."""
    names: list[str] = []
    for param in parameters:
        if param.get("in") == "path" and param.get("name"):
            name = str(param["name"])
            if name not in names:
                names.append(name)
    leftover = path
    while "{" in leftover and "}" in leftover:
        start = leftover.index("{")
        end = leftover.index("}", start)
        name = leftover[start + 1 : end]
        leftover = leftover[end + 1 :]
        if name and name not in names:
            names.append(name)
    return names


def _request_body_schema(operation: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any] | None:
    """JSON request body schema (OpenAPI 3 `requestBody` or Swagger 2 `in: body`)."""
    body = operation.get("requestBody")
    if isinstance(body, dict):
        resolved = resolve_refs(body, spec)
        content = resolved.get("content") or {}
        media = content.get("application/json") or next(iter(content.values()), None)
        if isinstance(media, dict) and isinstance(media.get("schema"), dict):
            return resolve_refs(media["schema"], spec)
    for param in operation.get("parameters") or []:
        if isinstance(param, dict) and param.get("in") == "body":
            schema = param.get("schema")
            if isinstance(schema, dict):
                return resolve_refs(schema, spec)
    return None


def _response_schema(operation: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any] | None:
    """Preferred success-response JSON schema."""
    responses = operation.get("responses") or {}
    if not isinstance(responses, dict):
        return None
    for code in (*SUCCESS_CODES, "2XX", "default"):
        raw = responses.get(code)
        if raw is None:
            continue
        resolved = resolve_refs(raw, spec) if isinstance(raw, dict) else {}
        if not isinstance(resolved, dict):
            continue
        content = resolved.get("content") or {}
        if isinstance(content, dict) and content:
            media = content.get("application/json") or next(iter(content.values()), None)
            if isinstance(media, dict) and isinstance(media.get("schema"), dict):
                return resolve_refs(media["schema"], spec)
        schema = resolved.get("schema")
        if isinstance(schema, dict):
            return resolve_refs(schema, spec)
    return None


def _auth_required(operation: dict[str, Any], spec: dict[str, Any]) -> bool:
    """True when the operation (or spec-level default) declares a security scheme."""
    if "security" in operation:
        requirements = operation["security"] or []
        return any(bool(item) for item in requirements)
    global_req = spec.get("security") or []
    return any(bool(item) for item in global_req)


def _loads(text: str) -> dict[str, Any]:
    """Parse JSON or YAML into a spec object."""
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass
    data = yaml.safe_load(text)
    if not isinstance(data, dict):
        raise ValueError("OpenAPI/Swagger document must be a JSON or YAML object")
    return data


class SpecParser:
    """Load and normalize OpenAPI 3 / Swagger 2 specifications."""

    def parse(self, spec: dict[str, Any]) -> list[Endpoint]:
        """Normalize every operation in ``spec`` into an :class:`Endpoint`."""
        endpoints: list[Endpoint] = []
        paths = spec.get("paths") or {}
        if not isinstance(paths, dict):
            return endpoints
        for path, path_item in paths.items():
            item = path_item
            if isinstance(item, dict) and "$ref" in item:
                item = resolve_refs(item, spec)
            if not isinstance(item, dict):
                continue
            for method, operation in item.items():
                if method.lower() not in HTTP_METHODS or not isinstance(operation, dict):
                    continue
                parameters = _iter_parameters(operation, item, spec)
                path_params = _path_param_names(str(path), parameters)
                endpoints.append(
                    Endpoint(
                        method=method.upper(),
                        path=str(path),
                        path_params=path_params,
                        object_id_params=[name for name in path_params if is_object_id_param(name)],
                        request_body_schema=_request_body_schema(operation, spec),
                        response_schema=_response_schema(operation, spec),
                        auth_required=_auth_required(operation, spec),
                    )
                )
        return endpoints

    def load_from_file(self, path: str | Path) -> list[Endpoint]:
        """Load a JSON or YAML spec from disk and normalize it."""
        text = Path(path).read_text(encoding="utf-8")
        return self.parse(_loads(text))

    def load_from_url(
        self,
        url: str,
        *,
        allowed_base_urls: Sequence[str] | None = None,
        timeout_seconds: float = 10.0,
    ) -> list[Endpoint]:
        """Fetch a spec over HTTP. Refuses hosts that are not allow-listed."""
        allow = list(allowed_base_urls) if allowed_base_urls is not None else default_allowlist()
        if not url_is_allowed(url, allow):
            raise AllowlistDeniedError(
                f"Refusing to fetch spec from {url} — not on the allow-list "
                f"({', '.join(allow)})."
            )
        with httpx.Client(timeout=timeout_seconds, follow_redirects=False) as client:
            response = client.get(url)
            response.raise_for_status()
            try:
                payload = response.json()
                if isinstance(payload, dict):
                    return self.parse(payload)
            except json.JSONDecodeError:
                pass
            return self.parse(_loads(response.text))


def bola_candidates(endpoints: Iterable[Endpoint]) -> list[Endpoint]:
    """Filter endpoints whose path takes an object identifier."""
    return [endpoint for endpoint in endpoints if endpoint.is_bola_candidate]
