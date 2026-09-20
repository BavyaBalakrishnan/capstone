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

| | | Status |
|---|---|---|
| 001 | REST does not enforce the app boundary for `sales` — 6 of 7 sales entities readable from a Helpdesk seat on **both** instances, while MCP and the UI correctly refuse | written up |
| 002 | `Ticket.tags` stored as a list where the schema declares `text`, crashing 70 of 100 ticket detail pages | **filed** — board S9, severity High, fixed |
| 003 | `first_response_at` never recorded (0/100), so response-SLA breach is not computable and the stored flag tracks ticket status for 100/100 tickets | written up |
| 004 | Agent dashboard reports $6,010,165 estimated cost against 19,100 tokens | written up |
| 005 | `reopen_count` holds values unreachable under the state machine (56 reopens on a ticket in `new`), `response_count` contradicts the conversation rows, `sender_type` is `customer` on system messages | written up |

## Method

Everything measured was pulled **read-only** over MCP and REST against both
instances, and every figure was re-derived from the saved pulls before the report
was written. **Nothing was written to either book.**

Raw pulls are deliberately **not** committed: they contain named people and
companies from books that other teams share. `out/` is gitignored.

Claims about commercial products are marked in the report with what was actually
read — primary documentation, vendor marketing, or third-party summary — because
several early claims turned out to be assumptions from a resource name rather
than a page.
