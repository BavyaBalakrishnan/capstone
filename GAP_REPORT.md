# Gap report — Seat 15, Helpdesk

**Team 15 · team15@theschoolofai.in · Suryodaya (India) and Keystone (US)**
**Status: DRAFT.** Side A (what AgentSwitch has) is measured and verified. Side B
(what the commercial products have) needs the trial and the docs, which is mine
to do — see the TODO markers.

Products chosen for comparison:

| Product | Why | Studied? |
|---|---|---|
| **Pylon** (usepylon.com) | B2B, Slack-native, account-level context, MCP **with write actions**, and "Skills" = reusable plain-English instructions for agents | TODO — trial + docs |
| **Lorikeet** (lorikeetcx.ai) | Regulated industries, sells on *"provable behaviour and audit trails"* — the standard to measure our agent against | TODO — read the audit/provability docs |
| **Decagon** (decagon.ai) | "Agent Operating Procedures" — a third product converging on plain-language agent instructions | TODO — 20 min |

Rejected: **Intercom Fin** — market leader, but its MCP server is read-only (6
tools, no replies, no ticket updates). Kept as a contrast case, not a benchmark.
**Plain** — appears mainly in its own marketing; did not survive neutral rankings.
**Zendesk / Freshdesk / Front / Help Scout / HubSpot** — no MCP server at all;
the "twenty-year-old product with a chatbot bolted on" case.

---

## 1. What do they do that we do not?

### 1.1 Spotting trends and patterns in incoming tickets — CONFIRMED GAP

**Them.** Fin surfaces what customers are asking about most — "AI topics" and
trends — as an input to improving the product and the docs. [SOURCE: Fin's own
sales material, quoted in §1.2. Pylon's site lists "Analytics & reporting" but I
have not read the page; do not attribute topic analysis to Pylon until I have.]

**Us.** The Helpdesk dashboard has six counters — open, unassigned, urgent, SLA
breached, resolved, closed — plus CSAT and breach rate. Nothing groups tickets by
topic, nothing surfaces what recurs, nothing recommends an action. That is
reporting, not insight.

**Bucket: ORCHESTRATION — mine to build.** Demonstrated read-only in a single
pass using only tools this seat already has (`Ticket.list`, `KBArticle.list`). No
new tables or endpoints required.

Measured on Suryodaya, 100 tickets and 100 KB articles:

```
demand by type                    demand by topic (words in subjects)
  question         19               despatch   26
  complaint        17               line       20
  other            15               shortage   17
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

Only **10 of 100** KB articles are `published` + `public`. The rest are draft,
`in_review`, archived, or `internal`/`agents_only`.

So: 17 customers have asked about shortages, the company has written 15 articles
about shortages, and **not one of them can be sent to a customer.** Every one of
those tickets needs a human to rewrite an answer that already exists.

That is the difference between a trend and an insight. A dashboard says
"despatch is your top topic". The useful statement is "you are re-answering
shortages by hand 17 times because the answers are locked internal — publish
them and 17 tickets become self-serve."

### 1.2 Scorecards, monitors and recommendations — CONFIRMED GAP

**Them.** Fin sells these three together as a **Pro add-on, $99/month per 1,000
conversations**:

- **Custom AI scorecards.** You write your own rubric — acknowledged in SLA,
  order number confirmed, a date given rather than "soon", tone right for an OEM
  customer — and every conversation is graded against it, rather than the sample
  a human reviewer could get through by hand.
- **Monitors.** A standing condition that alerts when it trips: refund questions
  up 40% week on week, CSAT on billing below 70%, the AI answering a question
  differently than it did last week. This is what "catch emerging issues before
  they impact customer experience" means in practice — a new product defect
  usually appears as a spike in one topic hours before anyone files it as a bug.
- **AI recommendations.** Not a chart, an instruction: *"27 conversations last
  week asked about the return window and no help article covers it — write one."*
  *"This article is cited often and marked not-helpful 40% of the time — rewrite
  it."*

Note the relative pricing: Pro is $0.099 per conversation while the Copilot
add-on, which actually helps an agent answer, is $35 per 5,000 — $0.007.
**Measuring the agent costs 14x more per conversation than assisting it.** A
vendor's pricing page is the clearest statement of what it thinks is hard.

**Us.** None of the three. The Helpdesk dashboard has six counters and a CSAT
percentage. Nothing grades a conversation, nothing watches for a change, nothing
recommends an action.

**Bucket: ORCHESTRATION — mine to build**, with one caveat per item.

| | what it needs | state on our side |
|---|---|---|
| Recommendations | `Ticket.list` + `KBArticle.list` | **already demonstrated** — see §1.1 |
| Scorecards | read conversations, grade against a rubric | tools exist; needs a rubric and a scorer |
| Monitors | run a check on a schedule | the Agent dashboard reports **0 scheduled tasks**; `AgentTask` holds 96 rows, all `completed`, and `AgentRunbook` holds 0 |

The last row is the interesting one. The platform ships a scheduler and a job
ledger — `AgentJob` holds 973 rows — and **nothing is scheduled on it**. A
monitor is a scheduled check with a threshold, so the substrate is present and
unused rather than missing.

### 1.3 Nothing can connect two tickets to each other — CONFIRMED GAP

**Them.** Pylon exposes **Feature Requests** as a first-class API resource,
separate from Issues. A customer saying "it would be good if it did X" becomes an
object that persists, accumulates the other customers asking for the same thing,
and carries a count to the product team. Pylon also exposes **Teams**, so work
groups exist as records rather than strings.

**Us.** Swept all 424 entity schemas for `featurerequest | idea | roadmap | vote |
enhancement | suggestion | backlog | productfeedback`. One match —
`MeetingPollVote`, in `scheduling`, about choosing meeting times. There is no
feature-request object in the platform. The only representation is
`Ticket.type = 'feature'`, which is 13 tickets on Suryodaya that get answered and
closed like any other.

The sharper finding is underneath it. `Ticket` has **32 fields and not one of
them links to another ticket** — no parent, no merge, no duplicate, no related.

That is not because the platform lacks the pattern. **21 other entities** carry a
`parent_*`, `related_*` or `linked_entity` field, including:

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
  mine**. It needs only `Ticket.list` plus the topic analysis already
  demonstrated in §1.1, and it can be reported to a human.
- **Persisting** that relationship is **platform**. Without a parent or related
  field on `Ticket`, or a feature-request object to promote them into, an agent
  can find the pattern and cannot record it. The finding dies when the run ends.

That distinction is worth stating plainly: an agent here can produce the insight
but has nowhere to put it, which caps what repeated analysis can ever be worth.

### 1.4 Other gaps — measured, bucket assigned

| Gap | Evidence on our side | Bucket |
|---|---|---|
| **Multi-channel intake** (Pylon: 8+ — Slack, Teams, email, SMS, WhatsApp, phone) | `Ticket.channel` has 6 options and tickets carry values, but `TicketReplyDispatch.transport` is `none_configured` and all three dispatch ledgers hold **0 rows**. Nothing has ever been sent or received through a live channel. | **Platform** |
| **Third-party integrations** (Pylon: 25+ — Salesforce, HubSpot, Linear, Jira) | none | **Platform** |
| **Workforce management / capacity routing** | `SupportAgentProfile` holds **0 rows**. No roster exists, so `required_skill` and `max_open_tickets` cannot be used. Tickets carry `assigned_to` UUIDs that resolve to nothing — which is why the UI renders a raw id. | **Platform** (data) |
| **Account-level context for B2B** — Pylon's core pitch | `crm` is in this seat's `allowed_apps`, but only **1 of 8** crm entities is in the tool catalogue (`CRMPreferences`), and that only via the `viewer` role, which the Keystone seat does not hold. No `AccountPlan`, no `Pipeline`, no `Goal`. The "shared customer spine" is nearly empty for a Helpdesk seat. | **Platform** |
| **Intent / sentiment classification** | `Ticket.type` and `priority` are manual `select` fields. No classifier. | **Platform** (needs a model) |
| **CSAT loop** — Pylon has a `Surveys` API resource [VERIFIED: listed in Pylon's API reference index; I have not read the page] | `satisfaction_rating` and `satisfaction_comment` exist as fields; no survey object and no transport to send one with. On Suryodaya the field is populated anyway — **22 tickets still in `new` carry a rating**, so 92 of 100 are rated while only 24 have reached `resolved` or `closed`. Keystone rates 28 of its 30 on `closed`. | Platform to collect, **orchestration** to act on |
| **Duplicate / merge detection** | no parent, merge, duplicate or related field on `Ticket` — see §1.3 | Detect: **orchestration**. Persist: **platform** |
| **Breach-risk triage across the queue** | data is present (`sla_response_due`, priority, status) | **Orchestration — mine** |
| **A call object** — Pylon's `Call Recordings` carries title, summary, participant emails, duration, source platform and URL [VERIFIED: docs page read. Pylon stores no audio itself — it indexes recordings held on Gong, Fathom, Grain etc., and has **no create or upload endpoint**] | No call object of any kind. **18 tickets record `channel: phone`** and nothing captures who was on the call, how long it ran, or what was agreed. `CallNoteDraft` exists in `crm` and is not reachable from this seat. | **Platform** |
| **Integrations to populate a call record** (Gong, Fathom, Grain) | none | **Platform** |
| **Teams as records** — Pylon exposes `Teams` [VERIFIED: listed in API reference index; page not read] | `Ticket.assigned_group` is `type: text`. On Suryodaya it holds **69 distinct values across 68 tickets**, almost all product names appearing once; Keystone holds **4** (Customer Service, Quality, Finance). `required_skill` is also free text — 65 distinct values on Suryodaya, 1 on Keystone. A record would have refused those writes; a string accepted every one. | **Platform** |

**NOT gaps — checked and found present.** Recorded here so they are not claimed by
mistake:

| Claimed gap | Why it is not one |
|---|---|
| Knowledge model | `KBArticle` matches Pylon's Training Data resource closely, including the same three-way visibility split (`public`/`internal`/`agents_only` vs `everyone`/`user_only`/`ai_agent_only`). |
| Forms | `Form` (`domain: forms`) has `blocks`, `logic_rules` (Pylon's conditional logic), `presentation_mode`, and `consent_lawful_basis` carrying all six GDPR bases — richer than Pylon's ticket-forms page describes. The gap is that **nothing links a form to a ticket**: `Ticket` has no form reference and `FormResponse` has no ticket reference, while 17 tickets record `channel: portal`. Forms also belong to seat 25, so reaching them is an escalation, not a defect. |
| Attachments | `FileAttachment` plus the `Drive*` family — versioning, sharing, access logs, retention policy, legal hold — is a richer document layer than Pylon's. |
| Audit trail | `endpoint.job_ledger.verify` / `.replay` / `.forensics` exist and are in this seat's catalogue. |
| Testing a skill before deploying it | `endpoint.agent_governance.skill_sandbox` accepts `candidate_markdown`. Fin sells the equivalent inside its $99/month Pro add-on. |

**Remaining gaps in knowledge handling** (narrower than "we have nothing"):
ingestion — Pylon can crawl a docs site and upload PDF, CSV, markdown and images
up to 50MB, while every `KBArticle` must be hand-written; and freshness — Pylon
records `scrape_status` with `last_scraped`, while `KBArticle` has only
`updated_at`, which says when someone edited it, not whether it is still true.

TODO after the Pylon trial: confirm each "them" claim against the actual product
rather than its marketing page, and add anything found that is not listed here.

---

## 2. Which of those gaps can an agent close with the tools this seat already has?

**Mine to build, today, no platform change:**

1. **Topic and demand analysis** — §1.1, already demonstrated.
2. **KB coverage gap analysis** — cross demand against *sendable* articles and
   name which articles need publishing. This is the §1.1 table.
3. **Breach-risk triage** — walk the open queue, compute time remaining against
   the real SLA policy (OEM Customer SLA: 09:00–18:00 Mon–Fri; urgent 1h/8h,
   high 4h/24h, medium 8h/72h, low 24h/120h), rank by risk, act.
4. **Escalation follow-through** — the escalation engine fires correctly but
   nothing downstream acts on it. TKT-2026-00099 had level 1 fire at 12h and
   level 2 at 48h and was still sitting in `new` three days past its response
   deadline. An agent can close that loop.
5. **Repeat-customer detection** — Kirloskar Pumps Ltd has 4 open tickets.
   Group by party, read what was promised in each, draft one escalation with
   the evidence attached.
6. **Duplicate and repeat-request detection** across the shared book — but
   reporting only. Per §1.3 there is no field on `Ticket` to record the
   relationship, so the agent can surface the grouping and cannot persist it.
7. **Ticket → article loop.** `KBArticle.source_ticket_id` exists and is unused.
   After solving a ticket, draft the missing *public* article from it.

**Platform work, not mine:** live channel transport, integrations, a support
agent roster, the missing crm entities, any classifier.

---

## 3. What can an agent do that their product cannot?

### 3.1 We are ahead of the market leader on agent drivability

Only four support platforms ship an official MCP server in 2026: Pylon, Intercom,
Plain and Drag. The incumbents ship none.

| | tools exposed | agent can act? |
|---|---|---|
| **AgentSwitch, this seat** | **230** | **yes** — create, update, workflow transitions |
| Intercom MCP | 6 | **no** — read-only; cannot reply or update a ticket |
| Pylon MCP | TODO | yes |

On the one axis this capstone cares about — *can an agent actually drive the
system?* — AgentSwitch is ahead of Intercom, which is the market leader in AI
customer support. That is worth stating plainly because gap reports rarely can.

### 3.2 What the pricing pages say about the standard

Fin (Intercom) prices in two currencies at once: **$39 / $99 / $139 per human
seat per month**, and **$0.99 per outcome** for the AI agent, with a 50-outcome
monthly minimum. [VERIFIED: Fin's own sales material.]

The wider picture is weaker-sourced and should be stated as such. Lorikeet is
reported at about **$0.80 per resolution**, Sierra as outcome-only, Decagon at
**$95K–150K/year** — all three from **Lorikeet's own comparison pages**, which
rank Lorikeet first, so treat them as leads rather than facts. **Pylon publishes
no pricing at all**: its pricing URL is a demo booking form [VERIFIED: page
fetched]. So the honest claim is that at least two vendors publish
per-resolution pricing and a third is reported to, not that the market has
converged.

That convergence is the useful signal, because **you cannot bill per outcome
unless you can prove an outcome occurred.** To charge $0.99 with confidence a
vendor needs a definition of "resolved", evidence that it happened, and a rule
for not charging when it did not. That is a verification requirement, not a
feature.

Which makes AgentSwitch's dispatch vocabulary worth reading again:
`attempt_outcome_unknown`, `unknown_possibly_delivered`,
`unknown_possibly_sent`. **None of those could honestly be billed.** The platform
already models the uncertainty that makes outcome-based pricing hard, and has
never emitted a single row of it. An agent built here should record which of
those states it ended in, because that is the difference between a claimed
resolution and a proven one.

Architecturally, Fin also sells as an AI layer over *someone else's* helpdesk
(Salesforce and others) rather than only inside Intercom. That is the same shape
as this capstone — an agent running separately and driving the platform over its
API — so the assignment's architecture matches where the market leader landed.

### 3.3 The reply pipeline is built for provable agent behaviour, and has never run

Lorikeet sells on *"provable behaviour and audit trails"*. AgentSwitch already
models it, in three ledgers:

- `TicketReplyDelivery` — the decision. Records `audience`
  (`customer_facing` | `internal_note`), `grounding_state`
  (`none_claimed` | `published_kb_only` | `grounding_unverifiable`),
  `body_fingerprint`, `thread_binding`, `recipient_source`.
- `TicketReplyDispatchClaim` — a lease (`claim_token`, `lease_expires_at`,
  `claim_count`) so the same reply cannot be sent twice.
- `TicketReplyDispatch` — the attempt, with a vocabulary that separates "did not
  try" from "tried and failed" from "do not know":
  `not_attempted_no_transport`, `not_attempted_body_unverifiable`,
  `attempt_failed`, `attempt_outcome_unknown`, `transport_accepted`, and
  resolutions including `refused_body_changed` and `unknown_possibly_delivered`.

`body_fingerprint` plus `refused_body_changed` is time-of-check-to-time-of-use
protection: approve a body, and if the text changes before the send, the send is
refused. That is the mentor's "re-read before you act" rule enforced in code.

**All three ledgers hold 0 rows.** Every one of those outcome codes is an
untested zero. Driving this pipeline correctly, and writing tests that prove the
`published_kb_only` and `refused_body_changed` guards actually hold, is the
strongest thing available to build on this seat.

### 3.4 The whole-thread move

Their software makes a support engineer fast; a human still drives every step.
The agent takes one sentence — *"Kirloskar says nothing has worked all week"* —
and works the thread alone: finds every ticket from that party, checks which
deadlines passed and by how much, reads what was promised in each, identifies the
pattern across them, checks whether a public article exists to answer it, and
drafts the escalation with evidence attached. Nobody opens twelve tabs.

This is the sustenance-engineering week I do at Infoblox, automated.

### 3.5 Honest limits on this instance

Parts of this seat's assigned request are constrained by data and permission
defects found while measuring the above:

- `first_response_at` is null on all 100 tickets on Suryodaya, so response-SLA
  breach cannot be computed from data; the stored flag correlates with ticket
  status for 100/100 tickets. An agent must say so rather than report status
  under a different name. **Written up, not yet filed** (`findings/003`).
- `tags` was stored as a list where the schema declares `text`, crashing 70 of
  100 ticket detail pages. **Filed** — bug-report
  `5442dba1-4696-4ae8-8000-a74187c59f69`, class board S9, severity High, fixed
  and pending deploy.
- `reopen_count` holds values unreachable under the state machine (56 reopens on
  a ticket in `new`), `response_count` reads 48 on a ticket with zero reply rows,
  and `sender_type` is `customer` on system-generated messages. **Written up, not
  yet filed** (`findings/005`).
- REST does not enforce the app boundary for `sales`: 6 of 7 `sales` entities are
  readable from this seat on **both** instances, while MCP and the UI correctly
  refuse. **Written up, not yet filed** (`findings/001`).

Keystone is unaffected by the first three. The REST defect is present on both.

---

## Method, and how far each claim can be trusted

**Everything on our side is measured.** All figures were pulled read-only over
MCP and REST against both instances, not taken from documentation, and every
number in this report was re-derived from the saved pulls before submission.
Nothing was written to either book. Raw data is in `out/`; the defects referenced
are written up in `findings/`.

**Their side is not all equal, and pretending otherwise would undermine the
rest.** Three tiers:

*Primary source, page actually read:*
Pylon's API reference index (23 resources); Pylon Training Data (6 endpoints,
three-way visibility, `scrape_status`, 50MB uploads); Pylon Ticket Forms
(customer-facing, conditional logic, `POST /ticket-forms/{id}/submissions`
creates the issue); Pylon Call Recordings (indexes third-party recordings, no
upload endpoint); Pylon publishes no pricing; Fin's pricing and add-on structure,
from Fin's own sales material.

*Vendor marketing page, read but self-described:*
Pylon's "Skills", Assist Agent, Background Agent, 8+ channels, 25+ integrations.

*Third-party or competitor-sourced, NOT independently verified:*
"Intercom's MCP is read-only with 6 tools"; "only four support platforms ship an
MCP server"; Pylon's MCP tool list; Lorikeet, Sierra and Decagon pricing. The
four-platform claim comes from a vendor blog that lists itself among the four.
The Lorikeet/Sierra/Decagon figures come from Lorikeet's own comparison pages.

**The single most load-bearing unverified claim** is that Intercom's MCP server
cannot take write actions, since §3.1 rests on it. It should be confirmed against
`developers.intercom.com` before this report is relied on.

**Still outstanding:** the Pylon trial, Pylon's MCP tool list, and Pylon's
pricing. Until those exist, every "them" line marked above as unverified is a
lead, not a finding — the same standard applied to the defects in `findings/`.
