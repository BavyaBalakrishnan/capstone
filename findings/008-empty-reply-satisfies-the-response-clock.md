# 008 — An empty reply stamps `first_response_at` and counts as a response

**Seat:** 15 (Helpdesk) · team15@theschoolofai.in
**Instance:** Suryodaya (observed). Keystone not re-tested — see Notes.
**Door:** REST `/api/Ticket` and the web UI.
**Severity:** the only evidence that a customer was answered can be created
without answering them. Every response-SLA number on the platform is computed
from a field that an empty string can set.
**Status:** **FILED 2026-10-03 11:02** · `BugReport` id
`0a7bf46b-8203-4b8a-91f7-c3ebc7661a96` · delivery `filed` · status `new`.
**No new write was made to demonstrate this** — see Notes.
**Reproduces:** the evidence is already on the platform, on `TKT-2026-00103`.

## What is wrong

A ticket reply with an empty body is accepted, is rendered in the conversation
thread as a reply from its sender, increments `response_count`, and — the part
that matters — **sets `first_response_at`**.

`first_response_at` is what "did we answer in time" is measured against. So a
reply containing nothing satisfies the response SLA exactly as well as a real
answer.

## Evidence

`TKT-2026-00103` on Suryodaya, read read-only on 2026-10-03:

```
first_response_at      2026-09-27T06:20:50.895792
first reply created_at 2026-09-27T06:20:50.895792     <- identical
that reply's body      ''                             <- length 0
response_count         2.0
sla_response_due       2026-09-23T09:30:00
sla_response_breached  1
```

The timestamps are identical to the microsecond, so the empty reply is
unambiguously the event that stamped the clock.

Across the 15 Suryodaya tickets that carry any conversation at all, 30 entries
exist and **2 have an empty body** — both on this ticket.

In the UI those two appear as two reply cards attributed to "Team 15" with no
text in them. A human reading the thread sees two replies that say nothing; the
SLA machinery sees a ticket that was responded to.

## Why this matters beyond a typo

This platform's response-SLA story already has a defect — `findings/003`,
`first_response_at` is never recorded on Suryodaya, so breach is not computable.
008 is the other half of the same problem. Where the field *is* recorded, it can
be set by something that is not an answer.

Taken together: on one instance the response clock is never started, and on both
it can be started by an empty string. A metric that can be satisfied without
doing the work is worse than a missing metric, because it looks like evidence.

For an agent this is sharper still. An agent that is permitted to reply, and is
measured on response SLA, has a trivially available action that scores perfectly
and helps nobody. **This is the reason our agent does not send.** Its drafts are
filed as evidence with a citation line, and whether it may write to a customer
field is still an open team decision (`GD_Week2` Q9). The platform currently has
no check that would stop a careless agent from "responding" 21 times with
nothing and reporting a clean SLA.

## Suggested fix

Reject a reply whose body is empty after whitespace and markup are stripped, at
the same place that sets `first_response_at`. If empty replies must be allowed —
for an attachment-only reply, say — then `first_response_at` and
`response_count` should ignore them, and the thread should render them as
something other than a reply.

Related: `conversations[].attachments` arrives as the **string** `"[]"` rather
than an empty list, the same declared-type defect as `findings/002`
(`Ticket.tags`) and the `KBArticle.tags` case in `KBArticleSchema.md`.

## Notes

**This was not demonstrated by writing.** The two empty replies already existed,
created by this team on 2026-09-27 while probing the reply path, on a ticket
explicitly named "TEAM15 VERIFY - count check (safe to delete)". We did not add
a third to make the point: the books are shared with other teams, ticket replies
are customer-facing, and the evidence needed was already there to be read.

Keystone was not re-tested for the same reason — confirming it would mean
writing an empty reply to a second shared book. The reply shape is identical in
both schemas, so we expect it to behave the same, and we have said "observed on
Suryodaya" rather than claiming both.

**Where reply text actually lives.** Found while investigating this:
`Ticket.conversations` is a list of objects
(`type`, `body`, `sender`, `sender_id`, `sender_type`, `is_private`,
`attachments`, `created_at`). It is **not** in `TicketReplyDelivery` or
`TicketReplyDispatch`, which hold zero rows for this ticket. Anyone building the
send path for `GD_Week2` Q9 should start here.
