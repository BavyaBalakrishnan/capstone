# 001 — REST does not enforce the app boundary for `sales`: 6 of 7 sales entities readable from a Helpdesk seat, on both instances

**Seat:** 15 (Helpdesk) · team15@theschoolofai.in · `allowed_apps: support, agent, crm`
**Instances:** BOTH Suryodaya and Keystone.
**Door:** REST. The MCP and UI doors correctly refuse.
**Severity:** cross-app read of the entire sales pipeline — named prospects, open
deals, orders with pricing, call activities, internal notes. Read-only tested.
**Reproduces:** every call.

Supersedes the earlier narrower write-up, which attributed this to a spurious
`viewer` role on Suryodaya. That explained only the MCP catalogue difference. The
REST behaviour is present on both instances and is the real defect.

## What I did

From seat 15, read one entity per out-of-app domain over REST:

```
GET /api/<Entity>?limit=1     Authorization: Bearer <token>
```

23 domains sit outside this seat's `allowed_apps`. GET only; no writes.

## What I expected

403 for all of them, matching MCP and the UI navigation, per section 3 of the
brief — "Your app: yes. Another team's app: no. 403" — and section 4 — "the same
permission rules ... different door, same answer".

## What happened

**22 of 23 domains correctly returned 403**, with a clear message:

```
{"detail":"App 'payroll' is not enabled for your account"}
```

accounting, approvals, assets, axiom, channels, checklists, communication,
contracts, demo, designreview, email, esign, forms, inventory, knowledgebase,
manufacturing, payroll, people, projects, scheduling, storefront, website — all
refused.

**`sales` was served.** All 7 entities in that domain, on both instances:

| entity | in MCP catalogue | REST Suryodaya | REST Keystone |
|---|---|---|---|
| Activity | no | **200 — 175 rows** | **200 — 177 rows** |
| Deal | no | **200 — 132** | **200 — 63** |
| Item | yes | 200 — 102 | 200 — 28 |
| Lead | no | **200 — 141** | **200 — 21** |
| Note | no | **200 — 100** | **200 — 84** |
| Quotation | no | 403 | 403 |
| SalesOrder | yes / no | **200 — 310** | **200 — 167** |

Sample values returned, unredacted:

```
Lead        "Manoj Rokade"                          (Keystone: "Hocking Hills Mower Works")
Deal        "Thumb Area Grain Handling Co — Grai..."
Activity    "Follow up: Kirloskar Pumps — sourc..."
Note        "Complaint — Ganesh Bearings Pvt Lt..."
SalesOrder  SO-2026-00060 / "Bharat EV Motors Ltd" / grand_total 433389.93
            items[] "Charger Mounting Bracket (FG-CHRG-BRKT)", qty 75,
            amount 62040.0, hsn_or_sac 87089900, gst_treatment "sez"
```

That is the whole sales pipeline: who the prospects are, which deals are open and
at what value, what was ordered at what price under what tax treatment, and
internal call notes about named customers.

## The three doors disagree

Section 4 states the three doors enforce the same rules. For `SalesOrder` on
Keystone they do not:

| door | result |
|---|---|
| UI | hidden — no Sales app in navigation |
| MCP `SalesOrder.list` | `{"code":-32602,"message":"Unknown tool.","data":{"code":"tool_not_available"}}` |
| **REST `GET /api/SalesOrder`** | **200, total 167, customer names included** |

The UI hides it, MCP refuses it, REST serves it. The two doors that are checked
are the two that are enforced.

## Why `Quotation` survives, and what that tells us

`Quotation` is the only `sales` entity refused, and its message is a different
shape:

```
Quotation  403  {"detail":"None of your roles ['support_user','user',...] "}   <- ROLE check
Invoice    403  {"detail":"App 'accounting' is not enabled for your account"}  <- APP check
```

So the app-level check is what is missing, and it is missing specifically for
`sales`. `Quotation` is protected only because it happens to carry an additional
per-entity role check. Nothing else in `sales` does.

That makes the fix a one-line question — why is `sales` absent from the app
enforcement list the other 22 domains are on — rather than seven separate
entity permissions.

## What I verified rather than assumed

The brief states: "Verified on both instances today: from every seat that does
not own them, SalarySlip, Contract and EsignDocument all return 403."

**That holds.** All three returned 403 on both instances via REST from this seat.
So this is not a general collapse of the boundary; it is one app missing from the
enforcement list.

## Notes and limits

- **Read-only throughout. GET only. Nothing was written to either book.**
- Writes were NOT tested. `/openapi.json` declares the generic entity paths
  `/api/{entity_name}`, `/api/bulk/{entity_name}/update` and
  `/api/bulk/{entity_name}/delete`. If the missing app check is in a shared
  dependency rather than on the GET handler, those would be affected too. I have
  not probed that, and would not without being asked — a bulk delete against
  another seat's live data on a shared book is not a test.
- Separately and more minor: this seat's `roles` differ between instances
  (Suryodaya has `viewer`, Keystone does not), which is why `SalesOrder` and
  `CRMPreferences` appear in Suryodaya's MCP catalogue and not Keystone's. That
  is a second, smaller issue in the same area: the MCP catalogue is assembled
  from role grants without intersecting `allowed_apps`. The REST defect above is
  independent of it and present on both instances.
- Suryodaya's first `Item` row is `T6-authtest-item-20260917T042749Z`, so at
  least one other team is probing this area.

## IDS

```
page       : n/a — REST door, GET /api/<Entity>
agent_seat : Helpdesk
instances  : both agentswitch.theschoolofai.in and class.agentswitch.theschoolofai.in
```
