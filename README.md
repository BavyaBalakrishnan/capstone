# AgentSwitch capstone — Seat 15, Helpdesk

Team 15. Two instances: **Suryodaya** (India, GST) and **Keystone** (US, Sales &
Use Tax).

Seat 15's request: *"Triage the new tickets, draft a first response from the
knowledge base, and tell me which will breach SLA."*

## What is here

| | |
|---|---|
| [`seat15/harness/`](seat15/harness/) | **The evaluation harness.** 20 tasks, 17 checkers, 6 fixtures, a two-arm experiment runner. Every checker reads the database; none reads the agent's prose. |
| [`seat15/agent/`](seat15/agent/) | **The agent.** One loop, a fixed tool set, two policies — a fixed script and a model — over the same tools. All factual decisions live in `domain.py`, with no model in that file. |
| [`tests/`](tests/) | 21 unit tests, hand-written by the team, not generated. |
| [`HARNESS_STATUS.md`](HARNESS_STATUS.md) | **Start here for the harness.** What it does, what it has caught, what is still open. Written for someone who has not seen the code. |
| [`proofs/`](proofs/) | Sanitised run summaries and experiment results. Verdict reasons are stripped: they quote ticket subjects and article titles from books other teams share. |
| [`GAP_REPORT.md`](GAP_REPORT.md) | Week-one deliverable. What commercial helpdesk products do that AgentSwitch does not, which gaps an agent can close with this seat's existing tools, and what an agent can do that those products cannot. |
| [`findings/`](findings/) | Nine defects found while measuring the platform. One fixed at the root, two filed on the platform's own bug board, six written up. |
| [`as.sh`](as.sh) | Shell helpers for logging in and calling MCP. Reads credentials from `.env`, so the password never reaches shell history. |
| `.env.example` | Template. Copy to `.env`, which is gitignored. |

## Findings

Re-tested **2026-09-20**, and 001 re-tested again **2026-10-03** when a harness
task reported *"premise gone"*. Three have changed status since first being
written; every change is recorded rather than quietly dropped, because a defect
report that silently updates itself cannot be audited.

| | | Status |
|---|---|---|
| 001 | App boundary not enforced for `sales` — at its worst, 6 of 7 sales entities readable from a Helpdesk seat over all three doors. Root cause: `roles` carried `sales_viewer` while `allowed_apps` omitted `sales` | **FIXED 2026-10-03** — `sales_viewer` removed, all six now refuse on both instances. **`Item` is still readable and writable** and is in the same app. Four state changes in three weeks; the harness caught the fix itself, as *premise gone* |
| 002 | `Ticket.tags` stored as a list where the schema declares `text`, crashing 70 of 100 ticket detail pages | **filed** — board S9, severity High, fixed |
| 003 | `first_response_at` never recorded, so response-SLA breach is not computable; the stored flag tracks ticket status instead | **fixed on Keystone, still open on Suryodaya** (2026-09-21) — Keystone stamps 133/150 and computes breach correctly 150/150; Suryodaya stamps 1/103, leaving 24 breaches reported as compliant |
| 004 | Agent dashboard reports $6,010,165 estimated cost against 19,100 tokens | written up — **not re-tested this pass** |
| 005 | `reopen_count` holding values unreachable under the state machine (56 reopens on a ticket in `new`); `response_count` 48 against zero reply rows | **no longer reproduces** — max `reopen_count` is now 1, max `response_count` 1. Fixed or reseeded between passes. The `sender_type` limb was not re-tested |
| 006 | `AgentTask.last_run_status` holds `queued`, a value its schema does not declare (15/96); 31 `cron` rows whose `cron_expression` is a product name; Keystone's two live tasks report 30 runs with `last_run_at` null | **new** — written up |
| 007 | `KBArticle.helpful_count` and `not_helpful_count` are writable by any client that can update an article, and no entity records the individual votes behind them. The only quality signal an answering agent has cannot be audited | written up — **the write was deliberately not attempted**, so this is read from the schema rather than proven by abuse |
| 009 | A ticket with no SLA deadline is recorded as `not breached` — the same value a ticket gets for being answered on time, so unmeasured is indistinguishable from compliant | **LOW, not filed** — 2 tickets, both our own probes, no customer ticket affected. Our first explanation (only the default policy sets deadlines) was **wrong** and is retracted in the report: Keystone runs 100 tickets on five non-default policies with no deadlines missing |
| 008 | **An empty reply stamps `first_response_at` and counts as a response.** On `TKT-2026-00103` the first-response timestamp matches an empty-bodied reply to the microsecond. Response SLA can therefore be satisfied without answering anyone | **FILED 2026-10-03** — `BugReport` `0a7bf46b`. Proven from evidence already on the platform; no new write was made |

## Running it

Credentials come from **environment variables first, `.env` second**, so a
deployment can inject them and never write a file:

```
AS_EMAIL, AS_PASSWORD_SURYODAYA, AS_PASSWORD_KEYSTONE
SEAT15_LLM_BASE_URL, SEAT15_LLM_MODEL, SEAT15_LLM_API_KEY   (only for --agent llm)
```

```bash
cp .env.example .env          # or set the variables above; either works
pip install pytest            # the harness itself needs no third-party packages

python -m pytest tests/ -q                       # 21 hand-written unit tests
python -m seat15.harness.selftest                # 47 checker self-tests
python -m seat15.harness.runner --agent rules    # the whole suite, no model needed
python -m seat15.harness.runner --agent null     # a do-nothing agent: must fail everything
python -m seat15.harness.runner --agent llm      # the same suite, model-driven
python -m seat15.harness.grid --arms rules,llm   # both, and which tasks tell them apart
```

### Verifying it without credentials

**Eight of the twenty tasks are fixture-backed and need no `.env`, no network
and no API key.** On a fresh clone, these two commands are the whole proof:

```bash
python -m pytest tests/ -q                                    # 21/21
for t in b01 c01 g01 p01 r01 r02 r03 t01; do     python -m seat15.harness.runner --agent rules --task $t; done   # 8/8 approve
```

Then the check that matters more — the do-nothing agent, which **every** task
must fail. A checker that cannot fail an agent that did nothing is testing its
own assumptions:

```bash
for t in b01 c01 g01 p01 r01 r02 r03 t01; do     python -m seat15.harness.runner --agent null --task $t; done   # 8/8 revise
```

The remaining twelve tasks run against the live platform and need `.env`.

**The number worth reading is not the pass rate.** It is which tasks separate the
two arms. A task both arms pass tells you the task is not discriminating, not
that both agents are good. `HARNESS_STATUS.md` section 8 explains why most of
ours do not.

## What this writes

The week-one gap report was produced entirely read-only. **The agent is not.** It
writes to two entities, both inside this team's own `agent` workspace, and the
client refuses writes to anything else in code:

| Entity | Why | Reversible? |
|---|---|---|
| `AgentMemory` | One row per run holding the finding the harness grades. Evidence, not output. | Yes — ordinary rows |
| `AgentTodo` | One to-do per ticket the agent could not answer, so a human sees it | **No.** This platform allows create and update but **not delete.** A row can be cancelled, never removed |

Because to-dos cannot be deleted and the book is shared with other teams, the
agent **deduplicates before filing**: a ticket that already has a to-do nobody
has finished with is skipped. Three runs in a row file three rows, not nine, and
`t01_todos_not_duplicated` is the task that proves it.

Nothing is written to `Ticket`, `KBArticle` or any customer-facing field. The
agent drafts replies and files them as evidence; sending them is a team decision
that has not been taken (`GD_Week2` Q9).

## Method

Everything in the **gap report** was pulled read-only over MCP and REST against
both instances, and every figure was re-derived from the saved pulls before the
report was written. Nothing was written to either book for that work.

The **agent** does write, to the two entities listed above. See "What this
writes".

Figures were re-pulled and recomputed on **2026-09-20**, the submission date,
rather than carried over from the first pass. These books are shared, and they
moved: Suryodaya tickets 100 → 103, `AgentJob` 973 → 1227, `SupportAgentProfile`
0 → 7, Keystone's reply ledgers 0 → 196, and two limbs of finding 005 stopped
reproducing. The gap report lists every claim retracted as a result.

Raw pulls are deliberately **not** committed: they contain named people and
companies from books that other teams share. `out/` is gitignored.

Claims about commercial products are marked in the report with what was actually
read — primary documentation, vendor marketing, or third-party summary — because
several early claims turned out to be assumptions from a resource name rather
than a page.
