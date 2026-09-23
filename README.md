# AgentSwitch capstone — Seat 15, Helpdesk

Team 15. Two instances: **Suryodaya** (India, GST) and **Keystone** (US, Sales &
Use Tax).

Seat 15's request: *"Triage the new tickets, draft a first response from the
knowledge base, and tell me which will breach SLA."*

## What is here

| | |
|---|---|
| [`GAP_REPORT.md`](GAP_REPORT.md) | Week-one deliverable. What commercial helpdesk products do that AgentSwitch does not, which gaps an agent can close with this seat's existing tools, and what an agent can do that those products cannot. |
| [`findings/`](findings/) | Defects found while measuring the platform. One filed and fixed; four written up. |
| [`as.sh`](as.sh) | Shell helpers for logging in and calling MCP. Reads credentials from `.env`, so the password never reaches shell history. |
| `.env.example` | Template. Copy to `.env`, which is gitignored. |

## Findings

All re-tested **2026-09-20**. Two of the original five changed status on re-test;
both are recorded rather than quietly dropped.

| | | Status |
|---|---|---|
| 001 | App boundary not enforced for `sales` — 6 of 7 sales entities readable from a Helpdesk seat on **both** instances. Root cause now visible: `roles` carries `sales_viewer` while `allowed_apps` omits `sales` | **reproduces, and has widened** — the MCP catalogue now carries the sales entities too, so the door the write-up certified as refusing no longer does |
| 002 | `Ticket.tags` stored as a list where the schema declares `text`, crashing 70 of 100 ticket detail pages | **filed** — board S9, severity High, fixed |
| 003 | `first_response_at` never recorded, so response-SLA breach is not computable; the stored flag tracks ticket status instead | **fixed on Keystone, still open on Suryodaya** (2026-09-21) — Keystone stamps 133/150 and computes breach correctly 150/150; Suryodaya stamps 1/103, leaving 24 breaches reported as compliant |
| 004 | Agent dashboard reports $6,010,165 estimated cost against 19,100 tokens | written up — **not re-tested this pass** |
| 005 | `reopen_count` holding values unreachable under the state machine (56 reopens on a ticket in `new`); `response_count` 48 against zero reply rows | **no longer reproduces** — max `reopen_count` is now 1, max `response_count` 1. Fixed or reseeded between passes. The `sender_type` limb was not re-tested |
| 006 | `AgentTask.last_run_status` holds `queued`, a value its schema does not declare (15/96); 31 `cron` rows whose `cron_expression` is a product name; Keystone's two live tasks report 30 runs with `last_run_at` null | **new** — written up |

## Method

Everything measured was pulled **read-only** over MCP and REST against both
instances, and every figure was re-derived from the saved pulls before the report
was written. **Nothing was written to either book.**

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
