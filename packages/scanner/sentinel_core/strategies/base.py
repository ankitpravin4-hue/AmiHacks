"""Test-case generation strategies. Rule-based today; LLM later."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from sentinel_core.detectors.helpers import (
    is_auth_sensitive,
    is_bola_probe,
    is_public_ops,
    looks_like_login,
    looks_like_update,
    privileged_body_fields,
)
from sentinel_core.detectors.rate_limit import PROBE_BODY
from sentinel_core.models import Endpoint


@dataclass
class TestCase:
    """One planned probe against an endpoint.

    ``identity_name`` is a role hint (``non-owner``, ``customer``,
    ``anonymous``) — the engine still resolves real tokens via IdentityProvider.
    """

    method: str
    path: str
    params: dict[str, Any] = field(default_factory=dict)
    body: Any | None = None
    identity_name: str = ""
    rationale: str = ""


@runtime_checkable
class TestStrategy(Protocol):
    """How the scanner decides *which* requests to try.

    Detectors still execute the probes. Swapping the strategy later (heuristic
    → LLM) should not require rewriting ScanEngine.
    """

    name: str

    def generate_test_cases(self, endpoint: Endpoint) -> list[TestCase]:
        """Return the probes this strategy would run for ``endpoint``."""
        ...


class HeuristicStrategy:
    """Default strategy: the same targeting rules the Phase 3 detectors use.

    Cases are generated so the existing logic is reachable through
    ``TestStrategy``. Scan behavior stays identical — detectors still decide
    what to send.
    """

    name = "heuristic"

    def generate_test_cases(self, endpoint: Endpoint) -> list[TestCase]:
        """Mirror BOLA, data-exposure, auth, rate-limit, and mass-assignment gates."""
        cases: list[TestCase] = []
        if is_bola_probe(endpoint):
            cases.append(
                TestCase(
                    method=endpoint.method,
                    path=endpoint.path,
                    params={name: f"{{{name}}}" for name in endpoint.object_id_params},
                    identity_name="non-owner",
                    rationale="Cross-identity object access (BOLA).",
                )
            )
        if endpoint.method == "GET" and not is_public_ops(endpoint):
            cases.append(
                TestCase(
                    method="GET",
                    path=endpoint.path,
                    params={name: f"{{{name}}}" for name in endpoint.object_id_params},
                    identity_name="customer",
                    rationale="Read own object and inspect the JSON for sensitive keys.",
                )
            )
        if is_auth_sensitive(endpoint):
            cases.append(
                TestCase(
                    method=endpoint.method,
                    path=endpoint.path,
                    params={name: f"{{{name}}}" for name in endpoint.path_params},
                    identity_name="anonymous",
                    rationale="Call a protected or /admin route with no credentials.",
                )
            )
        if looks_like_login(endpoint):
            cases.append(
                TestCase(
                    method=endpoint.method,
                    path=endpoint.path,
                    body=dict(PROBE_BODY),
                    identity_name="anonymous",
                    rationale="Capped burst against a credential endpoint (no 429 expected).",
                )
            )
        if looks_like_update(endpoint):
            privileged = privileged_body_fields(endpoint)
            if privileged:
                field = "is_admin" if "is_admin" in privileged else next(iter(privileged))
                cases.append(
                    TestCase(
                        method=endpoint.method,
                        path=endpoint.path,
                        params={
                            name: f"{{{name}}}"
                            for name in (endpoint.object_id_params or endpoint.path_params)
                        },
                        body={field: True},
                        identity_name="customer",
                        rationale=f"Mass-assign privileged field `{field}` as a non-admin.",
                    )
                )
        return cases


class LLMTestStrategy:
    """Stub: smarter test-case generation from the endpoint spec.

    # TODO(ai): Ask an LLM to reason about likely authorization flaws from the
    endpoint's OpenAPI description, parameters, and schemas, then return
    ``TestCase`` rows (identities, object ids, bodies) that go beyond the
    fixed heuristic matrix. No provider call happens here — this class must
    stay a stub until an AI phase is explicitly approved.
    """

    name = "llm"

    def generate_test_cases(self, endpoint: Endpoint) -> list[TestCase]:
        """Not implemented — reserved for a future LLM planner."""
        raise NotImplementedError(
            "# TODO(ai): LLMTestStrategy.generate_test_cases will ask an LLM "
            f"to propose authorization-aware probes for {endpoint.key}. "
            "No provider is wired."
        )
