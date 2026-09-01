# BillWatch — Devpost submission

## Elevator pitch
A background agent that watches your household bills and subscriptions and only
pings you when a payment is genuinely at risk or a charge looks wrong.

## Inspiration
Money admin is never hard, just relentless. A non-autopay bill sneaks past and
costs a late fee; a promo price quietly doubles; a subscription nobody has used
since spring keeps billing. Watching for all of it every week is exactly the
dull, repetitive vigilance an agent should own.

## What it does
Runs on a nightly schedule, does a full deterministic scan of bills, amount
history and recent charges, and surfaces only what needs a decision: payment
risks on non-autopay bills, charge anomalies (spikes, duplicates, unrecognized
merchants), subscription price creep, and stale subscriptions — each with the
real dollar figure. If nothing is off, the output is one sentence.

## How we built it
- **Strands Agents SDK** — a single `Agent` with six `@tool` functions and a
  system prompt built around restraint.
- **Amazon Bedrock** — Claude Haiku 4.5 via a cross-region inference profile.
- **Amazon Bedrock AgentCore** — `BedrockAgentCoreApp` entrypoint, deployed with
  the AgentCore CLI, invoked on an EventBridge cron.
- **A deterministic core** — all money logic (`billwatch/core.py`) is pure
  Python with 9 tests and zero model calls. The LLM never does arithmetic.

## Challenges
Getting the agent to *not* talk. Early versions dutifully listed every bill that
was fine. The fix was a system prompt that treats silence as the success case
and a `needs_attention` flag from the core that gives it permission to say
"nothing to do".

## Accomplishments
The correctness layer is fully testable without AWS — `make test` and
`make demo` run offline. The agent is a thin, swappable judgement layer on top.

## What we learned
For anything involving money or dates, keep the math in tested code and let the
model own tone and triage. That split is also what makes the demo trustworthy.

## What's next
Real bank data via Plaid; receipt-photo intake; AgentCore Memory for household
preferences; SES/SNS delivery.

## Built with
`strands-agents` · `amazon-bedrock` · `amazon-bedrock-agentcore` · `claude-haiku-4.5` ·
`python` · `boto3` · `eventbridge-scheduler`

## Try it out
- Code: https://github.com/nareshsaladi54-wq/billwatch-agent
- `make venv && make test && make demo`
- Deploy: [DEPLOY.md](DEPLOY.md)

## Checklist
- [x] Public GitHub repo, MIT license
- [x] README with architecture diagram
- [x] Built with Strands Agents SDK
- [x] Deployable on Amazon Bedrock AgentCore
- [ ] Demo video (≤5 min)
- [ ] AWS Builder ID on submission
