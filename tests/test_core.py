"""Deterministic tests - no model, no network."""
from datetime import date

from billwatch import core

TODAY = date(2026, 9, 1)


def test_scan_flags_attention():
    r = core.scan(TODAY)
    assert r["needs_attention"] is True


def test_power_bill_is_a_payment_risk():
    # power: due_day 12, not autopay, last_paid 2026-08-11 (previous cycle)
    risks = {r["id"] for r in core.payment_risks(core.load_bills(), TODAY)}
    assert "power" in risks


def test_autopay_bills_are_not_payment_risks():
    risks = {r["id"] for r in core.payment_risks(core.load_bills(), TODAY)}
    assert "water" not in risks and "internet" not in risks


def test_power_spike_detected():
    an = core.charge_anomalies(core.load_bills(), core.load_transactions())
    spikes = [a for a in an if a["kind"] == "spike"]
    assert any(a["merchant"] == "City Power & Light" for a in spikes)


def test_duplicate_storage_charge_detected():
    an = core.charge_anomalies(core.load_bills(), core.load_transactions())
    assert any(a["kind"] == "duplicate" and a["merchant"] == "BrightBox Storage" for a in an)


def test_streaming_a_price_creep():
    creep = {c["id"] for c in core.price_creep(core.load_bills())}
    assert "streaming_a" in creep


def test_stale_subscriptions_flag_gym_and_cloudtunes():
    stale = {s["id"] for s in core.stale_subscriptions(core.load_bills(), TODAY)}
    assert {"gym", "streaming_b"}.issubset(stale)
    assert "streaming_a" not in stale  # used 2 days ago


def test_next_due_date_rolls_forward():
    bill = {"due_day": 1}
    assert core.next_due_date(bill, date(2026, 9, 15)) == date(2026, 10, 1)


def test_quiet_when_nothing_wrong(tmp_path, monkeypatch):
    # a world where the only bill is autopay and current
    clean = {"as_of": "2026-09-01", "bills": [{
        "id": "x", "name": "X", "category": "utility", "cadence": "monthly",
        "due_day": 20, "grace_days": 5, "late_fee": 0.0, "autopay": True,
        "typical_amount": 10.0, "last_paid": "2026-08-25", "history": [10, 10, 10, 10]}]}
    (tmp_path / "bills.json").write_text(__import__("json").dumps(clean))
    (tmp_path / "transactions.json").write_text('{"as_of":"2026-09-01","transactions":[]}')
    monkeypatch.setattr(core, "DATA_DIR", tmp_path)
    assert core.scan(TODAY)["needs_attention"] is False
