# 002 — Ticket detail page crashes on 70 of 100 tickets (Suryodaya)

**Status:** REPORTED 2026-09-16 13:24 · bug-report id `5442dba1-4696-4ae8-8000-a74187c59f69`
**Seat:** 15 (Helpdesk) · team15@theschoolofai.in
**Instance:** Suryodaya. Keystone is NOT affected.
**Door:** web UI, confirmed against MCP.
**Severity:** the primary screen of this seat's primary app is unusable for 70% of records.
**Reproduces:** every affected ticket, every load.

## What I did

Opened a ticket from All Tickets in the Helpdesk UI:

```
/v/Support:Home/all_tickets/Ticket/37d240f7-3109-4e66-b76d-bba8a9458c91
"Bench Vice — shift handover"  (status: waiting_on_customer)
```

## What I expected

The ticket detail page.

## What happened

```
This screen hit an error
o.tags.split is not a function
```

The page renders nothing. The ticket cannot be read, triaged or actioned
through the UI at all.

## Root cause

`Ticket.tags` is declared `"type": "text"` in `/api/schemas`. The UI calls
`.split()` on it, which is correct for a string.

On Suryodaya the field is not a string. Via MCP `Ticket.get`:

```json
"tags": ["rework", "export"]     // a list
```

Across all 100 tickets on Suryodaya (`Ticket.list`, paged):

| tags value | count |
|---|---|
| list | **70** |
| null | 30 |
| string | **0** |

Not one ticket stores `tags` as the declared type. The 30 that render are the
ones where `tags` is null, so `.split()` is never reached — which is why the
first ticket I opened (TKT-2026-00099) worked and misled me into thinking the
screen was fine.

## Which instance is right

Same query on Keystone, same seat:

| | Suryodaya | Keystone |
|---|---|---|
| `tags` is list | 70 | **0** |
| `tags` is string | **0** | 66 |
| `tags` is null | 30 | 1 |

Keystone stores `tags` as the schema declares, and its ticket pages work.
So this is not a UI bug in isolation: **Suryodaya's ticket rows violate the
schema the UI was written against.**

Either the UI should tolerate both shapes, or Suryodaya's `tags` column should
hold the declared type. Keystone demonstrates the intended shape.

## Affected tickets (first five of 70)

```
Aluminium extrusion shortage on the scriber line   open         ["rework"]
Aurangabad despatch, week 20                       closed       ["urgent"]
Latur despatch, week 31                            in_progress  ["urgent"]
File Set — despatch hold                           open         ["audit"]
Complaint — Yashwant Alloys Industries             open         ["rework"]
```

## Notes

- Read-only throughout. Nothing was written to either book.
- The API path is unaffected — `Ticket.get` and `Ticket.list` return these rows
  fine. Only the UI breaks, which is why an agent driving MCP would never
  notice, and a human would be blocked immediately.
- `page: Support:Home/all_tickets/Ticket/<id>`, `agent_seat: Helpdesk`
