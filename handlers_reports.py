"""Value-add reports for Brex Connector -- spend overview and card
utilization, same "aggregate raw records into one glance" shape as
every other connector's handlers_reports.py this session.
"""
from __future__ import annotations

from imperal_sdk import ActionResult

import brex_client as bc
from app import chat
from handlers_connection import resolve_or_error
from schemas import (
    GetSpendOverviewParams, SpendOverviewReport,
    GetCardUtilizationReportParams, CardUtilizationReport,
)


@chat.function(
    "get_spend_overview_report",
    "Value-add report: summarize recent Brex transaction spend by category -- total spend and transaction count.",
    action_type="read", chain_callable=True, data_model=SpendOverviewReport,
)
async def get_spend_overview_report(ctx, params: GetSpendOverviewParams) -> ActionResult:
    """Scan recent transactions and bucket spend by category."""
    conn, err = await resolve_or_error(ctx, params.connection_id)
    if not conn:
        return err
    data = await bc.request(
        ctx, conn, "GET", "/v2/transactions/card/primary", params={"limit": params.limit},
        action="list transactions for spend overview",
    )
    rows = data.get("items", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
    total = 0.0
    by_category: dict[str, float] = {}
    for r in rows:
        amt = r.get("amount", {})
        value = (amt.get("amount", 0) or 0) / 100 if isinstance(amt, dict) else float(r.get("amount", 0) or 0)
        total += value
        cat = (r.get("merchant", {}) or {}).get("mcc_category") or r.get("category") or "Uncategorized"
        by_category[cat] = by_category.get(cat, 0.0) + value
    return ActionResult.ok(SpendOverviewReport(
        transaction_count=len(rows), total_spend=round(total, 2),
        by_category={k: round(v, 2) for k, v in by_category.items()},
    ))


@chat.function(
    "get_card_utilization_report",
    "Value-add report: scan Brex cards and flag active/suspended counts.",
    action_type="read", chain_callable=True, data_model=CardUtilizationReport,
)
async def get_card_utilization_report(ctx, params: GetCardUtilizationReportParams) -> ActionResult:
    """Scan Brex cards and summarize their status breakdown."""
    conn, err = await resolve_or_error(ctx, params.connection_id)
    if not conn:
        return err
    data = await bc.request(ctx, conn, "GET", "/v1/cards", params={"limit": params.limit}, action="list cards for utilization report")
    rows = data.get("items", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
    active = sum(1 for r in rows if (r.get("status") or "").upper() == "ACTIVE")
    suspended = sum(1 for r in rows if (r.get("status") or "").upper() == "SUSPENDED")
    return ActionResult.ok(CardUtilizationReport(total_cards=len(rows), active_cards=active, suspended_cards=suspended))
