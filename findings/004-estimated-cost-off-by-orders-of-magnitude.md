# 004 — Agent dashboard reports $6,010,165 in estimated cost against 19,100 tokens

**Seat:** 15 (Helpdesk) · team15@theschoolofai.in
**Instance:** Suryodaya. Keystone not yet compared.
**Door:** Agent dashboard (UI), confirmed against MCP `AgentSession.list`.
**Severity:** cosmetic but highly visible — the figure is out by roughly seven
orders of magnitude on the seat's own dashboard.
**Status:** written up, NOT filed.

## What I did

Opened the Agent dashboard at `/v/Agent:Home`, then paged all `AgentSession`
rows over MCP and summed the numeric fields.

## What I expected

A cost estimate consistent with the recorded token usage.

## What happened

The dashboard shows:

```
TOTAL SESSIONS  2050      TOOL CALLS      1
ACTIVE SESSIONS 2029      MESSAGES TODAY  0
EST. COST       $6,010,165.21
```

Summing `AgentSession` over all 2,050 rows:

```
estimated_cost       SUM = 6,010,165.21     <- matches the dashboard exactly
total_input_tokens   SUM =     11,900
total_output_tokens  SUM =      7,200
```

So the dashboard is faithfully summing the stored field; the stored values are
the problem. **19,100 tokens in total are costed at $6,010,165** — about $315 per
token. Commercial rates are roughly $0.000003–$0.000075 per token, so this is out
by around seven orders of magnitude.

A single session carries `estimated_cost` 1,389,633.64 while the largest token
count on any one session is 5,400. No arrangement of the token data supports
these figures, so `estimated_cost` is not derived from them.

## Also visible on the same screen

`AgentSession.status` is `active` on 2,029 of 2,050 rows, `idle` on 6 and
`closed` on 15, with `MESSAGES TODAY: 0`. Sessions appear never to be closed.
Noted, not investigated.

## Notes

- Read-only. Nothing was written.
- Keystone has not been compared; doing so would confirm whether this is seed
  data or a calculation defect, and that comparison should be run before filing.
- `page: Agent:Home`, `agent_seat: Helpdesk`
