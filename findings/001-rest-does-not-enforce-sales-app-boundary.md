# 001 — REST does not enforce the app boundary for `sales`: 6 of 7 sales entities readable from a Helpdesk seat, on both instances

**Seat:** 15 (Helpdesk) · team15@theschoolofai.in · `allowed_apps: support, agent, crm`
**Instances:** BOTH Suryodaya and Keystone.
**Door:** REST **and MCP** — see the status update below. The UI refuses.
**Severity:** cross-app read of the entire sales pipeline — named prospects, open
deals, orders with pricing, call activities, internal notes. Read-only tested.
**Reproduces:** every call.

Supersedes the earlier narrower write-up, which attributed this to a spurious
`viewer` role on Suryodaya. That explained only the MCP catalogue difference. The
REST behaviour is present on both instances and is the real defect.

## Status update — 2026-09-25: fixed in part, then regressed

Three observed states in eleven days. Each was measured, not inferred:

| date | state |
|---|---|
| 2026-09-14 | 6 of 7 readable over REST. MCP catalogue carried none of them. |
| 2026-09-21 | **5 of 7** — `SalesOrder` revoked, refusing via the role check. Team 04 recorded the same revocation from the Production seat, attributing it to the 2026-09-20 release. But the MCP catalogue had by then *gained* `Deal`, `Lead`, `Activity`, `Note`, `Item` and `CRMPreferences`, so the door that originally refused had started serving. |
| **2026-09-25** | **6 of 7 again.** `SalesOrder` returns HTTP 200 — 312 rows on Suryodaya, 167 on Keystone — and `SalesOrder.*` is back in the MCP catalogue on both. The seat's tool count moved 243 → 234 → 242 across the same window. |

The root cause is unchanged and still visible in `/api/auth/me`: `roles` contains
**`sales_viewer`** while `allowed_apps` is `support, agent, crm`. `Quotation`
alone refuses, and it does so through the **role** check:

```
Quotation   403  "None of your roles ['support_user','user',...]"        <- role check
SalarySlip  403  "App 'payroll' is not enabled for your account"          <- app check
Contract    403  "App 'contracts' is not enabled for your account"        <- app check
EsignDocument 403 "App 'esign' is not enabled for your account"           <- app check
Invoice     403  "App 'accounting' is not enabled for your account"       <- app check
```

**The role check is sound; the app check is the gap.** Three independent tests of
the role path have now refused correctly — `Quotation` read, `SalesOrder` read
during the 21 Sept window, and `KBFolder` **create** from the UI on 2026-09-25
(*"None of your roles [...] can 'create' on KBFolder"*, no row created). The app
path refuses for 22 domains and is absent for `sales`.

That also explains the shape of the 20 Sept fix: a per-entity **role** check was
added to `SalesOrder`, the same protection `Quotation` already had, rather than
repairing the **app** check. It patched one symptom with the working mechanism and
left the other five entities exposed — and it has since been reverted.

## The exposure is wider than the seven entities

`endpoint.make.orders` is in this seat's catalogue and declares
*"Read-only; requires SalesOrder read."* Because that permission is present, it
returns **542 open sales-order lines** on Suryodaya (9 on Keystone), each row
carrying `customer`, `item`, `qty`, `promised`, `stage`, `owner`,
`sales_order_number` and `line_index`, plus stage totals:

```
invoiced 434 · ordered 72 · in_production 4 · shipped 30 · quoted 2
```

So the defect does not expose one entity; it gates a manufacturing planning
surface built on top of it. The endpoint itself is behaving correctly — it asked
for SalesOrder read and the platform granted it.

**Not tested:** whether `endpoint.make.orders` also served during the 20–21 Sept
window when `SalesOrder` read was revoked. It was only measured after the
regression, so no claim is made about that window.

## The platform already implements the correct pattern

`endpoint.accounting.supplier_scorecard` scores suppliers *"with each source
reported incomplete rather than zeroed when not permitted"*. Called from this
seat it returned **5 denied sources** and only the data we may legitimately see.
It checks each underlying source, refuses what is out of seat, and says so.

The fix is therefore not a new mechanism: apply the app check to `sales`, and
apply `supplier_scorecard`'s source-level pattern to endpoints that read across
apps.

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

> **This table describes 2026-09-14 and is no longer current.** By 2026-09-21 the
> MCP catalogue had gained `Deal`, `Lead`, `Activity`, `Note`, `Item` and
> `CRMPreferences`, and on 2026-09-25 `SalesOrder.*` returned to it on both
> instances. Two of the three doors now serve what the seat may not have; only the
> UI still hides it. The original observation stands as a dated measurement and is
> kept because the *direction* of travel is part of the finding: the door that
> enforced the boundary by construction stopped doing so. See the status update at
> the top.

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
