"""Spec parser and allow-list sanity tests against ShopAPI."""

from __future__ import annotations

from pathlib import Path

import pytest

from sentinel_core.http_client import AllowlistDeniedError, SafeClient
from sentinel_core.identity import IdentityProvider
from sentinel_core.spec_parser import SpecParser, bola_candidates

SCANNER_ROOT = Path(__file__).resolve().parent.parent
FIXTURE = Path(__file__).resolve().parent / "fixtures" / "shopapi.openapi.json"
IDENTITIES = SCANNER_ROOT / "configs" / "shopapi.identities.yaml"
LIVE_SPEC = "http://127.0.0.1:8000/openapi.json"


def _load_shopapi_endpoints() -> list:
    """Prefer the saved fixture; fall back to the live ShopAPI spec."""
    parser = SpecParser()
    if FIXTURE.is_file():
        return parser.load_from_file(FIXTURE)
    return parser.load_from_url(LIVE_SPEC)


def test_shopapi_detects_bola_candidates() -> None:
    """`/users/{user_id}` and `/orders/{order_id}` are object-id endpoints."""
    endpoints = _load_shopapi_endpoints()
    by_key = {endpoint.key: endpoint for endpoint in endpoints}

    users = by_key["GET /users/{user_id}"]
    orders = by_key["GET /orders/{order_id}"]
    assert users.object_id_params == ["user_id"]
    assert orders.object_id_params == ["order_id"]
    assert users.is_bola_candidate and orders.is_bola_candidate
    assert users.auth_required and orders.auth_required

    patch_users = by_key["PATCH /users/{user_id}"]
    assert patch_users.is_bola_candidate
    assert patch_users.request_body_schema is not None
    assert "is_admin" in (patch_users.request_body_schema.get("properties") or {})

    candidate_paths = {endpoint.path for endpoint in bola_candidates(endpoints)}
    assert "/users/{user_id}" in candidate_paths
    assert "/orders/{order_id}" in candidate_paths


def test_shopapi_safe_endpoints_are_not_bola_candidates() -> None:
    """Public catalog and healthz have no object-id path params."""
    endpoints = _load_shopapi_endpoints()
    by_key = {endpoint.key: endpoint for endpoint in endpoints}

    products = by_key["GET /products"]
    healthz = by_key["GET /healthz"]
    assert products.object_id_params == []
    assert healthz.object_id_params == []
    assert not products.is_bola_candidate
    assert not healthz.is_bola_candidate
    assert products.auth_required is False
    assert healthz.auth_required is False


def test_object_id_param_rules() -> None:
    """`id` and `*_id` are candidates; other path params are not."""
    spec = {
        "openapi": "3.0.0",
        "paths": {
            "/items/{id}": {
                "get": {
                    "parameters": [{"name": "id", "in": "path", "required": True}],
                    "responses": {"200": {"description": "ok"}},
                }
            },
            "/widgets/{widget_id}": {
                "get": {
                    "parameters": [{"name": "widget_id", "in": "path", "required": True}],
                    "responses": {"200": {"description": "ok"}},
                }
            },
            "/search/{query}": {
                "get": {
                    "parameters": [{"name": "query", "in": "path", "required": True}],
                    "responses": {"200": {"description": "ok"}},
                }
            },
        },
    }
    endpoints = SpecParser().parse(spec)
    by_path = {endpoint.path: endpoint for endpoint in endpoints}
    assert by_path["/items/{id}"].object_id_params == ["id"]
    assert by_path["/widgets/{widget_id}"].object_id_params == ["widget_id"]
    assert by_path["/search/{query}"].object_id_params == []


@pytest.mark.asyncio
async def test_safe_client_refuses_non_allowlisted_host() -> None:
    """SafeClient must never contact a host that is not on the allow-list."""
    async with SafeClient(allowed_base_urls=["http://127.0.0.1:8000"]) as client:
        with pytest.raises(AllowlistDeniedError, match="not on the configured allow-list"):
            await client.request("GET", "https://example.com/secret")
        with pytest.raises(AllowlistDeniedError):
            await client.request("GET", "http://127.0.0.1:8001/orders/1")
        with pytest.raises(AllowlistDeniedError):
            await client.request("GET", "http://127.0.0.1:8000.evil.com/")


def test_identity_matrix_shopapi_ground_truth() -> None:
    """Alice owns 101/102; a later detector can pick Bob's 201 as foreign."""
    provider = IdentityProvider.from_file(IDENTITIES)
    assert provider.authed_headers("alice") == {"Authorization": "Bearer tok_alice"}
    assert provider.authed_headers("anonymous") == {}
    assert provider.owned_ids("alice", "order") == [101, 102]
    assert provider.pick_owned("bob", "order") == 201
    cases = provider.cross_access_cases("order")
    alice_reads_bob = [
        case
        for case in cases
        if case.attacker.name == "alice" and case.owner.name == "bob"
    ]
    assert {case.object_id for case in alice_reads_bob} == {201, 202}
