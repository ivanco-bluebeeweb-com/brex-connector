"""Generic entity layer + explicit writes for Brex Connector.

list_entities/get_entity cover the bulk read surface (cards, transactions,
users, expenses, budgets, departments, locations). Writes are explicit,
narrow chat functions (not generic create/update) because Brex's write
surface is intentionally small and each write has distinct real-world
consequences (money movement, access changes).
"""
from __future__ import annotations

from imperal_sdk import ActionResult

import brex_client as bc
from app import chat
from handlers_connection import resolve_or_error
from schemas import (
    ListEntitiesParams, EntityList,
    GetEntityParams, EntityDetail,
    CreateExpenseParams, UpdateUserParams, SetCardStatusParams, WriteResult,
)


@chat.function(
    "list_entities",
    "List Brex records of any resource type (cards, transactions, users, expenses, budgets, departments, "
    "locations) in the connected Brex account.",
    action_type="read", chain_callable=True, data_model=EntityList,
)
async def list_entities(ctx, params: ListEntitiesParams) -> ActionResult:
    """List Brex records of any resource type."""
    conn, err = await resolve_or_error(ctx, params.connection_id)
    if not conn:
        return err
    if params.entity not in bc.known_entities():
        return ActionResult.error(
            f"Unknown entity '{params.entity}'. Known: {', '.join(bc.known_entities())}",
            code="BREX_VALIDATION_FAILED",
        )
    query = {"limit": params.limit}
    if params.filter_expr:
        for pair in params.filter_expr.split("&"):
            if "=" in pair:
                k, v = pair.split("=", 1)
                query[k] = v
    data = await bc.request(ctx, conn, "GET", bc.entity_path(params.entity), params=query, action=f"list {params.entity}")
    records = data.get("items", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
    return ActionResult.success(EntityList(entity=params.entity, count=len(records), records=records), summary="Entities listed.")


@chat.function(
    "get_entity",
    "Read one Brex record of any resource type in full by its id.",
    action_type="read", chain_callable=True, data_model=EntityDetail,
)
async def get_entity(ctx, params: GetEntityParams) -> ActionResult:
    """Read one Brex record by id."""
    conn, err = await resolve_or_error(ctx, params.connection_id)
    if not conn:
        return err
    if params.entity not in bc.known_entities():
        return ActionResult.error(
            f"Unknown entity '{params.entity}'. Known: {', '.join(bc.known_entities())}",
            code="BREX_VALIDATION_FAILED",
        )
    record = await bc.request(ctx, conn, "GET", bc.entity_path(params.entity, params.record_id), action=f"get {params.entity}")
    return ActionResult.success(EntityDetail(entity=params.entity, record=record if isinstance(record, dict) else {}), summary="Entity retrieved.")


@chat.function(
    "create_expense",
    "Create a new expense entry for a Brex user -- an out-of-pocket cost tracked against their account.",
    action_type="write", chain_callable=True, data_model=WriteResult,
    event="brex-connector.create_expense", effects=["create:expense"],
)
async def create_expense(ctx, params: CreateExpenseParams) -> ActionResult:
    """Create a new Brex expense."""
    conn, err = await resolve_or_error(ctx, params.connection_id)
    if not conn:
        return err
    body = {
        "user_id": params.user_id,
        "amount": {"amount": int(round(params.amount * 100)), "currency": params.currency},
        "memo": params.memo,
    }
    result = await bc.request(ctx, conn, "POST", "/v1/expenses", json_body=body, action="create expense")
    return ActionResult.success(WriteResult(ok=True, record_id=(result or {}).get("id", "")), summary="Expense created.")


@chat.function(
    "update_user",
    "Update an existing Brex user's department. Only given fields change.",
    action_type="write", chain_callable=True, data_model=WriteResult,
    event="brex-connector.update_user", effects=["update:user"],
)
async def update_user(ctx, params: UpdateUserParams) -> ActionResult:
    """Update a Brex user's department."""
    conn, err = await resolve_or_error(ctx, params.connection_id)
    if not conn:
        return err
    body = {}
    if params.department_id:
        body["department_id"] = params.department_id
    if not body:
        return ActionResult.error("Nothing to update -- provide department_id.", code="BREX_VALIDATION_FAILED")
    await bc.request(ctx, conn, "PATCH", f"/v2/users/{params.user_id}", json_body=body, action="update user")
    return ActionResult.success(WriteResult(ok=True, record_id=params.user_id), summary="User updated.")


@chat.function(
    "set_card_status",
    "Suspend or unsuspend a Brex card -- blocks/restores its ability to make new purchases.",
    action_type="write", chain_callable=True, data_model=WriteResult,
    event="brex-connector.set_card_status", effects=["update:card"],
)
async def set_card_status(ctx, params: SetCardStatusParams) -> ActionResult:
    """Suspend or unsuspend a Brex card."""
    conn, err = await resolve_or_error(ctx, params.connection_id)
    if not conn:
        return err
    status = "SUSPENDED" if params.suspend else "ACTIVE"
    await bc.request(ctx, conn, "PATCH", f"/v1/cards/{params.card_id}", json_body={"status": status}, action="set card status")
    return ActionResult.success(WriteResult(ok=True, record_id=params.card_id), summary="Card status updated.")
