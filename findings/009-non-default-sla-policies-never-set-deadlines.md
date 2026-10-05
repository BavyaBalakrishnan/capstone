# 009 — A ticket with no SLA deadline is reported as "not breached", which is indistinguishable from compliant

**Seat:** 15 (Helpdesk) · team15@theschoolofai.in
**Instance:** Suryodaya (observed). Keystone has no affected ticket — see Notes.
**Door:** REST `/api/Ticket` and `/api/SLA`.
**Severity: LOW on the evidence we have.** Two tickets are affected, both on
Suryodaya, and **both were created by this team as probes**. No customer ticket
is affected on either instance. The defect worth reporting is the reporting
behaviour, not the blast radius: a ticket with no deadline is recorded as `not
breached`, the same value a ticket gets for being answered on time. We have not
found a route to this that a customer ticket takes.
**Status:** written up. **Read-only — nothing was written to demonstrate this.**
**Reproduces:** every read. Measured 2026-10-05.

## What is wrong

A ticket can exist with an active SLA policy attached and **no deadlines at
all**. `sla_response_due` and `sla_resolution_due` are both unset. Such a ticket
can never breach, and the platform does not say so: it sets
`sla_response_breached = 0`, which is the same value a ticket gets for being
answered on time.

**That is the defect, and it holds whatever the cause.** A ticket that was not
measured is not a ticket that passed. On any dashboard, in any count, those two
appear in the same column.

## What we first claimed, and why it was wrong

The first version of this report said only the default SLA policy produces
deadlines. **That is false**, and the correction is recorded rather than quietly
edited.

Keystone carries **100 tickets on five different non-default policies** and 0 of
its 150 tickets lack SLA dates. Non-default policies demonstrably do produce
deadlines. The original claim rested on two tickets on one instance, which is
not a sample.

## What the two affected tickets actually have in common

Both are on Suryodaya, and **both were created by this team** through the API:

```
TKT-2026-00104  "I want some respect"  low     Standard support - Maintenance   no dates
TKT-2026-00105  "product exploded"     urgent  Priority support - Sales Desk    no dates
```

The other three tickets this team created (`TKT-2026-00101` to `00103`) all
carry the default policy and all have deadlines — identical ones, suggesting the
platform assigned them. So within our own five, the ones where we set a
non-default policy explicitly at creation are the ones with no deadlines.

**The cause is unresolved.** It may be that deadlines are derived when the
platform assigns a policy and not when one is supplied at creation. We have two
examples and have not reproduced it deliberately, because doing so means writing
more tickets to a shared book to confirm a theory.

## The example

This is one of our own probe tickets, not a customer incident — the title is a
test string. It is useful because it shows what the state looks like, not
because anything is burning.

```
TKT-2026-00105   "product exploded"   (a team-15 probe)
  priority            urgent
  type                incident
  status              open          (reopened once)
  sla_id              f92d0f1f...   -> "Priority support - Sales Desk", is_active=1
  sla_response_due    (unset)
  sla_resolution_due  (unset)
  sla_response_breached  0           <- reported as not breached
```

A ticket with an SLA policy attached, which cannot register a breach and is
counted among the compliant ones. Had this been a real urgent incident rather
than a probe, nothing about the platform's behaviour would have differed - which
is the whole of the argument.

## Is this just user error?

Partly, and we should say so. These are our own probe tickets, and we supplied
the policy ourselves. A reviewer is entitled to answer "you created them wrong".

But the reporting half is not user error, and that is what this report is for.
Whatever caused a ticket to have no deadline, **the platform should not call it
"not breached"**. It should be distinguishable from a ticket that was measured
and met. Otherwise any route to a missing deadline — a bad API call, a policy
with no matching level, a future import — silently manufactures compliance.

## How we found it

Not by reading the platform. A human asked the AgentSwitch assistant on
Suryodaya "how many tickets will breach SLA", and its answer noted in passing
that `TKT-2026-00105` has no SLA due dates set and so can never register a
breach. We had not spotted it. Verifying that observation produced the pattern
above.

Worth recording: that assistant also reported the 77 flagged breaches as "the
desk's own breach determinations", which is the defect in `findings/003` — on
this instance the flag tracks ticket status rather than any measured response
time, and `first_response_at` exists on 5 of 105 tickets. Its own breakdown is
the proof: all 77 flagged tickets are unfinished, all 26 finished tickets are
clean, zero exceptions.

## Relationship to findings/003 and 008

Three defects, one metric:

- **003** - the response clock is usually never started (`first_response_at` on
  5 of 105), so breach cannot be computed and the stored flag mirrors status.
- **008** - where the clock IS started, an empty reply starts it.
- **009** - a ticket can have no clock at all, and that is reported as
  compliance rather than as a gap.

Any one of them is a bug. Together they mean the response-SLA figure this
platform reports cannot be relied on in either direction: it can be satisfied
without answering anyone, and it can be missed entirely by assigning a
non-default policy.

## Suggested fix

Two parts, and the second matters more.

1. Derive the deadlines whenever a ticket is created with an `sla_id` pointing
   at an active policy, however that policy was chosen — or refuse the create.
   A ticket that cannot be measured should not be accepted silently.
2. **Distinguish "no breach" from "no clock".** A ticket with no deadline is not
   compliant; it is unmeasured. A third state, or a null breach flag, would stop
   an urgent open incident appearing in the same column as a closed, properly
   handled one. This is the same distinction `findings/003` asks for and the one
   our own agent makes: it reports response-SLA on this instance as *not
   computable* rather than returning a confident number.

## Notes

**Keystone is unaffected**: 0 of 150 tickets lack SLA dates there — including
100 tickets spread across five non-default policies. That is what disproved our
first explanation.

`TKT-2026-00104` ("I want some respect", closed, low) is the second affected
ticket and carries "Standard support - Maintenance". It matters less because it
is closed, but it is the same defect.

**No write was made.** Attaching a non-default policy to a ticket to prove the
mechanism would mean writing to a shared, customer-facing book; the two existing
examples were enough to establish the pattern, and the per-policy table above
was computed read-only across all 105 tickets.
