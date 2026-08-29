"""Connection management for Brex Connector: connect/disconnect/list.

Static Bearer user token -- verified synchronously against a harmless
read endpoint at connect time. No refresh logic needed (no expiry).
"""
from __future__ import annotations

import json
import uuid

from imperal_sdk import ActionResult

import brex_client as bc
from app import chat
from schemas import (
    NoParams,
    ConnectBrexParams,
    ProviderConnection, ProviderConnectionList,
    DisconnectBrexParams, DeleteResult,
)

_SECRET_NAME = "brex_connections"


async def _load_connections(ctx) -> list[dict]:
    raw = await ctx.secrets.get(_SECRET_NAME)
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except (TypeError, ValueError):
        return []
    return data if isinstance(data, list) else []


async def _save_connections(ctx, connections: list[dict]) -> None:
    await ctx.secrets.set(_SECRET_NAME, json.dumps(connections))


async def resolve_connection(ctx, connection_id: str = "") -> dict | None:
    connections = await _load_connections(ctx)
    if not connections:
        return None
    if connection_id:
        for c in connections:
            if c.get("id") == connection_id:
                return c
        return None
    return connections[0]


async def resolve_or_error(ctx, connection_id: str = ""):
    conn = await resolve_connection(ctx, connection_id)
    if not conn:
        return None, ActionResult.error(
            "No Brex connection found. Connect Brex first.",
            code="BREX_NOT_CONNECTED",
        )
    return conn, None


@chat.function(
    "connect_brex",
    "Connect your own Brex account by saving your admin-generated user token (from dashboard.brex.com > "
    "Developer Settings), after checking it actually works.",
    action_type="write", chain_callable=True, data_model=ProviderConnection,
    event="brex-connector.connect_brex", effects=["create:connection"],
)
async def connect_brex(ctx, params: ConnectBrexParams) -> ActionResult:
    """Verify the user token and save the connection."""
    if not params.user_token:
        return ActionResult.error("user_token is required.", code="BREX_VALIDATION_FAILED")
    result = await bc.verify_token(params.user_token)
    if not result.get("ok"):
        return ActionResult.error(result.get("message", "Could not verify Brex token."),
                                   code=result.get("code", "BREX_UNAUTHORIZED"))
    connections = await _load_connections(ctx)
    conn_id = str(uuid.uuid4())
    connections.append({
        "id": conn_id,
        "label": params.label or "Brex",
        "user_token": params.user_token,
    })
    await _save_connections(ctx, connections)
    return ActionResult.ok(ProviderConnection(id=conn_id, label=params.label or "Brex"))


@chat.function(
    "list_connections",
    "List the connected Brex accounts.",
    action_type="read", chain_callable=True, data_model=ProviderConnectionList,
)
async def list_connections(ctx, params: NoParams) -> ActionResult:
    """List all saved Brex connections (labels only, never tokens)."""
    connections = await _load_connections(ctx)
    return ActionResult.ok(ProviderConnectionList(
        connections=[ProviderConnection(id=c.get("id", ""), label=c.get("label", "Brex")) for c in connections]
    ))


@chat.function(
    "disconnect_brex",
    "Disconnect a Brex account: deletes the saved user token. Nothing in Brex itself is changed.",
    action_type="write", chain_callable=True, data_model=DeleteResult,
    event="brex-connector.disconnect_brex", effects=["delete:connection"],
)
async def disconnect_brex(ctx, params: DisconnectBrexParams) -> ActionResult:
    """Disconnect a Brex account: deletes the saved connection."""
    connections = await _load_connections(ctx)
    remaining = [c for c in connections if c.get("id") != params.connection_id]
    if len(remaining) == len(connections):
        return ActionResult.error("Connection not found.", code="BREX_NOT_CONNECTED")
    await _save_connections(ctx, remaining)
    return ActionResult.ok(DeleteResult(deleted=True, id=params.connection_id))
