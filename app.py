"""Extension declaration, secrets, lifecycle hooks.

WHY BYOK, same reasoning as every other connector here -- the user's own
Brex company's card/transaction/spend data lives inside THEIR OWN Brex
account.

WHY A STATIC USER TOKEN, NOT OAUTH (confirmed against developer.brex.com/
guides/authentication, 2026-08-29): standard Brex client API access uses a
Bearer user token generated once by an account admin from dashboard.brex.com
Developer Settings -- no token exchange, no expiry. Brex's OAuth2 Client
Credentials flow exists but is for Brex's own DEVELOPER PARTNERS building
onboarding/referral integrations, not standard per-client access.

WHY BILL PAY IS OUT OF SCOPE THIS RELEASE. Brex Bill Pay (vendor invoice AP
automation) is a separate product surface with its own permission grants
not universally enabled on every Brex account -- flagged as an explicit v2
follow-up in PREPARATION.md, matching the same call made for Ramp
Connector's Bill Pay exclusion.
"""
from __future__ import annotations

from imperal_sdk import ChatExtension, Extension

ext = Extension(
    "brex-connector",
    version="0.1.0",
    display_name="Brex",
    icon="icon.svg",
    capabilities=["brex:read", "brex:write"],
    description=(
        "Connect your own Brex account (bring your own admin-generated user token from dashboard.brex.com "
        "Developer Settings) to read cards, transactions, users, expenses, budgets, departments, and locations, "
        "plus value-add spend and card-utilization reports. Expense creation, user department updates, and card "
        "suspend/unsuspend are supported. Bill Pay (vendor invoices) is out of scope this release."
    ),
)

chat = ChatExtension(ext)


@ext.health_check
async def health_check(ctx):
    raw = await ctx.secrets.get("brex_connections")
    return {"ok": True, "has_connections": bool(raw)}
