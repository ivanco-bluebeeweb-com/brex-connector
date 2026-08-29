"""Panel UI -- connections list/connect form + the one required "App
settings" entry point, same shape as every other connector this
session's panels.py.

SIDEBAR CONTENT -- NO CARDS ANYWHERE, per ~/UI_INTERFACE_STANDARD.md's
"left sidebar, no decorated cards" rule. Disconnect lives only in the
"App settings" screen (panels_settings.py). The one secondary "App
settings" button is always the LAST element at the bottom of the sidebar.

PER ~/UI_INTERFACE_STANDARD.md (2026-08-21 addendum): every Input carries
its own visible label (a ui.Text wrapping the ui.Input in a Stack -- ui.Input
itself does not accept label=), the placeholder text is always contextually
specific. The "How do I set this up?" instructions live ONLY in the help
overlay below -- never duplicated as static sidebar text.

KNOWN UI COMPONENT PITFALLS (learned building Ramp Connector 2026-08-29):
ui.Form does NOT take a separate ui.Button(submit=True) child -- use
submit_label="..." on ui.Form itself. ui.Input does NOT accept secret=True
-- use ui.Password(param_name=..., placeholder=...) instead.
"""
from __future__ import annotations

from imperal_sdk import ui

from app import ext
import handlers_connection as h


def _settings_button() -> ui.UINode:
    return ui.Button(
        "App settings", variant="secondary", size="sm", full_width=True,
        icon="settings", on_click=ui.Call("__panel__brex_settings"),
    )


def _connection_row(c: dict) -> ui.UINode:
    label = c.get("label") or "Brex connection"
    return ui.Stack(direction="v", gap=1, children=[
        ui.Text(label, variant="body"),
        ui.Text("Connected", variant="caption"),
    ])


def _connections_section(connections: list[dict]) -> ui.UINode:
    if not connections:
        return ui.Text("No Brex accounts connected yet.", variant="caption")
    children: list[ui.UINode] = []
    for i, c in enumerate(connections):
        if i > 0:
            children.append(ui.Divider())
        children.append(_connection_row(c))
    return ui.Stack(direction="v", gap=2, children=children)


def _connect_section() -> ui.UINode:
    return ui.Stack(direction="v", gap=3, children=[
        ui.Form(
            action="connect_brex",
            submit_label="Connect Brex",
            children=[
                ui.Stack(direction="v", gap=1, children=[
                    ui.Text("User token", variant="label"),
                    ui.Password(param_name="user_token", placeholder="Paste your Brex user token (Developer Settings)"),
                ]),
                ui.Stack(direction="v", gap=1, children=[
                    ui.Text("Label (optional)", variant="label"),
                    ui.Input(param_name="label", placeholder="e.g. Acme Inc Brex"),
                ]),
            ],
        ),
        ui.Button(
            "How do I set this up?", variant="ghost", size="sm", full_width=True,
            on_click=ui.Call("__panel__brex_connect_help"),
        ),
    ])


@ext.panel("brex_connect", slot="left", title="Brex")
async def brex_connect(ctx, **kwargs) -> object:
    connections = await h._load_connections(ctx)
    return ui.Stack(direction="v", gap=3, children=[
        _connections_section(connections),
        ui.Divider(),
        _connect_section(),
        _settings_button(),
    ])


@ext.panel("brex_connect_help", slot="overlay", title="How do I set this up?")
async def brex_connect_help(ctx, **kwargs) -> object:
    return ui.Stack(direction="v", gap=2, children=[
        ui.Text("1. Sign in to dashboard.brex.com as an account admin.", variant="body"),
        ui.Text("2. Go to Settings > Developer, and generate a User Token.", variant="body"),
        ui.Text("3. Copy the token and paste it here -- it never expires unless you revoke it.", variant="body"),
        ui.Text("Note: some endpoints require the token to belong to an account admin.", variant="caption"),
    ])
