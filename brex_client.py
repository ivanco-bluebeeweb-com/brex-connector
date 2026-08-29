"""Thin HTTP client for Brex API.

Static Bearer user token -- no OAuth, no token refresh at all. Same
"fail()-dict + ClientFail exception" shape as every other connector this
session's *_client.py.
"""
from __future__ import annotations

from typing import Any

import httpx

API_BASE = "https://platform.brexapis.com"

BREX_NOT_CONNECTED = "BREX_NOT_CONNECTED"
BREX_UNAUTHORIZED = "BREX_UNAUTHORIZED"
BREX_FORBIDDEN = "BREX_FORBIDDEN"
BREX_NOT_FOUND = "BREX_NOT_FOUND"
BREX_RATE_LIMITED = "BREX_RATE_LIMITED"
BREX_BACKEND_ERROR = "BREX_BACKEND_ERROR"
BREX_VALIDATION_FAILED = "BREX_VALIDATION_FAILED"

_MESSAGES = {
    BREX_NOT_CONNECTED: "No Brex connection found. Connect Brex first.",
    BREX_UNAUTHORIZED: "Brex rejected the user token as invalid.",
    BREX_FORBIDDEN: "Brex rejected this request -- the connected user token lacks the required admin permission.",
    BREX_NOT_FOUND: "That Brex record was not found.",
    BREX_RATE_LIMITED: "Brex rate-limited this request. Try again shortly.",
    BREX_BACKEND_ERROR: "Brex's API returned an error.",
    BREX_VALIDATION_FAILED: "Brex rejected the request as invalid.",
}


class ClientFail(Exception):
    def __init__(self, payload: dict):
        self.payload = payload
        super().__init__(payload.get("message", "Brex request failed"))


def fail(code: str, detail: str = "") -> dict:
    msg = _MESSAGES.get(code, "Brex request failed.")
    if detail:
        msg = f"{msg} ({detail})"
    return {"ok": False, "code": code, "message": msg}


async def verify_token(user_token: str) -> dict:
    """Verify a user token works by calling a harmless read endpoint."""
    if not user_token:
        return fail(BREX_VALIDATION_FAILED, "user_token is required")
    headers = {"Authorization": f"Bearer {user_token}"}
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            resp = await client.get(f"{API_BASE}/v2/users/me", headers=headers)
        except httpx.RequestError as e:
            return fail(BREX_BACKEND_ERROR, str(e))
    if resp.status_code == 401:
        return fail(BREX_UNAUTHORIZED)
    if resp.status_code == 403:
        return fail(BREX_FORBIDDEN)
    if resp.status_code >= 400:
        return fail(BREX_BACKEND_ERROR, f"HTTP {resp.status_code}")
    return {"ok": True}


def _check_status(resp: httpx.Response, action: str) -> Any:
    if resp.status_code == 401:
        raise ClientFail(fail(BREX_UNAUTHORIZED, action))
    if resp.status_code == 403:
        raise ClientFail(fail(BREX_FORBIDDEN, action))
    if resp.status_code == 404:
        raise ClientFail(fail(BREX_NOT_FOUND, action))
    if resp.status_code == 429:
        raise ClientFail(fail(BREX_RATE_LIMITED, action))
    if resp.status_code >= 400:
        raise ClientFail(fail(BREX_BACKEND_ERROR, f"HTTP {resp.status_code} on {action}"))
    if not resp.content:
        return {}
    try:
        return resp.json()
    except ValueError:
        raise ClientFail(fail(BREX_BACKEND_ERROR, f"non-JSON response on {action}"))


async def request(ctx, conn: dict, method: str, path: str, *, params: dict | None = None,
                   json_body: dict | None = None, action: str = "call Brex") -> Any:
    headers = {"Authorization": f"Bearer {conn.get('user_token', '')}"}
    url = f"{API_BASE}{path}"
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.request(method, url, headers=headers, params=params, json=json_body)
        except httpx.RequestError as e:
            raise ClientFail(fail(BREX_BACKEND_ERROR, str(e)))
    return _check_status(resp, action)


def known_entities() -> list[str]:
    return ["cards", "transactions", "users", "expenses", "budgets", "departments", "locations"]


def entity_path(entity: str, record_id: str = "") -> str:
    paths = {
        "cards": "/v2/cards",
        "transactions": "/v2/transactions/card/primary",
        "users": "/v2/users",
        "expenses": "/v1/expenses",
        "budgets": "/v2/budgets",
        "departments": "/v2/departments",
        "locations": "/v2/locations",
    }
    base = paths.get(entity, f"/v2/{entity}")
    return f"{base}/{record_id}" if record_id else base
