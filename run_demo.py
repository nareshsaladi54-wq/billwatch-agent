#!/usr/bin/env python3
"""No-model demo: run the deterministic core and print what BillWatch would
surface. Proves the correctness layer works with zero Bedrock calls."""
import json
from datetime import date

from billwatch import core

if __name__ == "__main__":
    result = core.scan(date(2026, 9, 1))
    print(json.dumps(result, indent=2))
    print("\n--- what the agent would say ---")
    if not result["needs_attention"]:
        print("All bills on track. Nothing to do.")
    for r in result["payment_risks"]:
        print(f"ACT: {r['name']} - ${r['amount_expected']:.2f} due {r['due_date']} "
              f"({r['days_until_due']}d), not autopay, ${r['late_fee']:.2f} late fee.")
    for a in result["charge_anomalies"]:
        print(f"CHECK: {a['kind']} - {a['merchant']} ${a['amount']:.2f} on {a['date']}.")
    for c in result["price_creep"]:
        print(f"FYI: {c['name']} up {c['increase_pct']}% "
              f"(${c['from']:.2f} -> ${c['to']:.2f}), ${c['annual_extra']:.2f}/yr.")
    for s in result["stale_subscriptions"]:
        print(f"FYI: {s['name']} unused {s['days_idle']}d, ${s['annual_waste']:.2f}/yr.")
