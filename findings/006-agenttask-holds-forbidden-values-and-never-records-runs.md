# 006 — `AgentTask` holds values its own schema forbids, and never records that a task ran

**Seat:** 15 (Helpdesk) · team15@theschoolofai.in
**Instances:** BOTH, in different ways. Suryodaya carries the forbidden values;
Keystone carries the missing run bookkeeping.
**Door:** MCP `AgentTask.list`, schema from REST `GET /api/schemas`.
**Severity:** the scheduler cannot be used to prove a scheduled job ran, and its
rows cannot be parsed against their declared types.
**Status:** written up, NOT filed.
**Reproduces:** every read. Measured 2026-09-20.

## Why this matters for this seat

`AgentTask` is the substrate for monitors and digests — the gap in `GAP_REPORT.md`
§1.2. It carries `schedule_type` (`cron` / `interval` / `one_time`),
`cron_expression`, `interval_minutes`, a required `prompt`, a `channel` and a
`notify_party_id`. An agent that schedules a daily triage digest builds on this
table, and then reads `last_run_at` and `last_run_status` to know whether the
digest went out.

Neither read is trustworthy.

## What I did

Pulled every `AgentTask` row from both instances (Suryodaya 96, Keystone 2) over
MCP, and compared the stored values against the `AgentTask` schema in
`/api/schemas`. Read-only; `AgentTask.list` only.

## What I expected

Values consistent with the declared schema, and run bookkeeping consistent with
`run_count`.

## What happened

### (1) `last_run_status` holds a value the schema does not declare

The schema declares exactly three options:

```json
{"name": "last_run_status", "type": "select",
 "options": ["success", "failed", "timeout"]}
```

Observed on Suryodaya across 96 rows:

| value | rows |
|---|---|
| `failed` | 31 |
| `timeout` | 26 |
| `success` | 24 |
| **`queued`** | **15** |

`queued` is not in the enum. 15 of 96 rows carry it.

This is the same defect class as `findings/002`, where `Ticket.tags` was stored as
a list against a declared type of `text`. A client that switches on the declared
options — which is what a closed JSON Schema invites an agent to do, per section 6
of the brief — has no branch for `queued`.

### (2) `cron_expression` holds product names, not cron expressions

31 rows have `schedule_type: cron` and a `cron_expression` that is not a cron
expression:

```
"Feeler Gauge Set 597"      "Drill Chuck 596"       "Lathe Dog 595"
"Punch Set 593"             "C-Clamp 585"           "Scriber 586"
```

The `name` field is the same kind of value — `"Bench Vice 281mm (Kg)"`,
`"Toolmaker's Vice 263mm (Pair)"`, `"Machinist Square 308mm (Nos)"`. These are
`Item` rows: hardware products, with sizes and units of measure. Item data has
been seeded into the agent-task table.

No scheduler can act on `"Drill Chuck 596"`. Any agent that reads this table to
find out when its own task next runs gets a product name.

### (3) `one_time` tasks report having run many times

17 rows have `schedule_type: one_time` and `run_count > 1`:

```
"Feeler Gauge Set 50mm (Set)"   one_time   run_count 57
"Lathe Dog 45mm (Set)"          one_time   run_count 48
"Vernier Caliper 210mm (Pair)"  one_time   run_count 32
"File Set 203mm (Mtr)"          one_time   run_count 27
```

A one-time task that ran 57 times is unreachable under any reading of the field.

### (4) Rows report a last-run status without ever having run

14 rows have `run_count: 0` and a populated `last_run_status`:

```
"Bench Vice 281mm (Kg)"         run_count 0   last_run_status timeout
"Machinist Square 308mm (Nos)"  run_count 0   last_run_status timeout
"Hex Key Set 264mm (Kg)"        run_count 0   last_run_status success
```

A task that has run zero times cannot have succeeded.

### (5) Keystone: the tasks are clean, and the runs are never recorded

Keystone's two rows are exactly what this table is for, and their cron
expressions are valid:

| name | schedule | status | run_count | last_run_at | last_run_status |
|---|---|---|---|---|---|
| Weekly Business Summary | `cron 0 8 * * MON` | active | 8 | **null** | **null** |
| Daily Invoice Reminder | `cron 0 9 * * MON-FRI` | active | 22 | **null** | **null** |

Thirty runs between them, by the platform's own counter, and **not one recorded
when it happened or whether it worked.**

This is `findings/003` on a second entity. There, `first_response_at` is null on
102 of 103 tickets while replies demonstrably exist. Here, `last_run_at` is null
on both tasks while `run_count` says they ran 30 times. The same failure mode:
the work happens, the counter moves, the timestamp that would prove it stays
empty.

## Which instance is correct

Neither, in different halves.

| | Suryodaya | Keystone |
|---|---|---|
| rows | 96 | 2 |
| rows that look like real tasks | 0 | 2 |
| `last_run_status` outside the enum | 15 | 0 |
| `cron_expression` not a cron expression | 31 | 0 |
| `one_time` with `run_count > 1` | 17 | 0 |
| `run_count: 0` with a `last_run_status` | 14 | 0 |
| `run_count > 0` with `last_run_at` null | 0 | **2 of 2** |

Suryodaya's data is unusable. Keystone's data is plausible and unverifiable.

## Impact

1. **A scheduled digest cannot be proven to have run.** An agent that schedules a
   monitor and later checks `last_run_at` learns nothing on Keystone and reads a
   product name on Suryodaya.
2. **The declared schema cannot be used to parse the table.** `queued` is not in
   the enum, so a closed-schema client either crashes or silently misclassifies
   15 of 96 rows.
3. **`run_count` and `last_run_*` disagree in both directions** — zero runs with a
   status on one instance, many runs with no status on the other. There is no
   consistent rule for reconciling them.

## Suggested fix, in order of cost

1. Add `queued` to the declared options, or stop writing it. One of the two is
   wrong; the schema and the writer disagree.
2. Write `last_run_at` and `last_run_status` whenever `run_count` is incremented,
   in the same transaction.
3. Reject `cron_expression` values that do not parse as cron when
   `schedule_type: cron`. A record would have refused all 31; a text field
   accepted every one — the same point `GAP_REPORT.md` §1.5 makes about
   `Ticket.assigned_group`.
4. Reseed Suryodaya's `AgentTask` rows. They are `Item` data in an agent table.

## Notes and limits

- **Read-only throughout. `AgentTask.list` only. Nothing was written to either
  book.** No task was created, run, paused or resumed, although
  `AgentTask.create`, `.run_now`, `.pause` and `.resume` are all in this seat's
  catalogue.
- Whether the scheduler *executes* was not tested, because testing it means
  writing to a shared book. The claim here is only about what the rows say.
- `AgentRunbook` holds 0 rows on both instances.
- `AgentJob` holds 1227 rows on Suryodaya and 97 on Keystone, so job execution is
  clearly happening somewhere; this finding does not claim the agent subsystem is
  idle, only that `AgentTask`'s own record of it is unreliable.

## IDS

```
page       : n/a — MCP door, AgentTask.list
agent_seat : Helpdesk
instances  : both agentswitch.theschoolofai.in and class.agentswitch.theschoolofai.in
measured   : 2026-09-20
```
