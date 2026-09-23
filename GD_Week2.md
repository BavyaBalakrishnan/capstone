# GD_Week2 — Helpdesk agent scope

**Team 15 · Seat 15 (Helpdesk) · Suryodaya (India) and Keystone (US)**
**Prepared 2026-09-23. For group discussion — three decisions needed.**

This is the agenda for settling what the Helpdesk agent does, before more of it is
built. Every figure below was measured read-only against the live books on
2026-09-21 to 2026-09-23; nothing here is taken from documentation.

---

## The job, in one sentence

Once a run, the agent works through the new tickets on one book: it classifies
each, decides whether a safe knowledge-base answer exists, drafts a reply where
one does, escalates where one doesn't, and ranks the open queue by SLA breach
risk — writing everything to our own workspace and never to a ticket.

*This summarises the proposal. The details still open are in sections 4, 5 and 6.*

### What one run does

1. **Establish who it is** — instance, roles, `allowed_apps`. Nothing hardcoded to India.
2. **Pull the new queue** — every ticket in `new` (21 on Suryodaya today).
3. **For each ticket:** classify it, look for a usable article, then either draft a
   reply or escalate.
4. **Assess the open queue for SLA risk** — rank by time remaining, or state why
   that can't be done.
5. **File one finding** summarising everything, plus a to-do per ticket that needs
   a person.

### The per-ticket decision

For each new ticket, search the KB on that ticket's own words, then:

| what it finds | what it does |
|---|---|
| A published + public article, decently rated, that matches well | Draft a reply from that article and cite it |
| Articles match, but all internal, draft or archived | Escalate: *"we have the answer, it isn't publishable"* |
| The best match is public but badly rated | Escalate, and flag that article for review — don't send it |
| Nothing matches | Escalate: no KB coverage |

The escalation reasons differ deliberately, because they mean different things to
a human: one is a publishing problem, one is a content-quality problem, one is a
coverage gap.

### What it must never do

- **Send anything to a customer.** Not possible anyway — the transport is disarmed
  on both books.
- **Write to a ticket**, or to anything outside our team's own workspace.
- **Read sales data**, even though finding 001 leaves it open.
- **Draft a reply from an article that isn't publishable.**
- **Report the platform's stored SLA flag as the answer.** It is wrong on 24 of
  103 Suryodaya tickets, and wrong in only one direction — it under-reports.

---

## 1. What we are building to

The seat's assigned request:

> *"Triage the new tickets, draft a first response from the knowledge base, and
> tell me which will breach SLA."*

Three parts. Today the agent does the third fully, and the first two only in part:
it triages **one** ticket rather than the queue, and it selects an article rather
than drafting a reply. Closing that is the work this discussion scopes.

---

## 2. Facts that constrain the design

These are the reason several obvious designs are not available to us.

| fact | measured | consequence |
|---|---|---|
| **Nothing can reach a customer.** The reply transport is disarmed on both books; all 25 Keystone dispatch rows record `not_attempted_transport_disarmed` | 2026-09-20 | Whatever we build, the output is a draft for a human. "Send" is not a design option |
| **Only 10 of 100 Suryodaya articles are sendable** (`published` **and** `public`); none of the 15 shortage articles are | 2026-09-21 | "We have the answer and cannot send it" will be a common outcome, not an edge case |
| **11 of Keystone's 25 sendable articles have zero ratings** | 2026-09-23 | A simple "must be well rated" rule would reject every new product article |
| **Nobody knows who rates articles.** `helpful_count` / `not_helpful_count` are bare counters; no vote records exist anywhere in the 428 entity schemas | 2026-09-23 | Ratings are the only quality signal we have, and they are unauditable. We cannot tell who voted, when, or whether votes predate an edit |
| **SLA breach is computable on Keystone, not on Suryodaya** — `first_response_at` is populated 133/150 vs **1/103** | 2026-09-21 | The agent must decide this from the data of the book it is on, not be told |
| **21 tickets sit in `new` on Suryodaya** | 2026-09-21 | "The queue" is a real workload, not a token one |
| **Writing to a ticket writes to a book three other teams share** | brief §3 | Our output stays in our own workspace |

---

## 3. Settled so far — confirm or object

| # | decision | choice |
|---|---|---|
| S1 | How many tickets per run | **All** tickets in status `new` |
| S2 | Scope of one run | **One book per run.** Covering both is two runs |
| S3 | Where output goes | A finding in `AgentMemory`, plus to-dos. **Never** a write to a ticket or to any entity outside our own workspace |
| S4 | Article quality rule | **Three bands** — see below |

### S4, the three-band article rule

| band | test | agent behaviour |
|---|---|---|
| **Blocked** | ≥10 votes **and** under 50% helpful | Never draft from it. Flag for human review |
| **Preferred** | ≥10 votes **and** ≥70% helpful | Draft from it |
| **Unproven** | fewer than 10 votes, including zero | Usable only if nothing Preferred matches better, and the draft is marked *source not yet rated* |

Applied to today's data:

| | blocked | preferred | unproven |
|---|---|---|---|
| Suryodaya, 10 sendable | **2** | 8 | 0 |
| Keystone, 25 sendable | 0 | 12 | **13** |

The two blocked on Suryodaya are *"Quote — Deccan Fabricators Enterprises"*
(31 helpful / 59 not) and *"Complaint — Trimurti Machine Tools Engineering"*
(0 / 51).

The minimum-vote bar is **not** really about noise. With no vote records behind
the counters, more votes do not make them more trustworthy — they only make it
less likely the number came from a single incident. That is the honest
justification, and it should be stated that way rather than as "statistically
significant".

---

## 4. Open question 1 — what goes in a drafted reply?

| option | for | against |
|---|---|---|
| **A. Full reply + provenance line.** Greeting, the answer written from the article, sign-off, and a reviewer line: *"Source: <article>, rated 96 helpful / 8 not helpful; rating provenance not recorded by the platform."* | A human can send it after a glance, and knows exactly how much to trust it. Satisfies the brief's word "draft" | The model writes customer-facing prose, so it could misstate the article |
| **B. Substantive paragraph only.** The human adds greeting and sign-off | Less room for the model to go wrong | Closer to a suggestion than a first response |
| **C. No prose — quote the article extract verbatim plus its id** | The model cannot invent anything | It is a lookup, not a draft |

**Lean: A.** It is the only option that meets the request as written, and the
provenance line is honest about how weak the ratings are. If we take A, the
harness must verify that a draft cites only a sendable, non-blocked article.

---

## 5. Open question 2 — how does work reach a human?

| option | for | against |
|---|---|---|
| **A. One to-do per ticket that needs a person**, each carrying its reason: *not publishable* / *badly rated* / *no coverage* | A real backlog someone can work through. Makes the KB publishing gap visible ticket by ticket | Could be ~15 items per run on Suryodaya |
| **B. One summary to-do per run** | Quiet and tidy | Nobody can act on it without re-deriving the work |
| **C. Per-ticket for blocked or urgent, summary for the rest** | Fewer items | One more rule to agree, and one more to verify |

**Lean: A.** Those ~15 items *are* the finding from the gap report: 17 customers
asked about shortages, 15 articles exist, and none can be sent. A backlog makes
that impossible to ignore.

---

## 6. Open question 3 — does triage judge, or only report?

| option | for | against |
|---|---|---|
| **A. Judge by explicit rules, showing the stored value and the evidence.** e.g. *"stored: low — suggest high: 4th open ticket from this party this week, response deadline passed 2 days ago"* | This is our "an agent can do what their UI cannot" claim, made checkable. Rules are deterministic, so the harness can verify them and the model never invents a priority | We must agree the rules, and each needs a test |
| **B. Echo the stored type and priority** | Trivial to verify | Adds nothing over opening the ticket — and stored fields on this platform are frequently wrong |
| **C. Echo, but flag disagreements without proposing a change** | Safe | Leaves all judgement to the human |

**Lean: A**, with rules restricted to things provable from data:

1. repeat tickets from the same party inside a window,
2. a response deadline already passed,
3. stored priority contradicting the SLA policy for that ticket.

---

## 7. What the discussion needs to produce

1. **Confirm or amend S1–S4.**
2. **Pick one option** in each of sections 4, 5 and 6.
3. **If section 6 lands on A**, agree exactly which rules justify raising a
   priority, and the window for "repeat tickets".

Each choice adds harness tasks and verifiers. Agreeing them now avoids rewriting
verifiers later.

---

## 8. Context: what already exists

On branch `week1-harness-and-agent`, in `seat15/`:

- **Harness** — 7 tasks, verifiers that read the database rather than the agent's
  prose, three verdicts (`approve` / `revise` / `unevaluated`), evidence fsync'd to
  disk before scoring, and `--rescore`.
- **Agent** — a loop with 10 tools; all factual decisions in `domain.py` from live
  rows; the filed finding assembled from tool outputs so a model cannot write
  evidence into it. Two policies: a rules baseline and an LLM policy
  (`gemini-3.1-flash-lite-preview`).
- **Validation** — null agent 9/9 `revise`; verifier self-test 21/21; rules agent
  9/9 live; Gemini 6/9 on its first dry run, 9/9 after four bugs in our own tools
  were fixed. **The 9/9 is in-sample** and is not yet an independent score.

The scope decided here determines the next set of tasks: a queue-level triage
task, a draft-grounding task, and an escalation task.

---

## 9. Side item for someone to pick up

Suryodaya's two blocked articles are titled *"Quote — Deccan Fabricators
Enterprises"* and *"Complaint — Trimurti Machine Tools Engineering"*. Those read
like customer-specific records published as **public** knowledge-base articles
rather than general guidance, which would explain their ratings.

If *"Quote — Deccan Fabricators"* contains that customer's pricing and is marked
`public`, that is a data-exposure question rather than a quality one. Worth
someone opening both and checking. Potentially `findings/007`.
