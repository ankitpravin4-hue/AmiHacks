"""Allow-listed, rate-capped async HTTP client for scanning."""

from __future__ import annotations

import asyncio
import json
import os
import time
from collections.abc import Mapping
from typing import Any
from urllib.parse import urlparse

import httpx

from sentinel_core.models import Evidence, RequestEvidence, ResponseEvidence

DEFAULT_ALLOWLIST: tuple[str, ...] = (
    "http://127.0.0.1:8000",
    "http://127.0.0.1:8010",
)
DESTRUCTIVE_METHODS: frozenset[str] = frozenset({"DELETE"})
SENSITIVE_HEADER_SUBSTR: tuple[str, ...] = (
    "authorization",
    "cookie",
    "token",
    "api-key",
    "apikey",
    "secret",
    "x-auth",
)
BODY_TRUNCATE_CHARS = 8192
RETRYABLE_STATUS = frozenset({429, 502, 503, 504})


class AllowlistDeniedError(PermissionError):
    """Raised when a request target is not on the configured allow-list."""


class UnsafeMethodError(PermissionError):
    """Raised when safe mode blocks a destructive HTTP method."""


def default_allowlist() -> list[str]:
    """Allow-list from `$ALLOWLIST` (comma-separated) or the local demo defaults."""
    raw = os.getenv("ALLOWLIST", ",".join(DEFAULT_ALLOWLIST))
    return [part.strip().rstrip("/") for part in raw.split(",") if part.strip()]


def url_is_allowed(url: str, allowed_base_urls: list[str] | tuple[str, ...]) -> bool:
    """Return True if `url` is under one of the allow-listed base URLs.

    Matching is scheme + host[:port] + path-prefix. A base of
    ``http://127.0.0.1:8000`` does **not** match ``https://127.0.0.1:8000``
    or ``http://127.0.0.1:8001`` or ``http://127.0.0.1:8000.evil.com``.
    """
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return False
    req_path = parsed.path or "/"
    for raw_base in allowed_base_urls:
        base = urlparse(raw_base)
        if parsed.scheme.lower() != base.scheme.lower():
            continue
        if parsed.netloc.lower() != base.netloc.lower():
            continue
        base_path = base.path.rstrip("/")
        if base_path == "" or req_path == base_path or req_path.startswith(base_path + "/"):
            return True
    return False


def redact_headers(headers: Mapping[str, str]) -> dict[str, str]:
    """Copy headers, replacing auth/token values with ``[REDACTED]``."""
    redacted: dict[str, str] = {}
    for key, value in headers.items():
        lowered = key.lower()
        if any(token in lowered for token in SENSITIVE_HEADER_SUBSTR):
            redacted[key] = "[REDACTED]"
        else:
            redacted[key] = value
    return redacted


def truncate_body(body: Any, limit: int = BODY_TRUNCATE_CHARS) -> str:
    """Serialize a body to text and cap its length."""
    if body is None:
        return ""
    if isinstance(body, (dict, list)):
        text = json.dumps(body, default=str)
    elif isinstance(body, bytes):
        text = body.decode("utf-8", errors="replace")
    else:
        text = str(body)
    extra = len(text) - limit
    if extra > 0:
        return f"{text[:limit]}...[truncated {extra} chars]"
    return text


class SafeClient:
    """Async HTTP client that will not leave the allow-list or flood a host.

    Parameters
    ----------
    allowed_base_urls:
        Only these origins (and their path prefixes) may be contacted.
    safe_mode:
        When True (default), refuse ``DELETE`` and other destructive methods.
    max_concurrency:
        Global cap on in-flight requests.
    requests_per_second:
        Per-host rate cap.
    timeout_seconds:
        Per-request timeout.
    max_retries:
        Extra attempts after retryable failures (total attempts = 1 + this).
    """

    def __init__(
        self,
        allowed_base_urls: list[str] | tuple[str, ...] | None = None,
        *,
        safe_mode: bool = True,
        max_concurrency: int = 5,
        requests_per_second: float = 10.0,
        timeout_seconds: float = 10.0,
        max_retries: int = 2,
    ) -> None:
        bases = [b.rstrip("/") for b in (allowed_base_urls or default_allowlist())]
        if not bases:
            raise ValueError("SafeClient requires a non-empty allow-list")
        self.allowed_base_urls = bases
        self.safe_mode = safe_mode
        self.max_retries = max_retries
        self._min_interval = 1.0 / requests_per_second if requests_per_second > 0 else 0.0
        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._host_locks: dict[str, asyncio.Lock] = {}
        self._last_request_at: dict[str, float] = {}
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout_seconds),
            follow_redirects=False,
        )

    async def __aenter__(self) -> SafeClient:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        """Close the underlying httpx client."""
        await self._client.aclose()

    def _assert_allowed(self, url: str) -> None:
        if not url_is_allowed(url, self.allowed_base_urls):
            allow = ", ".join(self.allowed_base_urls)
            raise AllowlistDeniedError(
                f"Refusing request to {url} — host is not on the configured "
                f"allow-list ({allow}). SentinelAPI never scans non-allow-listed targets."
            )

    def _assert_safe_method(self, method: str) -> None:
        if self.safe_mode and method.upper() in DESTRUCTIVE_METHODS:
            raise UnsafeMethodError(
                f"Safe mode is on — refusing destructive method {method.upper()}. "
                "Disable safe_mode only when you explicitly intend to send it."
            )

    async def _throttle(self, url: str) -> None:
        host = urlparse(url).netloc.lower()
        lock = self._host_locks.setdefault(host, asyncio.Lock())
        async with lock:
            if self._min_interval <= 0:
                return
            now = time.monotonic()
            wait = self._min_interval - (now - self._last_request_at.get(host, 0.0))
            if wait > 0:
                await asyncio.sleep(wait)
            self._last_request_at[host] = time.monotonic()

    async def request(
        self,
        method: str,
        url: str,
        *,
        headers: Mapping[str, str] | None = None,
        json: Any | None = None,
        content: bytes | str | None = None,
        params: Mapping[str, Any] | None = None,
        retry: bool = True,
    ) -> Evidence:
        """Send one request and return redacted evidence.

        Raises
        ------
        AllowlistDeniedError
            Target is not under an allow-listed base URL.
        UnsafeMethodError
            Safe mode blocked a destructive method.
        """
        method_u = method.upper()
        self._assert_allowed(url)
        self._assert_safe_method(method_u)
        header_map = dict(headers or {})

        response = await self._send(
            method_u, url, header_map, json, content, params, retry=retry
        )
        return Evidence(
            request=RequestEvidence(
                method=method_u,
                url=str(response.request.url),
                headers=redact_headers(header_map),
                body=json if json is not None else content,
            ),
            response=ResponseEvidence(
                status=response.status_code,
                body=truncate_body(response.text),
            ),
        )

    async def _send(
        self,
        method: str,
        url: str,
        headers: dict[str, str],
        json: Any,
        content: bytes | str | None,
        params: Mapping[str, Any] | None,
        retry: bool = True,
    ) -> httpx.Response:
        delay = 0.2
        last_error: Exception | None = None
        retries = self.max_retries if retry else 0
        for attempt in range(retries + 1):
            async with self._semaphore:
                await self._throttle(url)
                try:
                    response = await self._client.request(
                        method,
                        url,
                        headers=headers,
                        json=json,
                        content=content,
                        params=params,
                    )
                except httpx.TransportError as exc:
                    last_error = exc
                    if attempt >= retries:
                        raise
                    await asyncio.sleep(delay)
                    delay *= 2
                    continue
            if response.status_code in RETRYABLE_STATUS and attempt < retries:
                await asyncio.sleep(delay)
                delay *= 2
                continue
            return response
        if last_error is not None:
            raise last_error
        raise RuntimeError("SafeClient retry loop exited without a response")
