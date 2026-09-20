# 005 — Three ticket fields hold values their own rules forbid (Suryodaya)

**Seat:** 15 (Helpdesk) · team15@theschoolofai.in
**Instance:** Suryodaya. Keystone is NOT affected.
**Door:** MCP `Ticket.list` / `Ticket.get`, confirmed against the UI.
**Severity:** the ticket record cannot be trusted for triage or reporting.
**Status:** written up, NOT filed.
**Reproduces:** every read.

## What I did

Paged all tickets on both instances (Suryodaya 100, Keystone 67) and compared the
stored values against the `Ticket` schema and the `TicketFlow` state machine in
`/api/schemas`.

## What I expected

Values consistent with the declared schema and reachable under the state machine.

## What happened

### (1) `reopen_count` holds values unreachable under the state machine

`TicketFlow` defines Reopen only as `resolved -> open` and `closed -> open`. A
ticket in `new` has never been resolved or closed, so it cannot have been
reopened even once.

- **17 of the 21 tickets in status `new` have `reopen_count > 0`**
- worst case: "Rajkot despatch, week 36" — status `new`, `reopen_count` **56**,
  `response_count` 0
- "Order — Balaji Springs Udyog" (`9e284e4b-ac17-4b68-956b-25c060e3f2ce`) —
  status `new`, `reopen_count` 34, shown as "34 Reopened" in the UI STATS panel
- max `reopen_count` by status: new 56, open 59, on_hold 58, resolved 57,
  closed 51 — distributed at random rather than counting anything

Keystone's highest `reopen_count` on any ticket is **1**.

### (2) `response_count` contradicts the ticket's own conversation rows

The same ticket stores `response_count` **48** but carries only 3 conversation
rows: two `type=system`, one `type=note`, and **zero `type=reply`**.

The UI STATS panel correctly shows "0 Replies". The stored counter says 48. The
screen and the stored field disagree about the same ticket.

### (3) `sender_type` is wrong on system-generated messages

All three conversation rows on that ticket carry `sender_type: "customer"`,
including the two with `type: "system"`. Two also have `sender: null`.

An agent reading the thread cannot distinguish text written by the customer from
text the platform generated itself. For this seat that matters more than it
looks: customer-authored text is untrusted input, and the `sender_type` label is
what an agent would use to decide how to treat it.

## Which instance is correct

| | Suryodaya | Keystone |
|---|---|---|
| tickets | 100 | 67 |
| `new` tickets with `reopen_count > 0` | **17 of 21** | 0 |
| highest `reopen_count` anywhere | **59** | **1** |
| `first_response_at` populated | 0 | 61 |
| `tags` stored as declared `text` | 0 of 100 | 66 of 67 |

## Why these look like one cause

Several unrelated fields are wrong on Suryodaya and correct on Keystone, in ways
that all resemble randomly generated values ignoring the entity's own rules. The
same pattern appears outside `Ticket`: 5 of 6 `SLA` policies carry product names
in `business_hours_start`, `apply_to_channel` and `levels[].priority`, with
`response_hours` up to 1,823; `Escalation` has `level: 1764.1`; all 100
`TicketTag` rows are named after products with `color: "File Set 5459"` and
`ticket_count: 0`, while tickets actually use sensible tags like `rework` and
`audit`. A single seed or generation path for Suryodaya seems the likely common
cause.

Only "OEM Customer SLA" is sane, and fortunately it is the default, so tickets do
get correct deadlines (09:00–18:00 Mon–Fri; urgent 1h/8h, high 4h/24h, medium
8h/72h, low 24h/120h — and the clock correctly skips weekends).

Related and already fixed: `tags` stored as a list where the schema declares
`text` — bug-report `5442dba1-4696-4ae8-8000-a74187c59f69`, board S9.
Related and separate: `first_response_at` never recorded — `findings/003`.

## Notes

- Read-only throughout. Nothing was written to either book.
- `page: Support:Home/all_tickets/Ticket/9e284e4b-ac17-4b68-956b-25c060e3f2ce`,
  `agent_seat: Helpdesk`
