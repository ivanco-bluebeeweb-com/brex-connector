# Brex Connector -- Preparation (v0.1)

## API surface
Brex API (platform.brexapis.com) -- standard REST/JSON, resources: cards,
transactions (card + cash), users, expenses, budgets, departments,
locations, bill pay (vendor invoices). Confirmed via developer.brex.com
(2026-08-29).

## Auth model
Static **user token** (NOT OAuth2 for standard client use) -- confirmed via
developer.brex.com/guides/authentication: an admin generates a token from
dashboard.brex.com Developer Settings and passes it as a Bearer token in
every request's Authorization header. No token exchange, no expiry to
manage -- same simplicity class as Expensify's partner credentials.
(Brex ALSO offers an OAuth2 Client Credentials flow, but that's for Brex's
own developer PARTNERS building onboarding/referral integrations -- not
the standard per-client API access this connector targets.)

## Why BYOK
Same reasoning as every other connector here -- the user's own Brex
company's card/transaction/spend data lives inside THEIR OWN Brex
account. The user token is generated per Brex account by an account admin,
not a shared Imperal-wide credential.

## Scope for v1
Read-heavy: cards, transactions, users, expenses, budgets, departments,
locations. Write: create expense, update user (department), suspend/
unsuspend card. Bill Pay (vendor invoice AP automation) is a separate
Brex product surface with its own permission grants -- flagged as v2
follow-up rather than silently omitted, matching the same call made for
Ramp Connector's Bill Pay exclusion.

## Rate limits / known constraints
Brex enforces standard REST pagination (cursor-based) and per-endpoint
rate limits. Most APIs require the token to belong to an account admin --
documented in IDEAL_ONBOARDING.md as a known access-scope caveat.
