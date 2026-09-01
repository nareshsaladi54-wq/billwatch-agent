"""Deterministic bill analysis. No LLM, no network. Every correctness claim
BillWatch makes is decided here and covered by tests/."""
from __future__ import annotations

import json
import statistics
from datetime import date, timedelta

from .config import DATA_DIR

SPIKE_RATIO = 1.6          # a charge this many x its typical amount is "unusual"
CREEP_RATIO = 1.15         # a subscription now >15% above its early median has "crept"
DUP_WINDOW_DAYS = 4        # identical merchant+amount within N days = likely duplicate
STALE_SUBSCRIPTION_DAYS = 60  # subscription unused this long is a cancel candidate


def _load(name: str) -> dict:
    with open(DATA_DIR / name) as fh:
        return json.load(fh)


def load_bills() -> list[dict]:
    return _load("bills.json")["bills"]


def load_transactions() -> list[dict]:
    return _load("transactions.json")["transactions"]


def _iso(d) -> date:
    return d if isinstance(d, date) else date.fromisoformat(d)


def next_due_date(bill: dict, today: date) -> date:
    """The next occurrence of due_day on or after today."""
    day = min(bill["due_day"], 28)
    candidate = today.replace(day=day)
    if candidate < today:
        month = candidate.month % 12 + 1
        year = candidate.year + (1 if candidate.month == 12 else 0)
        candidate = candidate.replace(year=year, month=month)
    return candidate


def _paid_this_cycle(bill: dict, today: date) -> bool:
    """True if last_paid falls within the current billing cycle (this month's window)."""
    last_paid = bill.get("last_paid")
    if not last_paid:
        return False
    due = next_due_date(bill, today)
    # paid "this cycle" only if the payment is close to the upcoming due date;
    # a payment ~a month before it belongs to the previous cycle.
    return _iso(last_paid) >= due - timedelta(days=20)


def payment_risks(bills: list[dict], today: date) -> list[dict]:
    """Bills that need a human to act: not autopay, unpaid this cycle, and the
    due date (plus grace) lands inside the next 7 days."""
    out = []
    for b in bills:
        if b.get("autopay"):
            continue
        if _paid_this_cycle(b, today):
            continue
        due = next_due_date(b, today)
        deadline = due + timedelta(days=b.get("grace_days", 0))
        days_left = (due - today).days
        if days_left <= 14:
            out.append({
                "id": b["id"], "name": b["name"], "due_date": due.isoformat(),
                "days_until_due": days_left, "hard_deadline": deadline.isoformat(),
                "amount_expected": b["typical_amount"], "late_fee": b.get("late_fee", 0.0),
            })
    return sorted(out, key=lambda r: r["days_until_due"])


def charge_anomalies(bills: list[dict], txns: list[dict]) -> list[dict]:
    by_id = {b["id"]: b for b in bills}
    out = []

    # spikes vs the bill's typical amount
    for t in txns:
        b = by_id.get(t.get("bill_id"))
        if b and t["amount"] >= b["typical_amount"] * SPIKE_RATIO:
            out.append({
                "kind": "spike", "date": t["date"], "merchant": t["merchant"],
                "amount": t["amount"], "typical": b["typical_amount"],
                "multiple": round(t["amount"] / b["typical_amount"], 2),
            })

    # duplicates: same merchant + amount within DUP_WINDOW_DAYS
    seen: dict[tuple, str] = {}
    for t in sorted(txns, key=lambda x: x["date"]):
        key = (t["merchant"], round(t["amount"], 2))
        prev = seen.get(key)
        if prev and (_iso(t["date"]) - _iso(prev)).days <= DUP_WINDOW_DAYS:
            out.append({
                "kind": "duplicate", "date": t["date"], "merchant": t["merchant"],
                "amount": t["amount"], "first_seen": prev,
            })
        seen[key] = t["date"]

    # charges with no matching known bill
    for t in txns:
        if not t.get("bill_id"):
            if not any(o["kind"] == "duplicate" and o["merchant"] == t["merchant"] for o in out):
                out.append({
                    "kind": "unrecognized", "date": t["date"],
                    "merchant": t["merchant"], "amount": t["amount"],
                })
    return out


def price_creep(bills: list[dict]) -> list[dict]:
    out = []
    for b in bills:
        if b["category"] != "subscription":
            continue
        hist = b.get("history", [])
        if len(hist) < 4:
            continue
        baseline = statistics.median(hist[: max(2, len(hist) // 2)])
        current = hist[-1]
        if baseline and current >= baseline * CREEP_RATIO:
            out.append({
                "id": b["id"], "name": b["name"], "from": baseline, "to": current,
                "increase_pct": round((current / baseline - 1) * 100, 1),
                "annual_extra": round((current - baseline) * 12, 2),
            })
    return out


def stale_subscriptions(bills: list[dict], today: date) -> list[dict]:
    out = []
    for b in bills:
        if b["category"] != "subscription":
            continue
        last_used = b.get("last_used")
        if not last_used:
            continue
        idle = (today - _iso(last_used)).days
        if idle >= STALE_SUBSCRIPTION_DAYS:
            out.append({
                "id": b["id"], "name": b["name"], "days_idle": idle,
                "monthly_amount": b["typical_amount"],
                "annual_waste": round(b["typical_amount"] * 12, 2),
            })
    return sorted(out, key=lambda r: -r["days_idle"])


def scan(today: date | None = None) -> dict:
    today = today or date.today()
    bills, txns = load_bills(), load_transactions()
    risks = payment_risks(bills, today)
    anomalies = charge_anomalies(bills, txns)
    creep = price_creep(bills)
    stale = stale_subscriptions(bills, today)
    actionable = bool(risks or anomalies or creep or stale)
    return {
        "as_of": today.isoformat(),
        "needs_attention": actionable,
        "payment_risks": risks,
        "charge_anomalies": anomalies,
        "price_creep": creep,
        "stale_subscriptions": stale,
        "monthly_subscription_spend": round(
            sum(b["typical_amount"] for b in bills if b["category"] == "subscription"), 2
        ),
    }
