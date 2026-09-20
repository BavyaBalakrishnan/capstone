# 003 — `first_response_at` never recorded on Suryodaya, so response-SLA breach is not computable

**Seat:** 15 (Helpdesk) · team15@theschoolofai.in
**Instance:** Suryodaya. Keystone is NOT affected.
**Door:** MCP `Ticket.list` / `Ticket.get`.
**Severity:** the field the response-SLA is measured against is empty on every
ticket, so the breach flag cannot be time-derived. It degenerates to a restatement
of ticket status.
**Reproduces:** all 100 tickets.

## What I did

Paged all 100 tickets and compared `first_response_at` against `response_count`
and `sla_response_breached`.

## What I expected

`first_response_at` populated wherever `response_count > 0`, and
`sla_response_breached` derived from `first_response_at` vs `sla_response_due`.

## What happened

```
first_response_at populated : 0 / 100
response_count > 0          : 66 / 100      (max observed: 51 responses)
sla_response_due parseable  : 100 / 100
```

66 tickets have recorded responses — one has 51 — and not one records when the
first response happened.

Consequently `sla_response_breached` cannot be computed from time, and in fact
correlates perfectly with status instead:

| status | breached=1 | breached=0 |
|---|---|---|
| new | 22 | 0 |
| open | 21 | 0 |
| in_progress | 26 | 0 |
| waiting_on_customer | 3 | 0 |
| on_hold | 4 | 0 |
| resolved | 0 | 4 |
| closed | 0 | 20 |

`status in {new, open, in_progress, waiting_on_customer, on_hold}` predicts
`sla_response_breached` for **100/100** tickets. The dashboard's "SLA BREACHED:
76" and "SLA BREACH RATE: 76%" are therefore both restatements of "76 tickets
are not yet resolved or closed", not a measure of response time.

This also means resolving a ticket clears its breach flag. A ticket that
genuinely breached and was then resolved reports as not breached, which is the
opposite of what SLA reporting exists to record.

## Which instance is right

Same query on Keystone, same seat:

| | Suryodaya | Keystone |
|---|---|---|
| tickets | 100 | 67 |
| `first_response_at` set | **0** | **61** |
| `response_count > 0` | 66 | 61 |
| `resolved_at` set | 4 | 41 |
| breach flag == "is active" | **True** (degenerate) | **False** |

On Keystone `first_response_at` is populated exactly where `response_count > 0`
(61/61), and the breach flag is not a restatement of status. Keystone shows the
intended behaviour.

## Why this matters for this seat

Seat 15's stated request is "tell me which will breach SLA". On Suryodaya there
is no recorded first-response time to measure against `sla_response_due`, so
neither the platform nor an agent can answer that question from the data. Any
agent that reports breach risk from this instance is reporting ticket status
with a different label.

## Notes

- Read-only. Nothing was written to either book.
- Related but separate: `sla_response_due`, `sla_resolution_due`,
  `first_response_at`, `resolved_at` and `closed_at` are all declared
  `"type": "text"` rather than a date type. Not reported here, but it is the kind
  of declaration that lets an empty or malformed timestamp pass unnoticed.
- `resolved_at` is set on 4/4 resolved tickets and `closed_at` on 20/20 closed
  tickets, so those two are consistent on Suryodaya. The gap is specific to
  `first_response_at`.
