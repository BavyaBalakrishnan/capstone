# Gap report — Seat 15, Helpdesk

**Team 15 · team15@theschoolofai.in · Suryodaya (India) and Keystone (US)**
**Week-one deliverable. All figures re-derived 2026-09-20.**

Every number on our side was re-pulled and recomputed on the submission date, not
carried over from the first pass. That matters here: these books are shared with
other teams, and between the first pass and this one the Suryodaya ticket count
moved 100 → 103, `AgentJob` moved 973 → 1227, `SupportAgentProfile` moved 0 → 7,
Keystone's reply ledgers moved 0 → 196, and two of the three defects in
`findings/005` stopped reproducing. A gap report written against a week-old pull
would have been wrong in four places. Re-deriving is not diligence theatre; it is
the only way a claim about a shared book stays true long enough to submit.

Products compared:

| Product | Why | Studied? |
|---|---|---|
| **Plain** (plain.com) | AI-native B2B support. MCP server with **full workflow writes**, SLA modelled as thread *state*, Slack digests, thread merge. The closest thing to what this capstone asks us to build. | **yes — docs read 2026-09-20** |
| **Intercom Fin** (intercom.com) | Market leader in AI customer support; the benchmark everyone is measured against | **yes — MCP docs read 2026-09-20** |
| **Pylon** (usepylon.com) | B2B, Slack-native, account-level context, MCP with write actions, "Skills" = reusable plain-English agent instructions | partial — API docs read, **trial outstanding** |
| **Lorikeet** (lorikeetcx.ai) | Regulated industries; sells on *"provable behaviour and audit trails"* — the standard to measure our agent against | TODO — audit/provability docs |
| **Decagon** (decagon.ai) | "Agent Operating Procedures" — a third product converging on plain-language agent instructions | TODO |

Not benchmarked: **Zendesk / Freshdesk / Front / Help Scout / HubSpot** — no
first-party MCP server; the "twenty-year-old product with a chatbot bolted on"
case the brief warns about.

> **Correction from the first draft.** That draft rejected Plain as a product that
> "appears mainly in its own marketing" and rejected Intercom on the grounds that
> its MCP server is "read-only, 6 tools". Both rejections were wrong, and both were
> made from third-party summaries rather than the vendors' own documentation.
> Intercom's MCP exposes **14 tools, three of which write**. Plain's exposes about
> **30, eleven of which write**, including replying to the customer. Plain is not a
> marketing artefact — it is the strongest product in this comparison. The error is
> recorded rather than quietly fixed because it is the same error the method
> section warns about: believing a resource name instead of reading the page.

---

## 1. What do they do that we do not?

### 1.1 Spotting trends and patterns in incoming tickets — CONFIRMED GAP

**Them.** Fin surfaces what customers ask about most as an input to improving the
product and the docs. [SOURCE: Fin's own sales material.] Plain ships this as a
named product surface — an **Insights** layer that clusters threads into themes,
plus a **Themes** digest pushed to Slack. [SOURCE: vendor marketing and a dated
changelog entry; not a docs page. Treat as a lead.]

**Us.** The Helpdesk dashboard has six counters — open, unassigned, urgent, SLA
breached, resolved, closed — plus CSAT and breach rate. Nothing groups tickets by
topic, nothing surfaces what recurs, nothing recommends an action. That is
reporting, not insight.

**Bucket: ORCHESTRATION — mine to build.** Demonstrated read-only using only
tools this seat already holds (`Ticket.list`, `KBArticle.list`). No new tables or
endpoints required.

Measured on Suryodaya, **103 tickets and 100 KB articles** (2026-09-20):

```
demand by type                    demand by topic (words in subjects)
  question         19               despatch   26
  other            18               line       20
  complaint        17               shortage   17
  incident         13               enquiry    10
  service_request  13               tooling     8
  feature          13
  bug              10
```

Crossing demand against what may actually be sent to a customer:

| topic | tickets | articles that exist | **sendable** (published + public) |
|---|---|---|---|
| despatch | 26 | 28 | 1 |
| line | 20 | 35 | 2 |
| **shortage** | **17** | **15** | **0** |
| **enquiry** | **10** | **7** | **0** |
| **tooling** | **8** | **2** | **0** |

Only **10 of 100** KB articles are `published` **and** `public`. The full split:
by status, 38 published / 36 archived / 18 draft / 8 in_review; by visibility,
50 internal / 27 public / 23 agents_only. The two conditions barely overlap.

So: 17 customers have asked about shortages, the company has written 15 articles
about shortages, and **not one of them can be sent to a customer.** Every one of
those tickets needs a human to rewrite an answer that already exists.

That is the difference between a trend and an insight. A dashboard says "despatch
is your top topic". The useful statement is "you are re-answering shortages by
hand 17 times because the answers are locked internal — publish them and 17
tickets become self-serve."

### 1.2 Scorecards, monitors, recommendations and digests — CONFIRMED GAP, but the substrate exists

**Them — Fin.** Sold as a **Pro add-on, $99/month per 1,000 conversations**:

- **Custom AI scorecards.** You write the rubric — acknowledged in SLA, order
  number confirmed, a date given rather than "soon", tone right for an OEM
  customer — and *every* conversation is graded, not the sample a human reviewer
  could get through by hand.
- **Monitors.** A standing condition that alerts when it trips: refund questions
  up 40% week on week, CSAT on billing below 70%. A new product defect usually
  appears as a spike in one topic hours before anyone files it as a bug.
- **AI recommendations.** Not a chart, an instruction: *"27 conversations last
  week asked about the return window and no help article covers it — write one."*

Note the relative pricing: Pro is $0.099 per conversation while the Copilot
add-on, which actually helps an agent answer, is $35 per 5,000 — $0.007.
**Measuring the agent costs 14x more per conversation than assisting it.** A
vendor's pricing page is the clearest statement of what it thinks is hard.

**Them — Plain.** Three named digests delivered to **Slack**, each separately
toggleable with a configurable UTC send time under `Settings → Notifications →
Slack` [SOURCE: primary, `plain.com/docs/digests`, read 2026-09-20]:

| digest | contents | audience |
|---|---|---|
| **Daily Standup** | focused view of what is in your queue | frontline |
| **Daily Summary** | queue health — and for teams running Ari, "how many threads it handled and handed off in the last 24 hours" | leadership |
| **Themes** | "the main topics coming up in your support threads" | leadership |

The Ari line is the one to notice: **the daily digest reports what the AI agent
did, including its handoffs.** Agent oversight, delivered on a schedule, to the
place the team already works.

**Us.** None of the four. Six counters and a CSAT percentage.

**Bucket: ORCHESTRATION — mine to build**, and the substrate is better than the
first draft claimed.

| | what it needs | state on our side (2026-09-20) |
|---|---|---|
| Recommendations | `Ticket.list` + `KBArticle.list` | **already demonstrated** — §1.1 |
| Scorecards | read conversations, grade against a rubric | tools exist; needs a rubric and a scorer |
| Monitors / digests | run a check on a schedule and deliver it | **`AgentTask` is a real scheduler** — see below |

`AgentTask` carries `schedule_type` (`cron` / `interval` / `one_time`),
`cron_expression`, `interval_minutes`, `next_run_at`, `last_run_at`,
`last_run_status`, `run_count`, `max_retries`, `timeout_seconds`, a required
`prompt`, `persona_id`, `provider_id`, a `channel` (`internal` / `web` / `email`)
and `notify_party_id`. That is a scheduled, prompt-driven, delivered-to-a-party
job — a digest in all but name.

**And Keystone proves it is used.** Two live rows:

```
Weekly Business Summary   cron 0 8 * * MON       status active
Daily Invoice Reminder    cron 0 9 * * MON-FRI   status active
```

> The first draft said "`AgentTask` holds 96 rows, all `completed`" and "nothing
> is scheduled on it". Both were wrong, and both came from looking only at
> Suryodaya. Suryodaya's 96 rows carry `completed`, `active`, `paused` and
> `failed`; Keystone runs two live cron schedules.

**Two real gaps remain against Plain.** `channel` offers `internal`, `web` and
`email` — **no chat destination**, so a digest cannot reach the team in Slack or
Teams where support actually lives. And Plain ships three digests pre-built;
AgentSwitch ships the scheduler and leaves the content to you. The first is
platform work. The second is mine.

**A caveat that belongs with the bucket, not buried in §3.5:** on this evidence
the scheduler's own bookkeeping cannot be trusted to tell you whether your digest
ran. See `findings/006`.

### 1.3 Nothing can connect two tickets to each other — CONFIRMED GAP

**Them — Pylon.** Exposes **Feature Requests** as a first-class API resource,
separate from Issues. A customer saying "it would be good if it did X" becomes an
object that persists, accumulates the other customers asking for the same thing,
and carries a count to the product team. Pylon also exposes **Teams**, so work
groups exist as records rather than strings.

**Them — Plain.** Two distinct mechanisms, both shipped 2026-03-11 [SOURCE:
Plain changelog, dated; not a docs page]:

- **Merge.** The parent thread stays active, the child becomes `Ignored`, the
  child's new messages appear in the parent's timeline, and a reply sent from the
  parent is **delivered back out through the child's original channel** — across
  email, Slack, Discord and chat. Reversible.
- **Lock + continuation.** A *locked* thread that receives a customer reply spawns
  a **new** thread rather than reopening, and the two are cross-linked `Continued
  in` / `Continued from`.

And a third, from the statuses page [SOURCE: primary, read 2026-09-20]: the
status **`Close the loop`** is auto-assigned when a linked issue resolves. So in
Plain, linkage **drives state** — resolve the underlying issue and every waiting
thread moves itself into a follow-up queue. That is the part that saves work; the
pointer alone would not.

**Us.** Swept all **425** entity schemas for `featurerequest | idea | roadmap |
vote | enhancement | suggestion | backlog | productfeedback`. One match —
`MeetingPollVote`, in `scheduling`, about choosing meeting times. There is no
feature-request object in the platform. The only representation is
`Ticket.type = 'feature'`, 13 tickets on Suryodaya, answered and closed like any
other.

The sharper finding is underneath it. **`Ticket` has 32 fields and not one links
to another ticket** — no parent, no merge, no duplicate, no related.

That is not because the platform lacks the pattern. **20 other entities** carry a
`parent_*`, `related_*` or `linked_entity` field:

```
Account.parent_account_id        AgentJob.parent_job_id
BOM.parent_bom_id                AssetCategory.parent_category_id
CalendarEvent.parent_event_id    BlogCategory.parent_category_id
BlogPost.related_posts           ChannelConversation.linked_entity
DesignVersion.parent_version_id  DesignAssemblyVersion.parent_version_id
```

So eight customers can ask for the same thing and nothing in the data can ever
connect them. Every ticket is an island. This is also why duplicate detection and
merge are absent: the field needed to express the result does not exist.

**Bucket: SPLIT, and the split is the point.**

- **Detecting** that several tickets are the same request is **orchestration —
  mine**. It needs only `Ticket.list` plus the topic analysis in §1.1.
- **Persisting** that relationship is **platform**. Without a parent or related
  field on `Ticket`, or a feature-request object to promote them into, an agent
  can find the pattern and cannot record it. The finding dies when the run ends.

An agent here can produce the insight but has nowhere to put it, which caps what
repeated analysis can ever be worth.

### 1.4 SLA is modelled as a flag, not a clock — CONFIRMED GAP

This is the gap that matters most for this seat, because seat 15's assigned
request is *"tell me which will breach SLA."*

**Them — Plain** [SOURCE: primary, `plain.com/docs/product/platform/slas` and
`/threads/statuses`, both read 2026-09-20]. Two SLA types — **first response
time** ("how long it takes your team to send the first reply to a new thread")
and **next response time** ("how long it takes to reply after a customer
responds"). A five-state timer:

```
Pending -> Imminent breach -> Breaching -> Breached        (+ Canceled)
```

Configured per **Tier** under `Settings → Tiers & SLAs`, optionally bounded to
business hours. Three design decisions worth copying:

1. **First response is a thread status, not a timestamp.** The first two statuses
   in Plain's `Todo` group are literally `Needs first response` and `Needs next
   response`. The thread occupies that state until someone replies, so the metric
   cannot silently go unrecorded.
2. **The clock measures obligations, not traffic.** SLAs skip messages that do not
   need a response — a customer's "thanks, that worked" does not start a timer, so
   a well-handled ticket cannot be scored as a breach.
3. **The two kinds of waiting have opposite timer semantics.** `Waiting for
   customer` cancels the timer (you have replied; the ball is theirs).
   `Paused for later` keeps it running (you have not; the ball is yours).

**Us.** `Ticket` carries `sla_id`, `sla_response_due`, `sla_resolution_due`,
`sla_response_breached`, `sla_resolution_breached`, `first_response_at`,
`resolved_at`, `closed_at`. The vocabulary is all there.

> **This section was overtaken by a platform fix during the report period, and the
> fix is recorded here with the same evidence standard as the defect.** On
> **2026-09-20** both instances behaved as described below. On **2026-09-21** a fix
> shipped: `first_response_at` is now stamped by real replies, and breach is derived
> from due-vs-response in one rule. Re-measured 2026-09-21T02:47Z, **it is effective
> on Keystone and not yet on Suryodaya.** The original defect is left in place
> because Suryodaya still exhibits it, and because the half-landed state is itself
> the more useful finding.

**Keystone — fixed, verified.** `first_response_at` populated on **133 of 150**
tickets. The stored flag now matches a due-vs-response recomputation on **150 of
150**, and it no longer tracks status: `closed` splits 45 False / 11 True,
`waiting_on_customer` splits 15 False / 1 True. Breach is being computed from
evidence.

**Suryodaya — rule shipped, data not backfilled.** Three things are still wrong,
measured on 103 tickets:

**(a) The clock never starts.** `first_response_at` is populated on **1 of 103**
tickets — and that one row is our own probe ticket, not seeded data. Response-SLA
breach is therefore not computable from stored data.

**(b) The flag is indistinguishable from the status column.** Cross-tabulating
status against `sla_response_breached` gives a near-perfect correlation, 102/103:

```
new 21 · open 21 · in_progress 27 · waiting_on_customer 3 · on_hold 4  -> True
closed 22 · resolved 4                                                  -> False
```

With no `first_response_at` to evaluate, the new one-rule computation falls
through to "not breached" for everything already closed or resolved — which is
observationally identical to the old behaviour. Recomputing the truth against
`sla_response_due` gives:

```
flag agrees with reality : 79
flag disagrees           : 24
   flagged breached but is not :  0
   NOT flagged but IS breached : 24   <- silent misses
```

**24 of 103 tickets missed their response deadline and are reported compliant**,
including `'Aurangabad despatch, week 20'` (closed, due 2026-09-16, never
answered) and `'Follow-up — Vidarbha Castings Udyog'` (resolved, due 2026-09-14,
never answered). Every error runs one way: zero false alarms, 24 silent misses.
The metric improves as tickets are closed, whether or not anyone replied.

That direction matters more than the count. An SLA number that can only
under-report is worse than no number, because it survives review.

**(c) The time fields are declared as text.** `first_response_at`,
`resolved_at`, `closed_at`, `sla_response_due` and `sla_resolution_due` are all
`"type": "text"` in `/api/schemas`. The platform *has* a datetime type and uses
it elsewhere — `AgentTask.next_run_at` is `"type": "date", "subtype":
"datetime"`. `Ticket` uses it for none of its five time fields. Same family as
`findings/002`, where `tags` was declared `text` and stored as a list.

**What we do have, and the first draft missed:** AgentSwitch *does* carry Plain's
two waiting states — `waiting_on_customer` (3 tickets) and `on_hold` (4) both
exist and are in use. The states are not the gap. The gap is that **no timer
semantics attach to either**, so even if (a) were fixed tomorrow, a ticket that
sat three days waiting on the customer would score identically to one we sat on
ourselves.

**Bucket: SPLIT.**

- **Platform:** populating `first_response_at` on reply, typing the time fields as
  datetime, and giving the two waiting states a defined effect on the clock.
- **Orchestration — mine:** with the real SLA policy (OEM Customer SLA:
  09:00–18:00 Mon–Fri; urgent 1h/8h, high 4h/24h, medium 8h/72h, low 24h/120h) an
  agent can compute time-remaining from `created_at` and rank the open queue by
  risk *today*, without waiting for the platform fix — and must report that the
  stored flag disagrees with its own arithmetic.

### 1.5 Other gaps — measured, bucket assigned

All "us" figures re-derived 2026-09-20 unless marked.

| Gap | Evidence on our side | Bucket |
|---|---|---|
| **Multi-channel intake** (Pylon 8+; Plain: email, Slack, Discord, chat, Teams) | `Ticket.channel` has 6 options and is populated (social 26, email 18, phone 18, portal 17, chat 13, api 11) — but on Suryodaya all three dispatch ledgers hold **0 rows**, and on Keystone the 25 dispatch rows all record `transport: mailbox` with outcome `not_attempted_transport_disarmed`. **Nothing has ever actually left the platform.** | **Platform** |
| **Chat as a digest/notification destination** | `AgentTask.channel` is `internal` / `web` / `email`. No Slack or Teams. | **Platform** |
| **Third-party integrations** (Pylon 25+ — Salesforce, HubSpot, Linear, Jira) | none | **Platform** |
| **Workforce management / capacity routing** | `SupportAgentProfile` now holds **7 rows on Suryodaya, 8 on Keystone** (the first draft said 0 — it has since been seeded). But `Ticket.assigned_group` is still `type: text` holding **68 distinct values across 68 non-empty tickets**, and `required_skill` **64 distinct across 64**. A roster now exists; the ticket fields still do not point at it. | **Platform** (data model) |
| **Account-level context for B2B** — Pylon's core pitch | `crm` is in `allowed_apps`, and the catalogue carries `CRMPreferences` (1 row on each instance), `Party`, `PartyRelationship`, `AddressBook`. No `AccountPlan`, no `Pipeline`, no `Goal`. The shared customer spine is thin for a Helpdesk seat. | **Platform** |
| **Intent / sentiment classification** | `Ticket.type` and `priority` are manual `select` fields. No classifier. | **Platform** (needs a model) |
| **CSAT loop** — Pylon has a `Surveys` API resource [listed in the API reference index; page not read] | `satisfaction_rating` exists; no survey object and no transport to send one. The field is populated anyway — **92 of 103 rated, of which 21 are still in `new`**, while only **27** have reached `resolved` or `closed`. Ratings exist for tickets nobody has finished. | Platform to collect, **orchestration** to act on |
| **Duplicate / merge detection** | no parent, merge, duplicate or related field on `Ticket` — §1.3 | Detect: **orchestration**. Persist: **platform** |
| **A call object** — Pylon's `Call Recordings` carries title, summary, participant emails, duration, source platform and URL [VERIFIED: docs page read. Pylon stores no audio — it indexes recordings held on Gong, Fathom, Grain, and has **no upload endpoint**] | No call object of any kind. **18 tickets record `channel: phone`** and nothing captures who was on the call, how long it ran, or what was agreed. | **Platform** |
| **Teams as records** — Pylon exposes `Teams` [listed in API reference index; page not read] | see workforce row: `assigned_group` is free text, 68 distinct values across 68 tickets. A record would have refused those writes; a string accepted every one. | **Platform** |

**NOT gaps — checked and found present.** Recorded so they are not claimed by
mistake. [Structural claims from `/api/schemas`; re-swept 2026-09-20.]

| Claimed gap | Why it is not one |
|---|---|
| Knowledge model | `KBArticle` matches Pylon's Training Data resource closely, including the same three-way visibility split (`public`/`internal`/`agents_only` vs `everyone`/`user_only`/`ai_agent_only`). |
| Canned responses | `CannedResponse` holds 100 rows on Suryodaya, 16 on Keystone, and is in this seat's catalogue. |
| Forms | `Form` has `blocks`, `logic_rules` (Pylon's conditional logic), `presentation_mode`, and `consent_lawful_basis` carrying all six GDPR bases — richer than Pylon's ticket-forms page describes. The gap is that **nothing links a form to a ticket** while 17 tickets record `channel: portal`. Forms belong to seat 25, so reaching them is an escalation, not a defect. |
| Attachments | `FileAttachment` plus the `Drive*` family — versioning, sharing, access logs, retention policy, legal hold — is a richer document layer than Pylon's. |
| Audit trail | `endpoint.job_ledger.verify` / `.replay` / `.forensics` exist and are in this seat's catalogue. |
| Testing a skill before deploying it | `endpoint.agent_governance.skill_sandbox` accepts `candidate_markdown`. Fin sells the equivalent inside its $99/month Pro add-on. |

**Remaining gaps in knowledge handling** (narrower than "we have nothing"):
ingestion — Pylon can crawl a docs site and upload PDF, CSV, markdown and images
up to 50MB, while every `KBArticle` must be hand-written; and freshness — Pylon
records `scrape_status` with `last_scraped`, while `KBArticle` has only
`updated_at`, which says when someone edited it, not whether it is still true.

---

## 2. Which of those gaps can an agent close with the tools this seat already has?

**Mine to build, today, no platform change:**

1. **Topic and demand analysis** — §1.1, demonstrated.
2. **KB coverage gap analysis** — cross demand against *sendable* articles and
   name which need publishing. The §1.1 table.
3. **Breach-risk triage** — compute time remaining from `created_at` against the
   real SLA policy, rank the open queue, and **report the disagreement** with
   `sla_response_breached`. Per §1.4 the stored flag is the status column; an
   agent that recomputes is strictly more truthful than the platform.
4. **A scheduled daily digest** — Plain's Daily Standup, built on `AgentTask` with
   `schedule_type: cron` and a `prompt`, delivered to `channel: email`. Keystone
   already runs two such tasks. This closes §1.2 for everything except the Slack
   destination.
5. **Escalation follow-through** — the escalation engine fires and nothing
   downstream acts on it. An agent can close that loop.
6. **Repeat-customer detection** — group by party, read what was promised in each,
   draft one escalation with the evidence attached.
7. **Duplicate and repeat-request detection** — reporting only. Per §1.3 there is
   no field on `Ticket` to record the relationship.
8. **Ticket → article loop.** `KBArticle.source_ticket_id` exists and is unused.
   After solving a ticket, draft the missing *public* article from it — which is
   the fix for the 10-of-100 sendable problem in §1.1.

**Platform work, not mine:** live channel transport (nothing has ever been sent
from either book), a chat destination for digests, integrations, `Ticket` fields
that point at the roster, `first_response_at` being written on reply, datetime
typing for the time fields, any classifier, and a link field on `Ticket`.

**One honest caveat on item 4.** `findings/006` shows the scheduler's own
bookkeeping is unreliable — Keystone's two tasks report 8 and 22 runs with
`last_run_at` and `last_run_status` both null. An agent can schedule a digest; it
cannot yet prove from the platform that the digest ran. Until that is fixed, the
agent should record its own run evidence rather than trusting `AgentTask`.

---

## 3. What can an agent do that their product cannot?

### 3.1 On drivability we are behind Plain and ahead of Intercom

All three tool counts below were measured or read on 2026-09-20.

| | tools exposed | can the agent reply to a customer? | can it drive workflow state? |
|---|---|---|---|
| **Plain MCP** | ~30 | **yes** — `Reply To Thread` | **yes** — `Mark As Done`, `Assign`, `Snooze`, `Change Priority`, `Add Labels` |
| **AgentSwitch, this seat** | **243** | not yet — the transport has never been armed (§3.3) | **yes** — create, update, one tool per workflow transition |
| **Intercom MCP** | 14 | **no** — `add_internal_note` only; "nothing is sent to the customer" | **no** — cannot create or update a ticket |

> **The first draft claimed "we are ahead of the market leader on agent
> drivability", citing Intercom at 6 read-only tools and AgentSwitch at 230. Both
> numbers were wrong and the conclusion was too strong.** Intercom has 14 tools
> including three writes (`create_article`, `update_article`,
> `add_internal_note`) — but none of them touch the conversation or the ticket, so
> the *shape* of the claim survives against Intercom. It does not survive against
> Plain, whose MCP does everything ours does and actually delivers the reply.

**What is genuinely ours:** breadth and generality. Plain's ~30 tools are a
curated set over the support workflow. AgentSwitch's 243 are generated from the
data model — one per entity, one per workflow transition — so an agent can reach
anything the seat is entitled to, including entities Plain has no equivalent for.
That is a different and defensible claim: **Plain exposes a support workflow;
AgentSwitch exposes a business.**

**And one thing Plain does that we should copy outright.** Plain's MCP
authenticates by OAuth against the user's own account, with no separate API key:
*"the MCP server has the same permissions as your user."* That is section 4 of the
brief — "different door, same answer" — implemented as an architectural property
rather than asserted as a rule. AgentSwitch derives each door's authority
separately, which is exactly why `findings/001` exists: this seat holds
`sales_viewer` in `roles` while `allowed_apps` omits `sales`, and the doors
disagree about which is authoritative.

### 3.2 What the pricing pages say about the standard

| vendor | pricing | AI billed how | published? |
|---|---|---|---|
| **Plain** | Foundation **$35/mo** (1 seat, +$35 each), Horizon **$299/mo** (3 seats, +$99 each), Frontier custom | **bundled credits** — 2,000/mo and 15,000/mo | **fully public** [VERIFIED: page fetched twice, 2026-09-20] |
| **Fin (Intercom)** | **$39 / $99 / $139** per human seat/mo | **$0.99 per outcome**, 50-outcome monthly minimum | public [VERIFIED: Fin's sales material] |
| **Pylon** | — | — | **none** — the pricing URL is a demo booking form [VERIFIED: page fetched] |
| Lorikeet / Sierra / Decagon | ~$0.80 per resolution / outcome-only / $95K–150K per year | per-resolution | **third-party** — all three from Lorikeet's own comparison pages, which rank Lorikeet first. Leads, not facts. |

Three philosophies, not one converged standard: Plain bundles AI into credits and
publishes everything, Fin bills per outcome, Pylon publishes nothing. The honest
claim is that **at least two vendors publish per-resolution pricing and a third is
reported to** — not that the market has converged.

The outcome-pricing half of that is still the useful signal, because **you cannot
bill per outcome unless you can prove an outcome occurred.** To charge $0.99 with
confidence a vendor needs a definition of "resolved", evidence it happened, and a
rule for not charging when it did not. That is a verification requirement, not a
feature.

Which makes AgentSwitch's dispatch vocabulary worth reading again:
`attempt_outcome_unknown`, `unknown_possibly_delivered`, `unknown_possibly_sent`.
**None of those could honestly be billed.** The platform models the uncertainty
that makes outcome pricing hard — and §3.3 now shows it enforcing it.

Architecturally, Fin also sells as an AI layer over *someone else's* helpdesk
rather than only inside Intercom. That is the same shape as this capstone — an
agent running separately, driving the platform over its API — so the assignment's
architecture matches where the market leader landed.

### 3.3 The reply pipeline is built for provable agent behaviour — and on Keystone it has run, and it held

Lorikeet sells on *"provable behaviour and audit trails"*. AgentSwitch models it
in three ledgers:

- `TicketReplyDelivery` — the decision. Records `audience`
  (`customer_facing` | `internal_note`), `grounding_state`
  (`none_claimed` | `published_kb_only` | `grounding_unverifiable`),
  `body_fingerprint`, `thread_binding`, `recipient_source`,
  `grounded_article_ids`, `provenance_basis`.
- `TicketReplyDispatchClaim` — a lease (`claim_token`, `lease_expires_at`,
  `claim_count`) so the same reply cannot be sent twice.
- `TicketReplyDispatch` — the attempt, with a vocabulary separating "did not try"
  from "tried and failed" from "do not know".

`body_fingerprint` plus `refused_body_changed` is time-of-check-to-time-of-use
protection: approve a body, and if the text changes before the send, the send is
refused. That is the brief's "re-read before you act" rule enforced in code.

> **The first draft said all three ledgers hold 0 rows and the pipeline "has never
> run". That is true on Suryodaya and false on Keystone**, where the pipeline has
> since been exercised. The corrected version is a better result.

Keystone, 2026-09-20:

```
TicketReplyDelivery  196 rows
   audience         customer_facing 146 · internal_note 50
   grounding_state  none_claimed 162 · published_kb_only 34
   recipient_source ticket_source_email 146 · none_resolvable 50

TicketReplyDispatch   25 rows   (TicketReplyDispatchClaim 25)
   transport        mailbox 25
   resolution       awaiting_operator_arming 25
   outcome          not_attempted_transport_disarmed 25
```

Read that carefully: **196 reply decisions were recorded, 25 sends were attempted,
and every single one was refused because no operator had armed the transport.**
Nothing reached a customer. The guard held, and it recorded *why* in a code that
distinguishes "we chose not to try" from "we tried and failed".

That is the provability Lorikeet sells, demonstrated with evidence on a live book
— and it is the strongest single thing this platform has against any product in
this report. Two honest qualifications: only **34 of 196** decisions claim
`published_kb_only` grounding, with 162 claiming none; and Suryodaya's ledgers are
still empty, so this is one instance, not the platform.

**What this means for the agent to be built:** the pipeline is real, it refuses
correctly, and it has never successfully delivered. Driving it end to end — and
writing tests that prove the `published_kb_only` and `refused_body_changed` guards
hold — is the most valuable work available on this seat.

### 3.4 The whole-thread move

Their software makes a support engineer fast; a human still drives every step.
Plain's agent can reply and close a thread, but a person still decides which
thread, and why.

The agent takes one sentence — *"Kirloskar says nothing has worked all week"* —
and works the thread alone: finds every ticket from that party, checks which
deadlines passed and by how much, reads what was promised in each, identifies the
pattern across them, checks whether a public article exists to answer it, and
drafts the escalation with evidence attached. Nobody opens twelve tabs.

The 243-tool catalogue is what makes this possible: the agent crosses from
`Ticket` to `Party` to `KBArticle` to `AgentTask` in one goal, which a curated
30-tool support API cannot express.

This is the sustenance-engineering week I do at Infoblox, automated.

### 3.5 Honest limits on this instance

Defects found while measuring the above. **All re-tested 2026-09-20**; two that
the first draft reported no longer reproduce, and are marked as such rather than
quietly dropped.

| # | What | Status today |
|---|---|---|
| **001** | REST does not enforce the app boundary for `sales`: 6 of 7 sales entities readable from this seat on **both** instances (`Quotation` alone refuses, and only via a per-entity role check). Controls still correct — `SalarySlip`, `Contract`, `EsignDocument`, `Invoice` all 403 with an *app* message. | **REPRODUCES, and has widened.** The MCP catalogue now also carries `Deal`, `Lead`, `Activity`, `Note`, `SalesOrder`, `CRMPreferences` and `Item` on **both** instances, so the door the first draft certified as correctly refusing no longer does. Root cause visible in `/api/auth/me`: `roles` contains **`sales_viewer`** while `allowed_apps` does not contain `sales`. |
| **002** | `tags` stored as a list where the schema declares `text`, crashing 70 of 100 ticket detail pages | **FILED AND FIXED** — bug report `5442dba1-4696-4ae8-8000-a74187c59f69`, board S9, severity High |
| **003** | `first_response_at` never recorded, so response-SLA breach is not computable; the stored flag tracks status instead | **FIXED ON KEYSTONE, STILL OPEN ON SURYODAYA** (re-tested 2026-09-21T02:47Z). Keystone: 133/150 stamped, flag correct 150/150. Suryodaya: 1/103 stamped, 24 of 103 breaches silently reported compliant. The rule shipped to both; the backfill reached one. See §1.4. |
| **004** | Agent dashboard reported $6,010,165 estimated cost against 19,100 tokens | **NOT RE-TESTED this pass.** Carried as written-up-only; do not rely on the figure without re-deriving it. |
| **005** | `reopen_count` holding values unreachable under the state machine (56 reopens on a ticket in `new`); `response_count` 48 against zero reply rows | **NO LONGER REPRODUCES.** Max `reopen_count` on Suryodaya is now **1**, and **zero** tickets in `new` carry a non-zero count; `response_count` is 0 on 102 of 103 tickets and 1 on the remaining one. Either fixed or reseeded between passes. The `sender_type` limb was not re-tested. |
| **006** | `AgentTask` holds values its own schema forbids, and run bookkeeping is never written | **NEW this pass.** Suryodaya: `last_run_status` = **`queued`** on 15 rows (schema declares only `success`/`failed`/`timeout`); 31 `cron` rows whose `cron_expression` is a product name (`"Feeler Gauge Set 597"`); 17 `one_time` tasks with `run_count > 1`, worst case 57; 14 rows with `run_count: 0` carrying a `last_run_status`. Keystone: both live tasks report `run_count` 8 and 22 with `last_run_at` and `last_run_status` **null**. |

**The pattern across 002, 003 and 006 is worth stating as one claim rather than
three bugs.** Twice now a field has held a value its declared type forbids
(`tags`, `last_run_status`), and twice a "when did X happen" timestamp has gone
unwritten while the work it describes demonstrably occurred (`first_response_at`,
`AgentTask.last_run_at`). Three unrelated entities, two failure modes, both
repeating. For an agent that must decide from stored state, that is a more useful
finding than any single defect: **this platform's declared schema is not a
reliable description of what its rows contain, so an agent should validate
before it reasons.**

Instance split: 001 affects both. 003 and 006 are Suryodaya-side for the data
defects; 006's null-bookkeeping limb is Keystone. 002 is fixed. 005 is gone.

---

## Method, and how far each claim can be trusted

**Everything on our side is measured, and re-measured.** All figures were pulled
read-only over MCP and REST against both instances on **2026-09-20** and
recomputed from those pulls before submission. Nothing was written to either
book: the client used for this pass refuses any MCP method other than
`initialize`, `notifications/initialized`, `tools/list` and `tools/call`, and
refuses any tool whose name does not end in `.list`, `.get`, `.search`, `.count`
or `.schema`. No `create`, no `update`, no workflow transition, and no
`PUT /api/accounting/locale`.

Raw pulls are **not committed** — they contain named people and companies from
books other teams share. `out/` is gitignored.

**Their side is not all equal, and pretending otherwise would undermine the
rest.** Three tiers:

*Primary source, page actually read (dated):*
**Plain** — MCP server tool list and the permissions-inheritance statement
(`/docs/agents/mcp-server`, 2026-09-20, fetched twice); SLA model and the five
timer states (`/docs/product/platform/slas`); thread status state machine
(`/docs/product/platform/threads/statuses`); the three Slack digests
(`/docs/digests`); pricing (fetched twice, identical). **Intercom** — the MCP tool
list and the statement that `add_internal_note` sends nothing to the customer
(`developers.intercom.com/docs/guides/mcp`, 2026-09-20). **Pylon** — API reference
index (23 resources); Training Data (6 endpoints, three-way visibility,
`scrape_status`, 50MB uploads); Ticket Forms; Call Recordings (indexes third-party
recordings, no upload endpoint); publishes no pricing. **Fin** — pricing and
add-on structure, from Fin's own sales material.

*Vendor-published but self-described — dated changelog or marketing page:*
Plain's thread **merge** and **lock/continuation** mechanics (changelog
2026-03-11); Plain's **Insights/Themes** clustering, sentiment grouping and
heatmaps (marketing pages only — the weakest Plain claim in this report); Plain's
"only platform with a GraphQL API, no restrictive rate limits, full API-UI
parity" (Plain's own comparison blog); Pylon's "Skills", Assist Agent, Background
Agent, 8+ channels, 25+ integrations.

*Third-party or competitor-sourced, NOT independently verified:*
"only four support platforms ship an MCP server" — from a vendor blog that lists
itself among the four; Pylon's MCP tool list; Lorikeet, Sierra and Decagon
pricing, all from Lorikeet's own comparison pages.

**Known imprecision, stated rather than smoothed over.** Plain's MCP docs page
says **30 tools** while its own per-category listing sums to **32** (the Tenants
heading says 3 and lists 4; Help Center says 5 and lists 6). The tool *names* were
identical across two independent fetches, so the capability claim is solid and the
count is approximate. Similarly, one third-party source counts Intercom's server
at 13 tools against the docs page's 14.

**Claims retracted from the first draft**, each because it was made from a
summary rather than a page, or from one instance rather than both:

1. "Intercom's MCP is read-only with 6 tools" — it is 14 with 3 writes.
2. "Plain appears mainly in its own marketing; did not survive neutral rankings" —
   Plain is the strongest product in this comparison.
3. "We are ahead of the market leader on agent drivability" — true of Intercom,
   false of Plain.
4. "AgentSwitch, this seat: 230 tools" — measured at **243**, identical on both
   instances.
5. "`AgentTask` holds 96 rows, all `completed`" and "nothing is scheduled" —
   Suryodaya's rows carry four different statuses and Keystone runs two live cron
   schedules.
6. "All three reply ledgers hold 0 rows / the pipeline has never run" — true on
   Suryodaya, false on Keystone (196 / 25 / 25).
7. "`SupportAgentProfile` holds 0 rows. No roster exists" — 7 on Suryodaya, 8 on
   Keystone.
8. "`CRMPreferences` is in the catalogue only via the `viewer` role, which the
   Keystone seat does not hold" — both seats now carry identical roles
   (`support_user`, `user`, `agent_user`, `sales_viewer`) and identical 243-tool
   catalogues.
9. "424 entity schemas" — `/api/schemas` returns **425**.
10. "21 entities carry a parent/related field" — **20**.

**Still outstanding:** the Pylon trial and Pylon's MCP tool list; Lorikeet's and
Decagon's own documentation; re-deriving `findings/004`; a docs-page source for
Plain's Insights layer; and the `sender_type` limb of `findings/005`. Until those
exist, every line marked above as unverified is a lead, not a finding — the same
standard applied to the defects in `findings/`.
