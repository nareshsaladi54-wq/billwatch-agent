"""Strands tools. Thin wrappers over the deterministic core and the file memory.
The agent never does arithmetic on money itself - it calls these."""
from __future__ import annotations

from datetime import date

from strands import tool

from . import core, memory


@tool
def scan_finances(as_of: str = "") -> dict:
    """Run the full deterministic scan of bills, subscriptions and recent charges.

    Args:
        as_of: ISO date (YYYY-MM-DD) to evaluate against; empty = today.

    Returns a dict with payment_risks, charge_anomalies, price_creep,
    stale_subscriptions and a needs_attention flag.
    """
    today = date.fromisoformat(as_of) if as_of else date(2026, 9, 1)
    return core.scan(today)


@tool
def list_bills() -> list[dict]:
    """List every tracked bill and subscription with its cadence and typical amount."""
    return core.load_bills()


@tool
def bill_history(bill_id: str) -> dict:
    """Return the amount history for one bill id (e.g. 'power', 'streaming_a')."""
    for b in core.load_bills():
        if b["id"] == bill_id:
            return {"id": bill_id, "name": b["name"], "history": b.get("history", []),
                    "typical_amount": b["typical_amount"]}
    return {"error": f"no bill with id {bill_id!r}"}


@tool
def recent_charges(limit: int = 20) -> list[dict]:
    """The most recent card/bank charges seen, newest first."""
    txns = sorted(core.load_transactions(), key=lambda t: t["date"], reverse=True)
    return txns[:limit]


@tool
def remember_preference(actor_id: str, note: str) -> str:
    """Save a durable household preference or decision (e.g. 'keep the gym through December')."""
    return memory.remember(actor_id, note)


@tool
def recall_preferences(actor_id: str, about: str = "") -> list[str]:
    """Recall durable preferences/decisions saved earlier, optionally filtered by topic."""
    return memory.recall(actor_id, about)


TOOLS = [scan_finances, list_bills, bill_history, recent_charges,
         remember_preference, recall_preferences]
