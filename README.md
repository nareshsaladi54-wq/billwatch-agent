# BillWatch

**A background agent that watches your household bills and subscriptions and
only pings you when a payment is genuinely at risk or a charge looks wrong.**

Track: **Everyday Agents** · Built with the [Strands Agents SDK](https://strandsagents.com) · Deploys to **Amazon Bedrock AgentCore**

---

## The problem

Money busywork is not hard, it is just relentless: a non-autopay bill sneaks up
and costs a late fee, a "temporary" promo price quietly doubles, a subscription
nobody has opened since spring keeps billing, a vendor double-charges and you
never notice. Watching for all of it every week is exactly the kind of dull,
repetitive vigilance a background agent should own.

BillWatch runs on a schedule, does the whole check, and stays silent unless
there is a real decision for you to make.

## What it does

Every run the agent:

1. Runs a **deterministic scan** (`scan_finances`) over your bills, their amount
   history, and recent charges.
2. Checks your **saved preferences** so it does not re-nag about things you have
   already decided.
3. Reports only what matters, most important first:
   | Signal | Example |
   |---|---|
   | **Payment risk** | "City Power $141 due Sept 12, not autopay, $18.50 late fee." |
   | **Charge anomaly** | spike (2x typical), duplicate charge, unrecognized merchant |
   | **Price creep** | "Streamly went $11.99 → $15.99, +$48/yr" |
   | **Stale subscription** | "Iron Yard Fitness unused 79 days, $468/yr" |
4. Offers to **remember** any decision you make so it never raises it again.

If nothing is off, the entire output is one sentence: everything is on track.

## Design principle: the LLM never touches the math

All money logic — due-date arithmetic, spike ratios, duplicate detection, price
creep, staleness — lives in `billwatch/core.py` and is covered by
`tests/test_core.py` (9 tests, no model, no network). The agent's job is
judgement and phrasing: which findings deserve a human, and how to say them
briefly. `python run_demo.py` runs the whole correctness layer with zero
Bedrock calls.

## Run it

```bash
make venv          # python3 -m venv .venv + deps
make test          # 9 deterministic tests
make demo          # no-model walkthrough of the scan
make agent         # one real turn against Bedrock (needs AWS creds + model access)
make serve         # AgentCore contract on localhost:8080
```

Live agent example:

```
$ make agent
Power bill spiked to $288.60 on Aug 29 — double your typical $141 — check for a
billing error or unusual usage.

Also: duplicate $89 BrightBox Storage charge (Aug 24 and Aug 26); unrecognized
$43.11 Corner Market on Aug 12. Streamly Premium is now $15.99 (+$48/yr).
CloudTunes and Iron Yard Fitness are unused 4+ months ($204 and $468/yr).
```

## Deploy to Amazon Bedrock AgentCore

See [DEPLOY.md](DEPLOY.md). Short version:

```bash
.venv/bin/agentcore configure -e agentcore_app.py -n billwatch -rf requirements.txt
.venv/bin/agentcore deploy
.venv/bin/agentcore invoke '{"prompt": "Nightly check - only tell me what I must act on."}'
```

Then schedule an EventBridge rule to invoke it nightly — that is the "runs
quietly in the background" part.

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md).

## Data

`billwatch/data/*.json` is a small, self-consistent synthetic household — no
real financial data. In production the two readers in `core.py`
(`load_bills`, `load_transactions`) swap for a Plaid / bank-export / bill-inbox
connector behind the same shape.

## License

MIT — see [LICENSE](LICENSE).
