# Gap report — Seat 15, Helpdesk (`support`)

**Team 15 · Suryodaya (India) + Keystone (US) · all figures measured read-only 2026-09-20**
**Product compared: [Plain](https://plain.com)** — AI-native B2B support; MCP server with full workflow
writes, SLA modelled as thread state, Slack digests. Secondary: Intercom Fin, Pylon.
Full evidence in [`GAP_REPORT.md`](GAP_REPORT.md); defects in [`findings/`](findings/).

## 1. What do they do that we do not?

**SLA is a flag, not a clock — the biggest gap, and it is our own seat's request.**
Plain has two SLA types (first / next response) and a five-state timer:
`Pending → Imminent breach → Breaching → Breached`, plus `Canceled`. First response is a
**thread status** (`Needs first response`), so it cannot go unrecorded. Clocks skip messages
needing no reply; `Waiting for customer` stops the timer, `Paused for later` keeps it running.

Ours — **fixed mid-report on one instance, which is why the split matters.** Keystone now
stamps `first_response_at` from real replies (**133/150**) and derives breach from due-vs-
response in one rule: **150/150 correct**, and the flag no longer tracks status. Suryodaya is
unrepaired: `first_response_at` still **1/103**, so the new rule has nothing to evaluate and
**24 of 103** tickets that missed their deadline are still reported compliant — all 24 in the
same direction, silent misses, never false alarms. Remaining gaps on both: all five time fields
are declared `type: text` while `AgentTask.next_run_at` is a proper `date/datetime`; and we have
both waiting states (`waiting_on_customer`, `on_hold`) but neither affects any clock.

**No ticket can reference another.** `Ticket` has 32 fields and **no** parent/related/merge/
duplicate field, though **20 other entities** carry one (`Account.parent_account_id`,
`AgentJob.parent_job_id`). Swept all **425** schemas for a feature-request object: none.
Plain merges threads channel-aware (reply from parent, delivered via the child's channel) and
auto-assigns `Close the loop` when a linked issue resolves — linkage *drives state*.

**No insight layer.** Six counters and a CSAT %. Nothing groups by topic or recommends action.
Fin sells scorecards + monitors + recommendations at $99/mo per 1,000 conversations.

**Nothing has ever left the platform.** Suryodaya's three dispatch ledgers hold 0 rows;
Keystone's 25 dispatches all record `not_attempted_transport_disarmed`. No customer has been
contacted from either book.

**Digest destination.** Plain pushes three digests to **Slack**. `AgentTask.channel` offers
`internal`/`web`/`email` only.

## 2. Which gaps can an agent close with this seat's existing tools?

**Mine — orchestration, no platform change:**
1. **Topic + KB coverage analysis** (`Ticket.list` + `KBArticle.list`). Demonstrated: 17 tickets
   ask about shortages, 15 articles exist, **0 are sendable**. Only **10 of 100** articles are
   `published` *and* `public`.
2. **Breach-risk triage** — recompute time-remaining from `created_at` against the real policy
   (urgent 1h/8h … low 24h/120h) and **report that the stored flag disagrees**.
3. **Scheduled digest** — `AgentTask` is a real scheduler (`cron`, `prompt`, `notify_party_id`);
   Keystone already runs `Weekly Business Summary` on `0 8 * * MON`.
4. **Ticket → article loop** — `KBArticle.source_ticket_id` exists and is unused; drafting the
   missing *public* article is the fix for gap 1.
5. **Duplicate detection** — detectable, **not persistable** (no link field). The insight dies
   with the run.

**Platform, not mine:** writing `first_response_at` on reply; datetime-typing the time fields;
a link field on `Ticket`; a chat destination; arming the transport; any classifier.

## 3. What can an agent do that their product cannot?

**Breadth.** Plain exposes ~30 curated support tools; this seat sees **243**, generated one per
entity and per workflow transition. **Plain exposes a support workflow; AgentSwitch exposes a
business.** So "Kirloskar says nothing has worked all week" can be worked in one goal —
`Ticket` → `Party` → `KBArticle` → `AgentTask` — which a 30-tool support API cannot express.

**Provable dispatch.** On Keystone the reply pipeline **has run**: 196 decisions recorded
(`customer_facing` 146, `published_kb_only` grounding 34), 25 sends attempted, and **all 25
refused** because no operator armed the transport. `body_fingerprint` + `refused_body_changed`
is time-of-check-to-time-of-use protection in code. That is Lorikeet's "provable behaviour"
pitch, demonstrated with evidence — no product in this comparison can show it.

**Honest correction:** we are **not** ahead on drivability. Plain's MCP replies to the customer
and drives state. We are ahead of Intercom (14 tools, 3 writes, none touching the conversation).

## Defects found while measuring (all re-tested 2026-09-20)

| # | What | Status |
|---|---|---|
| 001 | App boundary not enforced for `sales`: 6 of 7 entities readable from a Helpdesk seat on **both** instances. Cause: `roles` holds `sales_viewer`, `allowed_apps` omits `sales` | reproduces — **widened**, MCP now leaks too |
| 002 | `Ticket.tags` a list against declared `text`; crashed 70/100 detail pages | **filed & fixed**, board S9 |
| 003 | `first_response_at` unwritten; breach flag mirrored status | **fixed on Keystone** (133/150 stamped, 150/150 correct) — **still open on Suryodaya**: 1/103 stamped, 24 breaches silently reported compliant |
| 006 | `AgentTask.last_run_status` = `queued` (not in schema, 15/96); 31 `cron` rows whose expression is a product name; Keystone's tasks report 30 runs with `last_run_at` null | **new** |
| 005 | `reopen_count` 56 on a `new` ticket | **no longer reproduces** — max is now 1 |

**One claim, not five defects:** twice a field held a value its declared type forbids (`tags`,
`last_run_status`); twice a timestamp went unwritten while the work demonstrably happened
(`first_response_at`, `AgentTask.last_run_at`). Three unrelated entities, two repeating failure
modes — **the declared schema is not a reliable description of what the rows contain, so an
agent must validate before it reasons.**

## Method

Read-only over MCP and REST against both instances; nothing written to either book; no
`PUT /api/accounting/locale`. Every figure re-derived on the submission date, not carried from
the first pass — the books are shared and moved under us (tickets 100→103, reply ledgers
0→196, `SupportAgentProfile` 0→7). **Ten first-draft claims were retracted as a result**, each
listed in `GAP_REPORT.md`; the largest were rejecting Plain unread, and claiming a drivability
lead we do not have. Vendor claims are tiered: Plain's MCP, SLA, statuses, digests and pricing
are primary pages read 2026-09-20; Plain's merge mechanics are a dated changelog; Plain's
Insights layer is marketing only and is not relied on.
